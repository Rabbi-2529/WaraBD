"""manage.py clear_catalog: dry run by default, then deletes the catalogue and its pictures."""

import io
import os
import shutil
import tempfile
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings

from customers.models import Customer

from .models import Category, Order, OrderItem, Page, PortfolioProject, Product, ProductImage, SiteSettings, UseCase


class ClearCatalogTests(TestCase):
    def setUp(self):
        self.media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        cat = Category.objects.create(name="Locks", slug="locks")
        product = Product.objects.create(name="Lock", slug="lock", price=Decimal("1000"), stock=3, category=cat)
        product.image.save("lock.jpg", ContentFile(b"jpg"), save=True)
        gallery = ProductImage(product=product)
        gallery.image.save("lock-2.jpg", ContentFile(b"jpg"), save=True)
        order = Order.objects.create(full_name="Rahim", phone="01712345678", address_line1="House 1", city="Dhaka")
        OrderItem.objects.create(order=order, product=product, quantity=1, price=Decimal("1000"))
        UseCase.objects.create(title="Home", place="Bedroom", text="Wardrobe", category=UseCase._meta.get_field("category").choices[0][0])
        PortfolioProject.objects.create(title="Hotel", slug="hotel")
        Customer.objects.create(phone="01712345678", name="Rahim")
        Page.objects.create(slug="terms", title="Terms")
        SiteSettings.load()
        self.files = [product.image.path, gallery.image.path]

    def run_command(self, *args):
        out = io.StringIO()
        call_command("clear_catalog", *args, stdout=out)
        return out.getvalue()

    def test_dry_run_deletes_nothing(self):
        out = self.run_command()
        self.assertIn("Nothing deleted", out)
        self.assertIn("products", out)
        self.assertEqual((Product.objects.count(), Order.objects.count()), (1, 1))

    def test_yes_deletes_catalogue_and_pictures_but_keeps_the_rest(self):
        out = self.run_command("--yes")
        self.assertIn("Deleted", out)
        for model in (OrderItem, Order, ProductImage, Product, Category, UseCase, PortfolioProject):
            self.assertFalse(model.objects.exists(), model.__name__)
        for path in self.files:
            self.assertFalse(os.path.exists(path), path)
        self.assertTrue(Customer.objects.exists())
        self.assertTrue(Page.objects.exists())
        self.assertTrue(SiteSettings.objects.exists())
