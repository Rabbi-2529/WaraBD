"""Add the WaRa FT-SCL029 lock to the shop: this one product, in English and বাংলা.

    python manage.py add_ft_scl029              # product + text + category + SEO
    python manage.py add_ft_scl029 --pictures   # ...and copy its 4 photos from felnatech.com
    python manage.py add_ft_scl029 --update     # it is already there: write this text over it

Price, sizes and unlock methods follow the felnatech.com product page (SOURCE below);
the wording is the shop's own FT-SCL029 text (seed_wara / _seed_wara_bn).
Nothing else in the shop is changed, except that this product becomes the one
shown on the home page ("Show on home page" moves to it, as in the admin).
"""

import copy
import io
import urllib.request
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import translation

from web.models import Category, Product, ProductImage, SeoKeyword

from . import _seed_wara_bn as bn
from .seed_wara import PRODUCT as SHOP_TEXT

SOURCE = "https://felnatech.com/pro/ft-scl029-cabinet-drawer-lock-with-visitor-password-changing-access"
PICTURE_URL = "https://admin.felnatech.com/storage/app/public/products/ft-scl029-felnatech-6609-{}.jpg"
MAIN_PICTURE = "ft"              # main image
GALLERY_PICTURES = ["1", "2", "3"]  # shown after the main image
MAX_PICTURE = 8 * 1024 * 1024

CATEGORY = ("smart-cabinet-lock", "Smart Cabinet Lock", bn.CATEGORY_BN["Smart Cabinet Lock"])
KEYWORDS = ["smart lock", "cabinet lock", "drawer lock", "keypad lock", "password lock",
            "smart lock bangladesh", "WaRa FT-SCL029"]
KEEP_ON_UPDATE = {"stock", "stock_status", "is_active"}  # the shop's own numbers stay


def english():
    data = copy.deepcopy(SHOP_TEXT)
    data.update({
        # felnatech.com: ৳2,250, on sale for ৳2,175 (৳75 off).
        "price": Decimal("2250"),
        "discount_type": "fixed",
        "discount_price": Decimal("75"),
        "seo_title": "WaRa FT-SCL029 Keypad Cabinet & Drawer Lock | WaRaBD",
        "seo_description": ("Buy the WaRa FT-SCL029 keypad lock for cabinets, drawers and lockers in Bangladesh. "
                            "Password & USB key unlock, visitor mode. Cash on delivery."),
    })
    data["specs"] = [[k, "Ø 50.5 mm × 12.3 mm" if k == "Front body (keypad)" else v] for k, v in data["specs"]]
    return data


def bangla():
    data = copy.deepcopy(bn.PRODUCT_BN)
    data["specs"] = [[k, "Ø ৫০.৫ মিমি × ১২.৩ মিমি" if k == "সামনের অংশ (কিপ্যাড)" else v] for k, v in data["specs"]]
    data["seo_title"] = "WaRa FT-SCL029 কিপ্যাড ক্যাবিনেট ও ড্রয়ার লক | WaRaBD"
    data["seo_description"] = ("বাংলাদেশে WaRa FT-SCL029 কিপ্যাড লক কিনুন — ক্যাবিনেট, ড্রয়ার ও লকারের জন্য। "
                               "পাসওয়ার্ড ও ইউএসবি চাবি, ভিজিটর মোড। ক্যাশ অন ডেলিভারি।")
    return data


def fetch_picture(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (shop catalogue import)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        if not response.headers.get_content_type().startswith("image/"):
            raise ValueError("the link did not give a picture")
        data = response.read(MAX_PICTURE + 1)
    if len(data) > MAX_PICTURE:
        raise ValueError("the picture is bigger than 8 MB")
    from PIL import Image

    Image.open(io.BytesIO(data)).verify()  # a real picture, not an error page
    return data


class Command(BaseCommand):
    help = "Add the WaRa FT-SCL029 product (English + বাংলা). --pictures also copies its photos."

    def add_arguments(self, parser):
        parser.add_argument("--pictures", action="store_true",
                            help="Also copy the 4 product photos from felnatech.com.")
        parser.add_argument("--update", action="store_true",
                            help="The product is already there: write this text over it.")

    def handle(self, *args, **options):
        en, bn_text = english(), bangla()
        slug = en["slug"]
        product = Product.objects.filter(slug=slug).first()
        if product and not options["update"]:
            self.stdout.write(f"  skip  /{slug} is already in the shop (use --update to write this text over it)")
        else:
            product = self._save(product, en, bn_text)
        if options["pictures"]:
            self._pictures(product)
        self.stdout.write(f"  page  /{slug}   (facts from {SOURCE})")

    def _save(self, product, en, bn_text):
        new = product is None
        with translation.override("en"), transaction.atomic():
            category = Category.objects.filter(Q(slug=CATEGORY[0]) | Q(name_en__iexact=CATEGORY[1])).first()
            if category is None:
                category = Category.objects.create(slug=CATEGORY[0], name=CATEGORY[1])
                self.stdout.write(self.style.SUCCESS(f"  added category {CATEGORY[1]}"))
            if not category.name_bn:
                category.name_bn = CATEGORY[2]
                category.save(update_fields=["name_bn"])

            product = product or Product(slug=en["slug"])
            for field, value in en.items():
                if field == "slug" or (not new and field in KEEP_ON_UPDATE):
                    continue
                setattr(product, field, value)
                if hasattr(product, f"{field}_en"):
                    setattr(product, f"{field}_en", value)
            for field, value in bn_text.items():
                setattr(product, f"{field}_bn", value)
            product.category = category
            product.save()
            product.seo_keywords.set(SeoKeyword.from_names(KEYWORDS))
            others = Product.objects.filter(is_featured=True).exclude(pk=product.pk).update(is_featured=False)
        verb = "added" if new else "updated"
        self.stdout.write(self.style.SUCCESS(
            f"  {verb} {product.name_en}: ৳{product.price:,.0f}, ৳{product.discount_price:,.0f} off "
            f"= ৳{product.current_price:,.0f}, stock {product.stock}"))
        if others:
            self.stdout.write(f"  moved \"Show on home page\" to this product ({others} other product untick{'s' if others > 1 else ''}ed)")
        return product

    def _pictures(self, product):
        if product.image or product.gallery.exists():
            self.stdout.write("  skip  pictures (this product already has pictures)")
            return
        names = [MAIN_PICTURE] + GALLERY_PICTURES
        try:
            pictures = [fetch_picture(PICTURE_URL.format(name)) for name in names]
        except Exception as error:  # network, not a picture, too big
            self.stdout.write(self.style.WARNING(
                f"  could not copy the pictures ({error}). Upload them in the admin instead."))
            return
        product.image.save(f"{product.slug}.jpg", ContentFile(pictures[0]), save=True)
        for order, data in enumerate(pictures[1:], 1):
            ProductImage(product=product, order=order).image.save(
                f"{product.slug}-{order}.jpg", ContentFile(data), save=True)
        self.stdout.write(self.style.SUCCESS(f"  added {len(pictures)} pictures (1 main + {len(pictures) - 1} gallery)"))
