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
            "thana": "Dhanmondi",
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

    def test_outside_dhaka_fee_follows_the_district_not_the_browser(self):
        # The browser sends a fake zone / fee / total: the server ignores them.
        r = self.post(self.payload(district="Gazipur", thana="Tongi", zone="inside", delivery=0, total=1))
        self.assertEqual(r.status_code, 200, r.content)
        order = Order.objects.get(order_number=r.json()["order_number"])
        self.assertEqual(order.shipping, Decimal("120"))
        self.assertEqual(order.total, Decimal("4070"))
        self.assertEqual(order.delivery_zone, "outside")
        self.assertEqual((order.city, order.thana), ("Gazipur", "Tongi"))

    def test_thana_with_its_own_charge_overrides_the_district(self):
        from .models import Thana
        Thana.objects.filter(district__name_en="Dhaka", name_en="Dhanmondi").update(delivery_fee=80)
        r = self.post(self.payload())
        order = Order.objects.get(order_number=r.json()["order_number"])
        self.assertEqual(order.shipping, Decimal("80"))
        self.assertEqual(order.total, Decimal("4030"))

    def test_district_charge_edited_in_admin_is_used(self):
        from .models import District
        District.objects.filter(name_en="Gazipur").update(delivery_fee=150)
        r = self.post(self.payload(district="Gazipur", thana="Tongi"))
        self.assertEqual(Order.objects.get(order_number=r.json()["order_number"]).shipping, Decimal("150"))

    def test_thana_is_required(self):
        r = self.post(self.payload(thana=""))
        self.assertEqual(r.status_code, 400)
        self.assertIn("thana", r.json()["errors"])
        self.assertFalse(Order.objects.exists())

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
        self.assertIn("<loc>https://warabd.com/ft-scl029</loc>", body)
        self.assertNotIn("example.com", body)

    def test_each_product_page_has_its_own_title_and_description(self):
        body = self.client.get("/ft-scl029").content.decode()
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
        body = self.client.get("/ft-scl029").content.decode()
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
        body = self.client.get("/ft-scl029").content.decode()
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
        r = self.client.get("/ft-scl029")
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


# ==============================================================================
# Phase 2: English / Bangla
# ==============================================================================

@override_settings(ALLOWED_HOSTS=["testserver", "localhost"], SITE_URL="https://warabd.com")
class BanglaSiteTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_wara", stdout=StringIO())

    def page(self, url):
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200, url)
        return r.content.decode()

    def test_every_store_page_works_in_both_languages(self):
        for path in ["/", "/products/", "/ft-scl029", "/portfolio/", "/about/",
                     "/contact/", "/cart/", "/checkout/", "/order/failed/"]:
            en = self.page(path)
            bn = self.page("/bn" + path)
            self.assertIn('<html lang="en">', en, path)
            self.assertIn('<html lang="bn">', bn, path)

    def test_header_has_language_switcher_to_the_same_page(self):
        en = self.page("/ft-scl029")
        self.assertIn('class="lang-switch" href="/bn/ft-scl029"', en)
        self.assertIn("<span>বাংলা</span>", en)
        bn = self.page("/bn/ft-scl029")
        self.assertIn('class="lang-switch" href="/ft-scl029"', bn)
        self.assertIn("<span>English</span>", bn)

    def test_bangla_page_text_digits_and_links(self):
        bn = self.page("/bn/ft-scl029")
        self.assertIn("WaRa FT-SCL029 ক্যাবিনেট ড্রয়ার লক", bn)          # product name (model field)
        self.assertIn('<span class="price-now">৳১,৯৭৫</span>', bn)        # Bangla digits
        self.assertIn('<th scope="row">মডেল</th><td>FT-SCL029</td>', bn)  # specs
        self.assertIn("পাবলিক মোড আর প্রাইভেট মোডের পার্থক্য কী?", bn)     # FAQ
        self.assertIn(">কার্টে যোগ করুন<", bn.replace("</i> ", ">"))      # template string
        self.assertIn('href="/bn/products/"', bn)                           # links stay Bangla
        self.assertIn('class="lang-bn"', bn)

    def test_hreflang_alternates(self):
        en = self.page("/ft-scl029")
        self.assertIn('hreflang="en" href="https://warabd.com/ft-scl029"', en)
        self.assertIn('hreflang="bn" href="https://warabd.com/bn/ft-scl029"', en)
        self.assertIn('hreflang="x-default" href="https://warabd.com/ft-scl029"', en)

    def test_js_strings_are_translated_on_bangla_pages_only(self):
        bn = self.page("/bn/")
        catalog = json.loads(bn.split('id="wara-i18n" type="application/json">')[1].split("</script>")[0])
        self.assertEqual(catalog["Add to Cart"], "কার্টে যোগ করুন")
        self.assertEqual(catalog["Dhaka"], "ঢাকা")
        self.assertIn('lang = "bn"', bn)
        self.assertIn('checkout: "/bn/checkout/"', bn)
        en = self.page("/")
        self.assertIn('id="wara-i18n" type="application/json">{}</script>', en)

    def test_empty_bangla_falls_back_to_english(self):
        Product.objects.create(name="Only English Lock", slug="only-english", price=Decimal("100"), stock=1)
        bn = self.page("/bn/only-english")
        self.assertIn("Only English Lock", bn)

    def test_sitemap_lists_both_languages_and_robots_blocks_bangla_checkout(self):
        sitemap = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("<loc>https://warabd.com/bn/ft-scl029</loc>", sitemap)
        self.assertIn('hreflang="bn" href="https://warabd.com/bn/ft-scl029"', sitemap)
        robots = self.client.get("/robots.txt").content.decode()
        self.assertIn("Disallow: /bn/checkout/", robots)
        self.assertIn("Disallow: /checkout/", robots)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class BanglaCheckoutTests(TestCase):
    def setUp(self):
        Product.objects.create(name="Test Lock", slug="test-lock", price=Decimal("1000"), stock=5)

    def post(self, url, **overrides):
        data = {"name": "রহিম উদ্দিন", "phone": "০১৭১২৩৪৫৬৭৮", "district": "Dhaka", "thana": "Dhanmondi",
                "address": "বাড়ি ১২, রোড ৫, ধানমন্ডি", "zone": "inside", "payment": "cod",
                "lines": [{"id": "test-lock", "qty": 1}]}
        data.update(overrides)
        return self.client.post(url, json.dumps(data), content_type="application/json")

    def test_bangla_digit_phone_is_accepted_and_saved_in_ascii(self):
        r = self.post("/bn/api/checkout/")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Order.objects.get().phone, "01712345678")

    def test_errors_come_back_in_the_page_language(self):
        r = self.post("/bn/api/checkout/", phone="123")
        self.assertEqual(r.json()["errors"]["phone"], "সঠিক বাংলাদেশি মোবাইল নম্বর দিন (01XXXXXXXXX)।")
        r = self.post("/api/checkout/", phone="123")
        self.assertEqual(r.json()["errors"]["phone"], "Enter a valid Bangladeshi mobile number (01XXXXXXXXX).")

    def test_success_page_in_bangla(self):
        number = self.post("/bn/api/checkout/").json()["order_number"]
        bn = self.client.get(f"/bn/order/success/{number}/").content.decode()
        self.assertIn("ধন্যবাদ, রহিম উদ্দিন! আপনার অর্ডার নেওয়া হয়েছে।", bn)
        self.assertIn("ক্যাশ অন ডেলিভারি", bn)
        self.assertIn("ঢাকা, বাংলাদেশ", bn)


class TranslationFilesTests(TestCase):
    def test_every_string_has_a_bangla_translation_with_the_same_placeholders(self):
        import re

        import polib
        from django.conf import settings

        from .i18n_js import js_msgids
        from .management.commands.i18n_sync import collect

        po = polib.pofile(f"{settings.LOCALE_PATHS[0]}/bn/LC_MESSAGES/django.po")
        translated = {}
        for e in po:
            if e.obsolete or not e.translated():
                continue
            # plural entries (ngettext): check the "many" form
            translated[e.msgid] = e.msgstr_plural[1] if e.msgid_plural else e.msgstr
        wanted = set(collect()) | set(js_msgids())
        missing = sorted(wanted - set(translated))
        self.assertEqual(missing, [], "run: manage.py i18n_sync --missing")
        token = re.compile(r"%\(\w+\)s|%%|<[^>]+>")
        broken = [m for m, s in translated.items() if sorted(token.findall(m)) != sorted(token.findall(s))]
        self.assertEqual(broken, [])


class ProductAdminFormTests(TestCase):
    def test_text_list_fields_parse_and_render(self):
        from .forms import ApplicationsField, FaqField, FeaturesField, SpecsField, StepsField

        specs = SpecsField().clean("Model: FT-SCL029\nTime: 10:00 AM")
        self.assertEqual(specs, [["Model", "FT-SCL029"], ["Time", "10:00 AM"]])
        self.assertEqual(SpecsField().prepare_value(specs), "Model: FT-SCL029\nTime: 10:00 AM")
        with self.assertRaises(Exception):
            SpecsField().clean("no colon here")

        faq = FaqField().clean("Q: One?\nA: Yes.\n\nQ: Two?\nA: Line one\nline two")
        self.assertEqual(faq, [{"q": "One?", "a": "Yes."}, {"q": "Two?", "a": "Line one\nline two"}])
        with self.assertRaises(Exception):
            FaqField().clean("Q: No answer?")

        self.assertEqual(FeaturesField().clean("usb | USB keys | Backup"), [{"icon": "usb", "title": "USB keys", "text": "Backup"}])
        self.assertEqual(StepsField().clean("Mount | Screw it in"), [{"title": "Mount", "text": "Screw it in"}])
        self.assertEqual(
            ApplicationsField().clean("Works with: Cabinets, Drawers\nUsed in: Hotel"),
            {"compatible": ["Cabinets", "Drawers"], "places": ["Hotel"]},
        )
        self.assertEqual(SpecsField().clean(""), [])

    @override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
    def test_admin_save_keeps_lists_and_bangla_fields(self):
        from django.contrib.auth import get_user_model

        call_command("seed_wara", stdout=StringIO())
        admin_user = get_user_model().objects.create_superuser(email="admin@example.com", password="x-test-only")
        self.client.force_login(admin_user)
        product = Product.objects.get(slug="ft-scl029")
        url = f"/admin/web/product/{product.pk}/change/"
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Product Page Content")
        self.assertContains(r, 'name="faq_bn"')

        form = r.context["adminform"].form
        data = {}
        for name, field in form.fields.items():
            if name in ("image", "share_image"):  # file fields are not posted
                continue
            value = form[name].value()
            if not isinstance(value, str) and hasattr(field, "prepare_value"):
                value = field.prepare_value(value)
            if isinstance(value, bool):
                if value:
                    data[name] = "on"
                continue
            data[name] = "" if value is None else value
        data.update({"gallery-TOTAL_FORMS": "0", "gallery-INITIAL_FORMS": "0",
                     "gallery-MIN_NUM_FORMS": "0", "gallery-MAX_NUM_FORMS": "1000"})
        data["name_bn"] = "নতুন নাম"
        before = (product.specs_en, product.faq_en, product.highlights_bn, product.tags)

        r = self.client.post(url, data)
        self.assertEqual(r.status_code, 302, getattr(r.context and r.context["adminform"].form, "errors", ""))
        product.refresh_from_db()
        self.assertEqual((product.specs_en, product.faq_en, product.highlights_bn, product.tags), before)
        self.assertEqual(product.name_bn, "নতুন নাম")
        self.assertEqual(product.slug, "ft-scl029")


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class ProductUrlTests(TestCase):
    """Startech-style product links: /<slug> at the site root, old /products/<slug>/ redirects."""

    @classmethod
    def setUpTestData(cls):
        Product.objects.create(name="FT SCL029", slug="ft-scl029", price=Decimal("1000"), stock=5)

    def test_new_url_works_and_old_url_redirects_permanently(self):
        self.assertEqual(self.client.get("/ft-scl029").status_code, 200)
        r = self.client.get("/products/ft-scl029/?ref=fb")
        self.assertEqual((r.status_code, r["Location"]), (301, "/ft-scl029?ref=fb"))
        r = self.client.get("/bn/products/ft-scl029/")
        self.assertEqual((r.status_code, r["Location"]), (301, "/bn/ft-scl029"))

    def test_site_pages_are_not_mistaken_for_products(self):
        r = self.client.get("/about")
        self.assertEqual((r.status_code, r["Location"]), (301, "/about/"))
        self.assertEqual(self.client.get("/no-such-product").status_code, 404)

    def test_admin_slug_keeps_hyphens_and_avoids_page_names(self):
        from .forms import RESERVED_SLUGS, make_slug

        self.assertEqual(make_slug("Huion 420 H420", keep_case=True), "Huion-420-H420")
        self.assertIn("about", RESERVED_SLUGS)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class AdminPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        cls.admin = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")
        cls.product = Product.objects.create(name="Test Lock", slug="test-lock", price=Decimal("1000"), stock=2)

    def setUp(self):
        self.client.force_login(self.admin)

    def test_login_page_is_standalone_and_branded(self):
        self.client.logout()
        r = self.client.get("/admin/login/")
        self.assertContains(r, "Welcome back")
        self.assertContains(r, 'name="username"')
        self.assertNotContains(r, "admin-sidebar")          # no menu before signing in
        r = self.client.post("/admin/login/", {"username": "owner@example.com", "password": "wrong"})
        self.assertContains(r, "notice-error")
        r = self.client.post("/admin/login/?next=/admin/", {"username": "owner@example.com", "password": "x-test-only",
                                                           "next": "/admin/"})
        self.assertEqual((r.status_code, r["Location"]), (302, "/admin/"))

    def test_dashboard_shows_real_numbers(self):
        Order.objects.create(full_name="Rahim", phone="01712345678", address_line1="House 1", city="Dhaka",
                             thana="Dhanmondi", subtotal=Decimal("150000"), total=Decimal("150000"))
        r = self.client.get("/admin/")
        self.assertEqual(r.status_code, 200)
        body = r.content.decode()
        self.assertIn("Sales this month", body)
        self.assertIn("৳1,50,000", body)                    # BD lakh grouping
        self.assertIn("Low stock", body)
        self.assertIn('class="menu-badge"', body)           # pending-order badge in the sidebar

    def test_every_menu_screen_opens(self):
        for url in ["/admin/web/order/", "/admin/web/product/", "/admin/web/category/", "/admin/web/district/",
                    "/admin/web/thana/", "/admin/web/contentblock/", "/admin/web/page/", "/admin/web/contactmessage/",
                    "/admin/customers/customer/", "/admin/customers/smslog/", "/admin/customers/otpcode/",
                    "/admin/web/sitesettings/1/change/", "/admin/web/product/add/", "/admin/password_change/"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_datatables_json_search_sort_and_filter(self):
        r = self.client.get("/admin/web/district/")
        self.assertContains(r, 'id="adminDataTable"')
        r = self.client.get("/admin/web/district/datatable/", {
            "draw": "3", "start": "0", "length": "10", "search[value]": "gazi", "order[0][column]": "1",
            "order[0][dir]": "asc",
        })
        data = r.json()
        self.assertEqual(data["draw"], 3)
        self.assertEqual(data["recordsTotal"], 64)
        self.assertEqual(data["recordsFiltered"], 1)
        self.assertIn("Gazipur", "".join(data["data"][0]))
        self.assertIn('class="dt-fee"', "".join(data["data"][0]))
        # list_filter in the URL still applies (Dhaka division only)
        r = self.client.get("/admin/web/district/datatable/", {"draw": "1", "start": "0", "length": "100",
                                                                "division__exact": "Dhaka"})
        self.assertEqual(r.json()["recordsFiltered"], 13)

    def test_inline_fee_saving(self):
        from .models import District, Thana

        dhaka = District.objects.get(name_en="Dhaka")
        r = self.client.post(f"/admin/web/district/{dhaka.pk}/set-fee/", {"fee": "70"})
        self.assertEqual(r.json(), {"ok": True, "fee": 70})
        dhaka.refresh_from_db()
        self.assertEqual(dhaka.delivery_fee, 70)
        self.assertFalse(self.client.post(f"/admin/web/district/{dhaka.pk}/set-fee/", {"fee": "-5"}).json()["ok"])
        self.assertFalse(self.client.post(f"/admin/web/district/{dhaka.pk}/set-fee/", {"fee": ""}).json()["ok"])

        thana = Thana.objects.get(district=dhaka, name_en="Dhanmondi")
        self.client.post(f"/admin/web/thana/{thana.pk}/set-fee/", {"fee": "90"})
        thana.refresh_from_db()
        self.assertEqual(thana.effective_fee, 90)
        self.assertTrue(self.client.post(f"/admin/web/thana/{thana.pk}/set-fee/", {"fee": ""}).json()["ok"])
        thana.refresh_from_db()
        self.assertEqual((thana.delivery_fee, thana.effective_fee), (None, 70))   # back to the district's charge

        self.client.logout()
        r = self.client.post(f"/admin/web/district/{dhaka.pk}/set-fee/", {"fee": "1"})
        self.assertNotEqual(r.status_code, 200)
        dhaka.refresh_from_db()
        self.assertEqual(dhaka.delivery_fee, 70)
