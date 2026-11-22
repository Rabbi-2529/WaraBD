"""Create order (admin), WB order numbers, SEO keywords, FAQs, category pages, admin layout."""

import json
from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from customers.models import Customer

from .forms import FaqField, ProductOrganizeForm
from .models import Category, District, Order, OrderItem, Page, PageSeo, Product, SeoKeyword


def _order(**extra):
    data = {"full_name": "Rahim", "phone": "01712345678", "address_line1": "House 1", "city": "Dhaka"}
    data.update(extra)
    return Order.objects.create(**data)


class OrderNumberTests(TestCase):
    def test_numbers_run_per_day(self):
        today = timezone.localdate().strftime("%Y%m%d")
        self.assertEqual(_order().order_number, f"WB{today}001")
        self.assertEqual(_order().order_number, f"WB{today}002")
        self.assertEqual(Order.next_order_number(), f"WB{today}003")

    def test_number_follows_the_order_date(self):
        day = timezone.make_aware(datetime(2026, 1, 5, 11, 0))
        self.assertEqual(_order(created_at=day).order_number, "WB20260105001")
        self.assertEqual(_order(created_at=day).order_number, "WB20260105002")

    def test_old_numbers_are_kept(self):
        self.assertEqual(_order(order_number="ORD-ABC").order_number, "ORD-ABC")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class CreateOrderAdminTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")
        self.client.force_login(self.staff)
        self.lock = Product.objects.create(name="Smart Lock", slug="smart-lock", sku="FT-SCL029",
                                           model_number="FT-SCL029", price=Decimal("2000"), stock=5)
        self.watch = Product.objects.create(name="Smart Watch", slug="smart-watch", price=Decimal("3500"), stock=1)
        self.dhaka_fee = District.objects.get(name_en="Dhaka").delivery_fee

    def post(self, **extra):
        data = {
            "phone": "+880 1712-345678", "full_name": "Rahim Uddin", "email": "", "city": "Dhaka",
            "thana": "Dhanmondi", "address_line1": "House 12, Road 5", "notes": "Call first",
            "status": "pending", "payment_status": "unpaid", "payment_method": "cod", "shipping": "",
            "created_at_date": timezone.localdate().isoformat(),
            "item_product": [self.lock.pk, self.watch.pk], "item_qty": ["2", "3"], "item_price": ["1900", "3500"],
            "_save": "1",
        }
        data.update(extra)
        return self.client.post("/admin/web/order/add/", data)

    def test_page_shows_next_number_and_locations(self):
        r = self.client.get("/admin/web/order/add/")
        self.assertContains(r, Order.next_order_number())
        self.assertContains(r, 'id="order-locations"')
        self.assertContains(r, "wara-order.js")
        self.assertContains(r, 'inputmode="numeric"')

    def test_order_is_created_with_lines_totals_and_stock(self):
        Customer.objects.create(phone="01712345678", name="Rahim Uddin")
        r = self.post()
        self.assertEqual(r.status_code, 302, r.content.decode()[:3000])
        order = Order.objects.get()
        self.assertTrue(order.order_number.startswith("WB" + timezone.localdate().strftime("%Y%m%d")))
        self.assertEqual(order.phone, "01712345678")
        self.assertEqual(order.thana, "Dhanmondi")
        self.assertEqual(order.delivery_zone, Order.ZONE_INSIDE)
        self.assertEqual(order.subtotal, Decimal("1900") * 2 + Decimal("3500") * 3)
        self.assertEqual(order.shipping, self.dhaka_fee)
        self.assertEqual(order.total, order.subtotal + order.shipping)
        self.assertIsNotNone(order.customer)
        self.assertEqual(OrderItem.objects.filter(order=order).count(), 2)
        self.lock.refresh_from_db()
        self.watch.refresh_from_db()
        self.assertEqual((self.lock.stock, self.watch.stock), (3, 0))

    def test_typed_delivery_charge_wins(self):
        self.post(shipping="0")
        self.assertEqual(Order.objects.get().shipping, Decimal("0"))

    def test_bad_phone_and_no_products_are_refused(self):
        r = self.post(phone="12345", item_product=[], item_qty=[], item_price=[])
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Bangladeshi mobile number")
        self.assertContains(r, "Add at least one product")
        self.assertFalse(Order.objects.exists())

    def test_wrong_thana_is_refused(self):
        r = self.post(thana="Nowhere")
        self.assertContains(r, "Pick the thana from the list")
        self.assertFalse(Order.objects.exists())

    def test_product_search(self):
        r = self.client.get("/admin/web/order/product-search/", {"q": "scl029"})
        names = [row["name"] for row in r.json()["results"]]
        self.assertEqual(names, ["Smart Lock"])
        self.assertEqual(r.json()["results"][0]["price"], "2000.00")
        self.client.logout()
        self.assertEqual(self.client.get("/admin/web/order/product-search/", {"q": "x"}).status_code, 302)

    def test_customer_lookup(self):
        customer = Customer.objects.create(phone="01812345678", name="Karim", email="k@example.com")
        customer.addresses.create(label="Office", name="Karim", phone="01812345678", district="Gazipur",
                                  thana="Tongi", address="Plot 4", is_default=True)
        _order(phone="01812345678", full_name="Karim", total=Decimal("500"))
        data = self.client.get("/admin/web/order/customer-lookup/", {"phone": "8801812345678"}).json()
        self.assertTrue(data["found"])
        self.assertEqual(data["orders"]["count"], 1)
        self.assertEqual(data["fill"]["district"], "Dhaka")  # the last order wins over saved addresses
        self.assertEqual(data["addresses"][0]["label"], "Office")
        new = self.client.get("/admin/web/order/customer-lookup/", {"phone": "01912345678"}).json()
        self.assertFalse(new["found"])
        self.assertEqual(self.client.get("/admin/web/order/customer-lookup/", {"phone": "0171"}).status_code, 400)

    def test_edit_page_has_district_dropdowns(self):
        order = _order(thana="Dhanmondi")
        r = self.client.get(f"/admin/web/order/{order.pk}/change/")
        self.assertContains(r, "data-order-district")
        self.assertContains(r, "wara-order-address.js")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class KeywordsFaqCategoryTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")

    def test_category_admin_keywords_faq_and_page(self):
        SeoKeyword.objects.create(name="Smart lock")
        self.client.force_login(self.staff)
        r = self.client.post("/admin/web/category/add/", {
            "name_en": "Cabinet Locks", "name_bn": "", "slug": "cabinet-locks", "description_en": "Keypad locks.",
            "description_bn": "", "is_active": "on",
            "faq_en": "Q: Battery?\nA: 4 x AAA.\n\nQ: Warranty?\nA: One year.", "faq_bn": "",
            "seo_title_en": "", "seo_title_bn": "", "seo_description_en": "", "seo_description_bn": "",
            "seo_keywords": ["smart lock", "Keypad lock", "keypad LOCK"],
        })
        self.assertEqual(r.status_code, 302, r.content.decode()[:2000])
        category = Category.objects.get(slug="cabinet-locks")
        self.assertEqual(sorted(category.seo_keywords.values_list("name", flat=True)), ["Keypad lock", "Smart lock"])
        self.assertEqual(SeoKeyword.objects.count(), 2)
        self.assertEqual(category.faq_en[0], {"q": "Battery?", "a": "4 x AAA."})

        Product.objects.create(name="Lock", slug="lock-1", price=Decimal("10"), stock=1, category=category)
        page = self.client.get("/category/cabinet-locks/").content.decode()
        self.assertIn('<meta name="keywords" content="Keypad lock, Smart lock">', page)
        self.assertIn("Cabinet Locks | ", page)
        self.assertIn('"@type": "FAQPage"', page)
        self.assertIn("Battery?", page)
        self.assertEqual(self.client.get("/products/?category=cabinet-locks").status_code, 301)

    def test_keyword_box_offers_existing_keywords(self):
        SeoKeyword.objects.create(name="Fingerprint lock")
        self.client.force_login(self.staff)
        r = self.client.get("/admin/web/product/add/")
        self.assertContains(r, 'data-keyword-tags="1"')
        self.assertContains(r, '<option value="Fingerprint lock">Fingerprint lock</option>', html=False)
        self.assertContains(r, 'id="sec-faq"')
        self.assertContains(r, "data-faq-editor")

    def test_policy_page_and_fixed_page_faq(self):
        Page.objects.create(slug="returns", title="Returns", body="<p>Seven days.</p>",
                            faq=[{"q": "Who pays return delivery?", "a": "We do."}])
        body = self.client.get("/page/returns/").content.decode()
        self.assertIn("Who pays return delivery?", body)
        self.assertIn('"@type": "FAQPage"', body)
        row, _ = PageSeo.objects.get_or_create(page="contact")
        row.faq = [{"q": "Are you open on Friday?", "a": "Yes, after 3 PM."}]
        row.save()
        row.seo_keywords.add(SeoKeyword.objects.create(name="wara contact"))
        contact = self.client.get("/contact/").content.decode()
        self.assertIn("Are you open on Friday?", contact)
        self.assertIn('content="wara contact"', contact)
        self.assertNotIn("Are you open on Friday?", self.client.get("/about/").content.decode())

    def test_faq_field_needs_question_and_answer(self):
        self.assertEqual(FaqField().clean(""), [])
        with self.assertRaises(Exception):
            FaqField().clean("Q: \nA: An answer with no question")
        with self.assertRaises(Exception):
            FaqField().clean("Q: A question with no answer")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class AdminLayoutAndPriceTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")
        self.client.force_login(self.staff)

    def test_generic_pages_use_cards(self):
        self.assertContains(self.client.get("/admin/web/page/add/"), 'class="wf-card')
        category = Category.objects.create(name="Old", slug="old")
        self.assertContains(self.client.get(f"/admin/web/category/{category.pk}/delete/"), "wf-danger-card")
        self.assertContains(self.client.get(f"/admin/web/category/{category.pk}/history/"), "Change history")
        self.assertContains(self.client.get("/admin/password_change/"), "Change your password")
        popup = self.client.get("/admin/web/category/add/?_popup=1").content.decode()
        self.assertNotIn('class="admin-sidebar', popup)

    def test_discount_never_makes_a_negative_price(self):
        product = Product(name="X", price=Decimal("1200"), discount_type="percent", discount_price=Decimal("1212"))
        self.assertEqual(product.current_price, Decimal("0"))
        form = ProductOrganizeForm(data={"name_en": "X", "sku": "X1", "stock": 1, "price": "1200",
                                         "discount_type": "percent", "discount_price": "150", "stock_status": "in-stock"})
        self.assertFalse(form.is_valid())
        self.assertIn("100 or less", json.dumps(form.errors))

    def test_checkout_address_and_note_are_single_line(self):
        body = self.client.get("/checkout/").content.decode()
        self.assertIn('<input id="coAddress"', body)
        self.assertIn('<input id="coNote"', body)
        self.assertNotIn("<textarea", body)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class DiscountPaymentLookupTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")
        self.lock = Product.objects.create(name="Smart Lock", slug="smart-lock", price=Decimal("2000"), stock=5,
                                           warranty="1 Year")

    def create(self, **extra):
        self.client.force_login(self.staff)
        data = {"phone": "01712345678", "full_name": "Rahim Uddin", "city": "Dhaka", "thana": "Dhanmondi",
                "address_line1": "House 12, Road 5", "status": "pending", "payment_status": "unpaid",
                "payment_method": "cod", "shipping": "60", "item_product": [self.lock.pk], "item_qty": ["2"],
                "item_price": ["2000"], "_save": "1"}
        data.update(extra)
        return self.client.post("/admin/web/order/add/", data)

    def test_fixed_and_percent_discount(self):
        self.create(discount_type="fixed", discount_value="500")
        order = Order.objects.get()
        self.assertEqual((order.subtotal, order.discount, order.total), (Decimal("4000"), Decimal("500"), Decimal("3560")))
        self.assertContains(self.client.get(f"/admin/web/order/{order.pk}/change/"), "Discount")
        self.create(discount_type="percent", discount_value="10")
        self.assertEqual(Order.objects.order_by("-pk").first().discount, Decimal("400.00"))

    def test_too_big_discount_is_refused(self):
        r = self.create(discount_type="fixed", discount_value="5000")
        self.assertContains(r, "more than the products")
        r = self.create(discount_type="percent", discount_value="150")
        self.assertContains(r, "100 or less")
        self.assertFalse(Order.objects.exists())

    def test_checkout_lookup_only_for_own_number(self):
        Order.objects.create(full_name="Karim", phone="01812345678", address_line1="Plot 4", city="Gazipur", thana="Tongi")
        ask = lambda: self.client.post("/api/checkout/lookup/", json.dumps({"phone": "01812345678"}),
                                       content_type="application/json").json()
        self.assertEqual(ask(), {"found": False})          # a stranger cannot read someone's address
        from customers.auth import VERIFIED_KEY, _today

        session = self.client.session
        session[VERIFIED_KEY] = {"01812345678": _today()}
        session.save()
        data = ask()
        self.assertTrue(data["found"])
        self.assertEqual((data["district"], data["thana"], data["address"]), ("Gazipur", "Tongi", "Plot 4"))

    def test_payment_methods_follow_site_settings(self):
        from .models import SiteSettings

        site = SiteSettings.load()
        site.pay_bkash_enabled = False
        site.pay_default = "nagad"
        site.save()
        page = self.client.get("/checkout/").content.decode()
        self.assertNotIn('id="pBkash"', page)
        self.assertIn('id="pNagad" value="nagad" checked', page)
        self.assertIn('id="pCod" value="cod">', page)
        self.assertLess(page.index('id="coPhone"'), page.index('id="coName"'))   # mobile number first
        payload = {"name": "Guest Buyer", "phone": "01912345678", "district": "Dhaka", "thana": "Dhanmondi",
                   "address": "House 12, Road 5, Dhanmondi", "payment": "bkash", "sender": "01912345678",
                   "trx": "ABC123XYZ", "lines": [{"id": "smart-lock", "qty": 1}]}
        r = self.client.post("/api/checkout/", json.dumps(payload), content_type="application/json").json()
        self.assertEqual(r["errors"]["payment"], "Please choose a payment method.")
        site.pay_cod_enabled = site.pay_nagad_enabled = False
        self.assertEqual(site.payment_methods(), ["cod"])  # never empty

    def test_product_delivery_info_is_one_row(self):
        page = self.client.get("/smart-lock").content.decode()
        self.assertIn("delivery-box delivery-strip", page)
        self.assertIn("1 Year warranty", page)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class InvoiceAndPrivacyTests(TestCase):
    def setUp(self):
        self.lock = Product.objects.create(name="Smart Lock", slug="smart-lock", price=Decimal("1395"), stock=5,
                                           warranty="1 Year", model_number="FT-SCL029")
        self.order = Order.objects.create(full_name="Md Jihad", phone="01906935144", address_line1="Ward 26, Joydebpur",
                                          city="Gazipur", thana="Gazipur Sadar", subtotal=Decimal("1395"),
                                          discount=Decimal("0"), shipping=Decimal("150"), total=Decimal("1545"))
        OrderItem.objects.create(order=self.order, product=self.lock, quantity=1, price=Decimal("1395"))

    def test_strangers_cannot_open_an_order_by_guessing_its_number(self):
        n = self.order.order_number
        self.assertRedirects(self.client.get(f"/order/success/{n}/"), "/track-order/", fetch_redirect_response=False)
        self.assertRedirects(self.client.get(f"/order/{n}/invoice/"), "/track-order/", fetch_redirect_response=False)

    def test_browser_that_placed_it_sees_the_invoice(self):
        session = self.client.session
        session["placed_orders"] = [self.order.order_number]
        session.save()
        page = self.client.get(f"/order/{self.order.order_number}/invoice/").content.decode()
        for text in ("Invoice No:", self.order.order_number, "Md Jihad", "Ward 26, Joydebpur, Gazipur Sadar, Gazipur",
                     "1,395.00", "Promotion discount :", "Shipping Cost :", "৳150.00", "Total Payable Amount:",
                     "৳1,545.00", "Customer Signature", "Terms &amp; Condition", "Sales Person:</b> Website", "1 Year"):
            self.assertIn(text, page)
        self.assertEqual(self.client.get(f"/order/success/{self.order.order_number}/").status_code, 200)

    def test_admin_invoice_and_sales_person(self):
        staff = get_user_model().objects.create_superuser(email="sara@example.com", password="x-test-only")
        self.client.force_login(staff)
        self.order.created_by = staff
        self.order.status = Order.STATUS_DELIVERED
        self.order.save()
        self.assertIsNotNone(self.order.delivered_at)
        page = self.client.get(f"/admin/web/order/{self.order.pk}/invoice/").content.decode()
        self.assertIn("Sales Person:</b> sara", page)
        self.assertIn(f"/admin/web/order/{self.order.pk}/change/", page)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class OrderPageTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")
        self.client.force_login(self.staff)
        self.order = _order(thana="Dhanmondi", notes="Gate 2")

    def post(self, **extra):
        o = self.order
        data = {"status": "shipped", "payment_status": "unpaid", "notes": o.notes, "full_name": o.full_name,
                "email": o.email, "phone": o.phone, "address_line1": o.address_line1, "thana": o.thana,
                "city": o.city, "postal_code": "", "courier": "", "courier_tracking_code": "",
                "courier_tracking_url": "", "_continue": "1"}
        data.update(extra)
        return self.client.post(f"/admin/web/order/{o.pk}/change/", data)

    def test_page_shows_new_layout(self):
        page = self.client.get(f"/admin/web/order/{self.order.pk}/change/").content.decode()
        for text in ('class="wf-form od"', "od-track", "Customer &amp; delivery", "To collect:", 'name="status" value="shipped"'):
            self.assertIn(text, page)

    def test_saving_keeps_everything_and_checks_the_phone(self):
        self.assertEqual(self.post(phone="+880 1812-345678").status_code, 302)
        self.order.refresh_from_db()
        self.assertEqual((self.order.status, self.order.phone, self.order.notes), ("shipped", "01812345678", "Gate 2"))
        r = self.post(phone="12345")
        self.assertContains(r, "Not saved")
        self.assertContains(r, "Bangladeshi mobile number")
