"""manage.py add_ft_scl029: adds only the FT-SCL029 product, English + বাংলা, pictures on request."""

import io
import shutil
import tempfile
from decimal import Decimal
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from .models import Category, Product, SiteFeature, UseCase


def jpeg():
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 20, 40)).save(buf, format="JPEG")
    return buf.getvalue()


class FakePicture:
    def __init__(self, data, kind="image/jpeg"):
        self.data, self.headers = data, mock.Mock()
        self.headers.get_content_type.return_value = kind

    def read(self, limit=-1):
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class AddProductTests(TestCase):
    def setUp(self):
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, ignore_errors=True)
        override = override_settings(MEDIA_ROOT=media)
        override.enable()
        self.addCleanup(override.disable)

    def run_command(self, *args):
        out = io.StringIO()
        call_command("add_ft_scl029", *args, stdout=out)
        return out.getvalue()

    def test_adds_only_this_product_in_both_languages(self):
        old = Product.objects.create(name="Old", slug="old", price=Decimal("10"), stock=1, is_featured=True)
        out = self.run_command()
        p = Product.objects.get(slug="ft-scl029")
        self.assertIn("added", out)
        self.assertEqual((p.price, p.current_price), (Decimal("2250"), Decimal("2175")))
        self.assertTrue(p.name_bn and p.short_description_bn and p.faq_bn and p.specs_bn)
        self.assertIn(["Front body (keypad)", "Ø 50.5 mm × 12.3 mm"], p.specs_en)
        self.assertEqual(p.category.name_bn, "স্মার্ট ক্যাবিনেট লক")
        self.assertLessEqual(len(p.seo_title_en), 70)
        self.assertLessEqual(len(p.seo_description_en), 170)
        self.assertLessEqual(len(p.seo_description_bn), 170)
        self.assertEqual(p.seo_keywords.count(), 7)
        self.assertTrue(p.is_featured)
        old.refresh_from_db()
        self.assertFalse(old.is_featured)                                 # home page shows the new one
        self.assertEqual(Category.objects.count(), 1)
        self.assertFalse(SiteFeature.objects.exists() or UseCase.objects.exists())  # nothing else added
        self.assertIn("2,175", self.client.get("/ft-scl029").content.decode().replace("২,১৭৫", "2,175"))
        self.assertIn("ভিজিটর", self.client.get("/bn/ft-scl029").content.decode())

    def test_second_run_skips_and_update_keeps_stock(self):
        self.run_command()
        Product.objects.filter(slug="ft-scl029").update(stock=7, name_en="Changed")
        self.assertIn("skip", self.run_command())
        self.assertEqual(Product.objects.get(slug="ft-scl029").name_en, "Changed")
        self.run_command("--update")
        p = Product.objects.get(slug="ft-scl029")
        self.assertEqual((p.name_en, p.stock), ("WaRa FT-SCL029 Cabinet Drawer Lock", 7))
        self.assertEqual(Product.objects.count(), 1)

    def test_pictures_main_plus_three_gallery(self):
        with mock.patch("web.management.commands.add_ft_scl029.urllib.request.urlopen",
                        side_effect=lambda req, timeout: FakePicture(jpeg())) as opened:
            out = self.run_command("--pictures")
        p = Product.objects.get(slug="ft-scl029")
        self.assertTrue(p.image)
        self.assertEqual(p.gallery.count(), 3)
        self.assertIn("added 4 pictures", out)
        urls = [c.args[0].full_url for c in opened.call_args_list]
        self.assertTrue(all(u.startswith("https://admin.felnatech.com/") for u in urls))
        self.assertIn("skip  pictures", self.run_command("--pictures"))     # never doubled

    def test_bad_picture_keeps_the_product(self):
        with mock.patch("web.management.commands.add_ft_scl029.urllib.request.urlopen",
                        side_effect=lambda req, timeout: FakePicture(b"<html>", "text/html")):
            out = self.run_command("--pictures")
        self.assertIn("could not copy the pictures", out)
        p = Product.objects.get(slug="ft-scl029")
        self.assertFalse(p.image)
        self.assertFalse(p.gallery.exists())
