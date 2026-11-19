"""Phase 1 tests: BD formats, checkout totals, mobile payments, contact, SEO files."""

import json
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import Client, TestCase, override_settings

from .bd import clean_bd_district, format_taka, normalize_bd_phone
from .models import ContactMessage, Order, Product, SiteFeature, SiteSettings, UseCase


class BdFormatTests(TestCase):
    def test_phone_variants_normalise_to_local_format(self):
        for raw in ("01712345678", "+8801712345678", "8801712345678", "017-1234 5678", " 01712345678 "):
            self.assertEqual(normalize_bd_phone(raw), "01712345678", raw)

    def test_phone_rejects_bad_numbers(self):
        for raw in ("", None, "0171234567", "017123456789", "01212345678", "+11712345678", "abcdefghijk"):
            with self.assertRaises(ValueError, msg=raw):
                normalize_bd_phone(raw)

    def test_district_is_case_insensitive_and_canonical(self):
        self.assertEqual(clean_bd_district("dhaka"), "Dhaka")
        self.assertEqual(clean_bd_district("COX'S BAZAR"), "Cox's Bazar")
        with self.assertRaises(ValueError):
            clean_bd_district("Kolkata")

    def test_taka_uses_lakh_grouping(self):
        self.assertEqual(format_taka(1975), "৳1,975")
        self.assertEqual(format_taka(150000), "৳1,50,000")
        self.assertEqual(format_taka(Decimal("12345678.40")), "৳1,23,45,678")
        self.assertEqual(format_taka(60), "৳60")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class CheckoutTests(TestCase):
    def setUp(self):
        site = SiteSettings.load()
        site.delivery_inside_fee = 60
        site.delivery_outside_fee = 120
        site.save()
        self.product = Product.objects.create(
            name="Test Lock", slug="test-lock", price=Decimal("2050"),
            discount_type="fixed", discount_price=Decimal("75"), stock=10,
        )

    def payload(self, **overrides):
        data = {
            "name": "Rahim Uddin",
            "phone": "+880 1712-345678",
            "email": "",
            "district": "dhaka",
            "address": "House 12, Road 5, Dhanmondi",
            "note": "",
            "payment": "cod",
            "zone": "inside",
            "lines": [{"id": "test-lock", "qty": 2}],
        }
        data.update(overrides)
        return data

    def post(self, data, client=None):
        client = client or self.client
        return client.post("/api/checkout/", json.dumps(data), content_type="application/json")

    def test_inside_dhaka_fee_is_added_to_total(self):
        r = self.post(self.payload())
        self.assertEqual(r.status_code, 200, r.content)
        order = Order.objects.get(order_number=r.json()["order_number"])
        self.assertEqual(order.subtotal, Decimal("3950"))
        self.assertEqual(order.shipping, Decimal("60"))
        self.assertEqual(order.total, Decimal("4010"))
        self.assertEqual(order.delivery_zone, "inside")
        self.assertEqual(order.phone, "01712345678")
        self.assertEqual(order.city, "Dhaka")
        self.assertEqual(order.payment_status, "unpaid")
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 8)

    def test_outside_dhaka_fee_comes_from_settings_not_browser(self):
        r = self.post(self.payload(zone="outside", delivery=0, total=1))
        order = Order.objects.get(order_number=r.json()["order_number"])
        self.assertEqual(order.shipping, Decimal("120"))
        self.assertEqual(order.total, Decimal("4070"))

    def test_bkash_needs_sender_and_trx(self):
        r = self.post(self.payload(payment="bkash"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("sender", r.json()["errors"])
        self.assertIn("trx", r.json()["errors"])
        self.assertFalse(Order.objects.exists())

    def test_bkash_order_awaits_verification_with_trx_saved(self):
        r = self.post(self.payload(payment="bkash", sender="01812345678", trx="9a7k3m2q8t"))
        self.assertEqual(r.status_code, 200, r.content)
        order = Order.objects.get()
        self.assertEqual(order.payment_status, Order.PAYMENT_VERIFYING)
        self.assertEqual(order.payment_sender, "01812345678")
        self.assertEqual(order.transaction_id, "9A7K3M2Q8T")

    def test_cod_ignores_stray_trx(self):
        self.post(self.payload(payment="cod", sender="01812345678", trx="ABCDEF12"))
        order = Order.objects.get()
        self.assertEqual(order.transaction_id, "")
        self.assertEqual(order.payment_sender, "")

    def test_invalid_phone_and_district_rejected(self):
        r = self.post(self.payload(phone="12345", district="Atlantis"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.json()["errors"]), {"phone", "district"})
        self.assertFalse(Order.objects.exists())

    def test_not_enough_stock_is_a_clean_400(self):
        r = self.post(self.payload(lines=[{"id": "test-lock", "qty": 50}]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("stock", r.json()["error"])

    def test_checkout_requires_csrf_token(self):
        r = self.post(self.payload(), client=Client(enforce_csrf_checks=True))
        self.assertEqual(r.status_code, 403)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class ContactApiTests(TestCase):
    def post(self, **data):
        return self.client.post("/api/contact/", json.dumps(data), content_type="application/json")

    def test_saves_with_normalised_phone(self):
        r = self.post(name="Karim", phone="8801912345678", email="", subject="Order status", message="Where is my order please?")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(ContactMessage.objects.get().phone, "01912345678")

    def test_rejects_bad_phone(self):
        r = self.post(name="Karim", phone="555", subject="Order status", message="Where is my order please?")
        self.assertEqual(r.status_code, 400)
        self.assertIn("phone", r.json()["errors"])


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"], SITE_URL="https://warabd.com")
class SeoAndPagesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_wara", stdout=StringIO())

    def test_robots_txt_points_to_sitemap(self):
        r = self.client.get("/robots.txt")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("Disallow: /checkout/", body)
        self.assertIn("Sitemap: https://warabd.com/sitemap.xml", body)

    def test_sitemap_uses_site_url_and_lists_products(self):
        r = self.client.get("/sitemap.xml")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("<loc>https://warabd.com/products/ft-scl029/</loc>", body)
        self.assertNotIn("example.com", body)

    def test_each_product_page_has_its_own_title_and_description(self):
        body = self.client.get("/products/ft-scl029/").content.decode()
        self.assertIn("<title>WaRa FT-SCL029 Cabinet Drawer Lock (FT-SCL029) | ", body)
        self.assertIn('content="A compact round keypad', body)

    def test_portfolio_receives_use_cases_with_cat_key(self):
        body = self.client.get("/portfolio/").content.decode()
        self.assertIn('id="usecases-data"', body)
        self.assertIn('"cat": "office"', body)

    def test_home_mode_cards_show_badge_and_best_for(self):
        body = self.client.get("/").content.decode()
        self.assertIn('<span class="badge">Visitor password</span>', body)
        self.assertIn("gyms, spas, hotels, schools, malls", body)

    def test_product_page_renders_all_sections_on_the_server(self):
        body = self.client.get("/products/ft-scl029/").content.decode()
        # Price in BD format with discount
        self.assertIn('<span class="price-now">৳1,975</span>', body)
        self.assertIn('<span class="price-old">৳2,050</span>', body)
        # Highlights, description, specs, features, how-to, FAQ, delivery
        self.assertIn("<span>Management + user codes</span>", body)
        self.assertIn("Keyless, code-protected storage for anything with a door", body)
        self.assertIn('<th scope="row">Suitable door thickness</th><td>More than 3 mm</td>', body)
        self.assertIn("<h3>Visitor password changing</h3>", body)
        self.assertIn('id="tab-howto"', body)
        self.assertIn("What happens if the battery runs out?", body)
        self.assertIn('id="tab-warranty"', body)
        self.assertIn("Inside Dhaka — ৳", body)
        # Buy box + breadcrumbs + gallery data for the lightbox
        self.assertIn('id="buyRow"', body)
        self.assertIn('data-id="ft-scl029"', body)
        self.assertIn('?category=smart-cabinet-lock">Smart Cabinet Lock</a>', body)
        self.assertIn('id="product-images"', body)

    def test_out_of_stock_product_has_no_buy_buttons(self):
        Product.objects.filter(slug="ft-scl029").update(stock_status=Product.STOCK_OUT)
        body = self.client.get("/products/ft-scl029/").content.decode()
        self.assertNotIn('id="buyRow"', body)
        self.assertNotIn('id="stickyBuy"', body)
        self.assertIn("This product is out of stock", body)

    def test_badly_typed_admin_json_does_not_break_the_page(self):
        Product.objects.filter(slug="ft-scl029").update(
            specs=[["Only label"], {"label": "Weight", "value": "120 g"}, "junk"],
            features={"not": "a list"},
            faq=[{"question": "Old key names?", "answer": "<strong>Still</strong> shown"}, {"q": "No answer"}],
            steps=None and [] or ["Plain text step"],
            applications=["wrong type"],
            highlights=["  ", "Real highlight"],
        )
        r = self.client.get("/products/ft-scl029/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("<th scope=\"row\">Weight</th><td>120 g</td>", body)
        self.assertNotIn('id="tab-features"', body)
        self.assertIn("Old key names?", body)
        self.assertIn("Still shown", body)
        self.assertNotIn("<span>No answer</span>", body)
        self.assertEqual(body.count('class="faq-item'), 1)
        self.assertIn("Plain text step", body)
        self.assertIn("<span>Real highlight</span>", body)

    def test_seed_is_safe_to_run_twice(self):
        call_command("seed_wara", stdout=StringIO())
        self.assertEqual(Product.objects.filter(slug="ft-scl029").count(), 1)
        self.assertEqual(UseCase.objects.count(), 12)
        self.assertEqual(SiteFeature.objects.filter(section="home_mode").count(), 2)
