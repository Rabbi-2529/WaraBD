"""Phase 6: titles, descriptions, canonical links, share cards and structured data."""

import json
import re
from decimal import Decimal

from django.test import TestCase, override_settings

from .models import Page, PageSeo, Product


def jsonld(body):
    return [json.loads(m) for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.S)]


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"], SITE_URL="https://warabd.com")
class SeoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.product = Product.objects.create(
            name="Smart Lock", slug="huion-420-H420", model_number="H420", price=Decimal("2050"),
            discount_type="fixed", discount_price=Decimal("75"), stock=4, short_description="Keyless cabinet lock.",
        )

    def test_product_share_card_and_structured_data(self):
        body = self.client.get("/huion-420-H420").content.decode()
        self.assertIn("<title>Smart Lock (H420) | WaRa BD</title>", body)
        self.assertIn('<link rel="canonical" href="https://warabd.com/huion-420-H420">', body)
        self.assertIn('<meta property="og:type" content="product">', body)
        self.assertIn('<meta property="og:title" content="Smart Lock (H420) | WaRa BD">', body)
        self.assertIn('<meta property="og:description" content="Keyless cabinet lock.">', body)
        data = jsonld(body)
        product = next(d for d in data if d["@type"] == "Product")
        self.assertEqual(product["offers"]["price"], "1975.00")
        self.assertEqual(product["offers"]["priceCurrency"], "BDT")
        self.assertEqual(product["offers"]["availability"], "https://schema.org/InStock")
        self.assertTrue(any(d["@type"] == "BreadcrumbList" for d in data))

    def test_admin_seo_fields_win(self):
        Product.objects.filter(pk=self.product.pk).update(
            seo_title_en="Buy Smart Lock in Bangladesh", seo_description_en="Best price, cash on delivery.",
            seo_title_bn="স্মার্ট লক কিনুন",
        )
        en = self.client.get("/huion-420-H420").content.decode()
        self.assertIn("<title>Buy Smart Lock in Bangladesh</title>", en)
        self.assertIn('content="Best price, cash on delivery."', en)
        bn = self.client.get("/bn/huion-420-H420").content.decode()
        self.assertIn("<title>স্মার্ট লক কিনুন</title>", bn)
        self.assertIn('<link rel="canonical" href="https://warabd.com/bn/huion-420-H420">', bn)
        self.assertIn('<meta property="og:locale" content="bn_BD">', bn)

    def test_fixed_pages_use_page_seo_rows(self):
        about = self.client.get("/about/").content.decode()
        self.assertIn("<title>About Us | WaRa BD</title>", about)
        PageSeo.objects.filter(page="about").update(title_en="About WaRa BD — smart locks", description_en="Who we are.")
        about = self.client.get("/about/").content.decode()
        self.assertIn("<title>About WaRa BD — smart locks</title>", about)
        self.assertIn('<meta property="og:description" content="Who we are.">', about)
        bn = self.client.get("/bn/about/").content.decode()
        self.assertIn("<title>About WaRa BD — smart locks</title>", bn)   # empty Bangla falls back to English

    def test_home_has_organization_and_noindex_switch(self):
        home = self.client.get("/").content.decode()
        types = [d["@type"] for d in jsonld(home)]
        self.assertEqual(types, ["Organization", "WebSite"])
        self.assertNotIn('name="robots"', home)
        PageSeo.objects.filter(page="contact").update(noindex=True)
        self.assertIn('<meta name="robots" content="noindex">', self.client.get("/contact/").content.decode())

    def test_policy_page_seo(self):
        Page.objects.create(slug="returns", title="Returns", intro="7-day returns.", seo_title="Return policy — WaRa BD")
        body = self.client.get("/page/returns/").content.decode()
        self.assertIn("<title>Return policy — WaRa BD</title>", body)
        self.assertIn('<meta property="og:description" content="7-day returns.">', body)

    def test_checkout_stays_out_of_google(self):
        self.assertIn('<meta name="robots" content="noindex">', self.client.get("/checkout/").content.decode())
