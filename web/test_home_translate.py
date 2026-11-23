"""Home page product ("Show on home page") and the admin English -> বাংলা translate endpoint."""

import json
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from .models import Product, SiteSettings


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class HomeProductTests(TestCase):
    def test_no_products_no_demo_product(self):
        page = self.client.get("/").content.decode()
        self.assertNotIn("data-buy-now", page)
        self.assertNotIn('class="hero-photo"', page)
        self.assertIn("Browse products", page)
        js = open("web/static/web/js/products.js", encoding="utf-8").read()
        self.assertNotIn("felnatech", js)                    # no built-in demo catalogue

    def test_only_the_product_ticked_for_the_home_page_shows(self):
        Product.objects.create(name="Plain", slug="plain", price=Decimal("500"), stock=1)
        self.assertNotIn("data-buy-now", self.client.get("/").content.decode())
        Product.objects.create(name="Hero", slug="hero", price=Decimal("900"), stock=1, is_featured=True)
        page = self.client.get("/").content.decode()
        self.assertIn('data-buy-scope data-id="hero"', page)
        self.assertIn('class="hero-photo" href="/hero"', page)

    def test_ticking_another_product_takes_the_first_off(self):
        staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")
        self.client.force_login(staff)
        first = Product.objects.create(name="First", slug="first", price=Decimal("900"), stock=1, is_featured=True)
        second = Product.objects.create(name="Second", slug="second", price=Decimal("500"), stock=1)
        from web.admin import ProductAdmin
        from django.contrib.admin.sites import site
        from django.test import RequestFactory
        from django.contrib.messages.storage.fallback import FallbackStorage

        request = RequestFactory().post("/")
        request.user = staff
        request.session = self.client.session
        request._messages = FallbackStorage(request)
        second.is_featured = True
        ProductAdmin(Product, site).save_model(request, second, None, True)
        first.refresh_from_db()
        self.assertFalse(first.is_featured)
        self.assertTrue(Product.objects.get(pk=second.pk).is_featured)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class TranslateTests(TestCase):
    def setUp(self):
        self.staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")

    def post(self, data):
        return self.client.post("/admin/translate/", json.dumps(data), content_type="application/json")

    def test_staff_only(self):
        self.assertNotEqual(self.post({"texts": ["Hello"]}).status_code, 200)

    def test_without_key_says_where_to_add_it(self):
        self.client.force_login(self.staff)
        r = self.post({"texts": ["Hello"]})
        self.assertEqual(r.status_code, 400)
        self.assertIn("Site settings", r.json()["error"])

    def test_translates_with_the_key(self):
        site = SiteSettings.load()
        site.google_translate_api_key = "test-key"
        site.save()
        self.client.force_login(self.staff)
        answer = {"data": {"translations": [{"translatedText": "স্মার্ট লক"}, {"translatedText": "চাবি &amp; কোড"}]}}
        with mock.patch("web.translate.urllib.request.urlopen", return_value=FakeResponse(answer)) as opened:
            r = self.post({"texts": ["Smart lock", "Key & code"], "format": "text"})
        self.assertEqual(r.json(), {"translations": ["স্মার্ট লক", "চাবি & কোড"]})
        sent = opened.call_args[0][0]
        self.assertIn("key=test-key", sent.full_url)
        self.assertEqual(json.loads(sent.data)["target"], "bn")

    def test_admin_pages_load_the_buttons(self):
        self.client.force_login(self.staff)
        page = self.client.get("/admin/web/product/add/").content.decode()
        self.assertIn('name="wara-translate"', page)
        self.assertIn("admin/js/wara-translate.js", page)


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class ShortDescriptionEditorTests(TestCase):
    def test_editor_on_form_formatting_on_page_plain_on_cards(self):
        staff = get_user_model().objects.create_superuser(email="owner@example.com", password="x-test-only")
        self.client.force_login(staff)
        form = self.client.get("/admin/web/product/add/").content.decode()
        self.assertEqual(form.count('data-rich-editor="compact"'), 2)        # English + বাংলা short description
        Product.objects.create(name="Lock", slug="lock", price=Decimal("900"), stock=1, is_featured=True,
                               short_description="<p>Keyless <strong>cabinet</strong> lock.</p><script>x()</script>")
        page = self.client.get("/lock").content.decode()
        self.assertIn('<p class="p-short">Keyless <strong>cabinet</strong> lock.</p>', page)
        self.assertNotIn("x()", page)
        shop = self.client.get("/products/").content.decode()
        self.assertIn('"short": "Keyless cabinet lock."', shop)
