# web/models.py
from decimal import Decimal

from django.conf import settings as django_settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import uuid


# ─────────────────────────────────────────────────────────────
# 1. CATEGORY
# ─────────────────────────────────────────────────────────────
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────
# 2. PRODUCT
# ─────────────────────────────────────────────────────────────
class Product(models.Model):
    STOCK_IN = "in-stock"
    STOCK_OUT = "out-of-stock"
    STOCK_UPCOMING = "upcoming"

    DISCOUNT_CHOICES = [
        ("none", "No Discount"),
        ("percent", "Percentage (%)"),
        ("fixed", "Fixed Amount (৳)"),
    ]

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="products"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    subtitle = models.CharField(max_length=200, blank=True, default="")
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    description_title = models.CharField(max_length=200, blank=True, default="")

    brand = models.CharField(max_length=100, default="WaRa", blank=True)
    model_number = models.CharField(max_length=100, blank=True, default="")
    sku = models.CharField(max_length=100, blank=True, default="")
    color = models.CharField(max_length=50, blank=True, default="")
    warranty = models.CharField(max_length=100, blank=True, default="1 Year")
    
    sub_category = models.CharField(max_length=100, blank=True, default="")

    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    discount_type = models.CharField(max_length=20, choices=DISCOUNT_CHOICES, default="none")
    
    image = models.ImageField(upload_to="products/", blank=True, null=True)

    stock = models.PositiveIntegerField(default=0)
    stock_status = models.CharField(
        max_length=20,
        choices=[
            (STOCK_IN, _("In stock")),
            (STOCK_OUT, _("Out of stock")),
            (STOCK_UPCOMING, _("Upcoming")),
        ],
        default=STOCK_IN,
        help_text="Display status. 'stock' count is used for decrement logic.",
    )
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)

    tags = models.JSONField(default=list, blank=True, help_text='e.g. ["FCC", "CE", "RoHS"]')
    highlights = models.JSONField(default=list, blank=True, help_text='e.g. ["Password unlock", "Motorized"]')
    specs = models.JSONField(default=list, blank=True, help_text="List of [key, value] pairs.")
    features = models.JSONField(default=list, blank=True, help_text="List of {icon, title, text}.")
    applications = models.JSONField(default=dict, blank=True, help_text='{"compatible": [], "places": []}')
    steps = models.JSONField(default=list, blank=True, help_text="List of {title, text}.")
    faq = models.JSONField(default=list, blank=True, help_text="List of {q, a} pairs.")

    # SEO & sharing (Phase 6)
    seo_title = models.CharField("SEO title", max_length=70, blank=True,
                                 help_text="Google / share title, up to ~60 characters. Leave empty to build it from the name and description.")
    seo_description = models.CharField("SEO description", max_length=170, blank=True,
                                       help_text="Google / share text, up to ~155 characters. Leave empty to build it from the name and description.")
    share_image = models.ImageField("Share image", upload_to="seo/products/", blank=True, null=True,
                                    help_text="Picture shown on Facebook / WhatsApp. Empty = the main product image. 1200×630 works best.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.image and hasattr(self.image, "file") and not getattr(self.image, "_committed", False):
            try:
                from PIL import Image
                import io
                from django.core.files.base import ContentFile
                if self.image.size > 500 * 1024:
                    img = Image.open(self.image)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    img.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
                    buf = io.BytesIO()
                    img.save(buf, format="JPEG", quality=85, optimize=True)
                    image_name = self.image.name or "image"
                    self.image = ContentFile(
                        buf.getvalue(), name=image_name.rsplit(".", 1)[0] + ".jpg"
                    )
            except Exception:
                pass
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("web:product_detail", kwargs={"slug": self.slug})

    @property
    def current_price(self):
        if self.discount_type == "percent" and self.discount_price:
            discount_amount = self.price * (self.discount_price / 100)
            return self.price - discount_amount
        elif self.discount_type == "fixed" and self.discount_price:
            return max(0, self.price - self.discount_price)
        elif self.discount_price:
            return self.discount_price
        return self.price

    def __str__(self):
        return self.name


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="gallery")
    image = models.ImageField(upload_to="products/gallery/")
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Lower = shown first")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Gallery image"
        verbose_name_plural = "Gallery images"

    def __str__(self):
        return f"{self.product.name} — {self.caption or 'image'}"


# ─────────────────────────────────────────────────────────────
# 3. PORTFOLIO, CONTACT & ORDERS
# ─────────────────────────────────────────────────────────────
class PortfolioProject(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    client = models.CharField(max_length=150, blank=True)
    short_description = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="portfolio/", blank=True, null=True)
    project_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class ContactMessage(models.Model):
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject}"


class Order(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_PENDING, _("Pending")),
        (STATUS_PAID, _("Paid")),
        (STATUS_SHIPPED, _("Shipped")),
        (STATUS_DELIVERED, _("Delivered")),
        (STATUS_CANCELLED, _("Cancelled")),
    ]

    PAYMENT_UNPAID = "unpaid"
    PAYMENT_VERIFYING = "verifying"
    PAYMENT_PAID = "paid"
    PAYMENT_CHOICES = [
        (PAYMENT_UNPAID, _("Unpaid")),
        # bKash / Nagad: customer sent money and gave a TrxID; staff must
        # check it in the merchant app before marking the order paid.
        (PAYMENT_VERIFYING, _("Awaiting verification")),
        (PAYMENT_PAID, _("Paid")),
        ("refunded", _("Refunded")),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cod", _("Cash on Delivery")),
        ("bkash", _("bKash")),
        ("nagad", _("Nagad")),
    ]
    MOBILE_PAYMENT_METHODS = ("bkash", "nagad")

    ZONE_INSIDE = "inside"
    ZONE_OUTSIDE = "outside"
    ZONE_CHOICES = [
        (ZONE_INSIDE, _("Inside Dhaka")),
        (ZONE_OUTSIDE, _("Outside Dhaka")),
    ]

    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )
    # Shop customer (phone login) who placed the order, if logged in or verified.
    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
    )

    order_number = models.CharField(max_length=32, unique=True, editable=True, blank=True)
    
    full_name = models.CharField(max_length=200)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, help_text="Bangladeshi mobile, saved as 01XXXXXXXXX.")
    address_line1 = models.CharField(max_length=255)
    address_line2 = models.CharField(max_length=255, blank=True)
    city = models.CharField("District", max_length=100)
    thana = models.CharField("Thana / upazila", max_length=80, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    country = models.CharField(max_length=100, default="Bangladesh")
    delivery_zone = models.CharField(max_length=10, choices=ZONE_CHOICES, default=ZONE_INSIDE)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping = models.DecimalField("Delivery fee", max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default=PAYMENT_UNPAID)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cod")
    payment_sender = models.CharField("Sender number", max_length=20, blank=True)
    transaction_id = models.CharField("Transaction ID (TrxID)", max_length=50, blank=True)

    # Courier (Phase 5): filled by "Send to courier", or typed by staff for any other courier.
    courier = models.CharField("Courier", max_length=30, blank=True,
                               help_text="steadfast / pathao when booked from here, or any courier name typed by hand.")
    courier_consignment_id = models.CharField("Consignment ID", max_length=60, blank=True)
    courier_tracking_code = models.CharField("Tracking code", max_length=60, blank=True)
    courier_tracking_url = models.URLField("Tracking link", blank=True,
                                           help_text="Only for couriers that are not connected (Steadfast / Pathao links are made automatically).")
    courier_status = models.CharField("Courier status", max_length=60, blank=True)
    courier_sent_at = models.DateTimeField("Sent to courier", null=True, blank=True)
    courier_checked_at = models.DateTimeField("Status checked", null=True, blank=True)

    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:10].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} — {self.full_name}"


    @property
    def courier_display(self):
        from .courier import courier_label
        return courier_label(self)

    @property
    def courier_link(self):
        from .courier import tracking_url
        return tracking_url(self)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"

    @property
    def line_total(self):
        return self.price * self.quantity


# ─────────────────────────────────────────────────────────────
# 4. CMS & SITE SETTINGS
# ─────────────────────────────────────────────────────────────
class SiteSettings(models.Model):
    name = models.CharField(max_length=100, default="WaRa BD")
    phone = models.CharField(max_length=50, default="+880 1958-666999")
    whatsapp = models.CharField(max_length=50, default="8801958666999")
    email = models.EmailField(default="info@warabd.com")
    address = models.CharField(max_length=200, default="Dhaka, Bangladesh")
    map_query = models.CharField(max_length=200, default="Dhaka, Bangladesh")
    hours = models.CharField(max_length=100, default="Saturday – Thursday, 10:00 AM – 8:00 PM")
    announcement = models.CharField(max_length=200, default="In stock · Cash on delivery all over Bangladesh")
    delivery_inside_fee = models.PositiveIntegerField(default=60, help_text="Fee in BDT (Inside Dhaka)")
    delivery_outside_fee = models.PositiveIntegerField(default=120, help_text="Fee in BDT (Outside Dhaka)")
    delivery_inside_eta = models.CharField(max_length=50, default="1–2 working days")
    delivery_outside_eta = models.CharField(max_length=50, default="2–4 working days")
    bkash_number = models.CharField(max_length=50, default="01958-666999")
    nagad_number = models.CharField(max_length=50, default="01958-666999")
    facebook = models.CharField(max_length=200, blank=True, default="#")
    instagram = models.CharField(max_length=200, blank=True, default="#")
    youtube = models.CharField(max_length=200, blank=True, default="#")
    meta_title = models.CharField(max_length=200, default="WaRa BD — Keyless Cabinet Locks")
    meta_description = models.TextField(default="Buy the WaRa FT-SCL029 keypad cabinet & drawer lock...")

    # Branding (Phase 3) — empty = the built-in "WaRa BD" text logo / default icon.
    logo = models.ImageField(upload_to="site/", blank=True, null=True,
                             help_text="Shown in the header and footer instead of the text logo. PNG or SVG, about 160×48.")
    favicon = models.FileField(upload_to="site/", blank=True, null=True,
                               help_text="Browser tab icon: SVG, PNG or ICO.")

    # Phone login / OTP (Phase 4)
    otp_for_orders = models.BooleanField(
        default=True,
        help_text="Guests must enter an SMS code before an order is placed. "
                  "Logged-in customers and numbers already verified today skip it.",
    )
    sms_daily_limit_per_number = models.PositiveSmallIntegerField(
        default=3,
        help_text="Most SMS codes one mobile number can receive per day (resets at midnight, Dhaka time). "
                  "Set 1 to never send the same number a second SMS on the same day.",
    )
    sms_daily_limit_per_ip = models.PositiveSmallIntegerField(
        default=10, help_text="Most SMS codes requested from one internet connection per day (stops SMS abuse).",
    )
    otp_valid_minutes = models.PositiveSmallIntegerField(default=5)
    otp_resend_seconds = models.PositiveSmallIntegerField(default=60, help_text="Wait before 'Resend code' is allowed.")
    otp_max_attempts = models.PositiveSmallIntegerField(default=5, help_text="Wrong tries before the code stops working.")
    otp_sms_text = models.CharField(
        max_length=160,
        default="{code} is your WaRa BD verification code. It expires in {minutes} minutes. Do not share it.",
        help_text="Keep it in English letters to fit one SMS. {code} and {minutes} are filled in.",
    )

    # SMS gateway (IGL Web SMS: GET/POST api_key, contacts, senderid, msg)
    sms_enabled = models.BooleanField(
        "Send real SMS",
        default=False,
        help_text="Tick after filling in the API key and sender ID. While off, the site runs in test mode: "
                  "no SMS is sent (the code is shown on screen only when DEBUG is on).",
    )
    sms_api_url = models.URLField("SMS API URL", default="http://sms.iglweb.com/api/v1/send")
    sms_api_key = models.CharField("SMS API key", max_length=200, blank=True)
    sms_sender_id = models.CharField("SMS sender ID", max_length=50, blank=True,
                                     help_text="Your approved sender ID from the SMS provider.")
    SMS_NUMBER_FORMATS = [("880", "8801XXXXXXXXX (with country code)"), ("0", "01XXXXXXXXX")]
    sms_number_format = models.CharField("Number format", max_length=3, choices=SMS_NUMBER_FORMATS,
                                         default="880", help_text="How mobile numbers are sent to the API (contacts=…).")

    # Courier (Phase 5)
    COURIER_CHOICES = [("", "Not connected (type tracking codes by hand)"),
                       ("steadfast", "Steadfast Courier"), ("pathao", "Pathao Courier")]
    courier_provider = models.CharField("Courier", max_length=20, choices=COURIER_CHOICES, blank=True, default="",
                                        help_text="Orders are booked with this courier when you press “Send to courier”.")
    steadfast_api_url = models.URLField("Steadfast API URL", default="https://portal.packzy.com/api/v1")
    steadfast_api_key = models.CharField("Steadfast API key", max_length=200, blank=True)
    steadfast_secret_key = models.CharField("Steadfast secret key", max_length=200, blank=True)
    pathao_api_url = models.URLField("Pathao API URL", default="https://api-hermes.pathao.com",
                                     help_text="Sandbox for testing: https://courier-api-sandbox.pathao.com")
    pathao_client_id = models.CharField("Pathao client ID", max_length=100, blank=True)
    pathao_client_secret = models.CharField("Pathao client secret", max_length=200, blank=True)
    pathao_username = models.CharField("Pathao merchant email", max_length=150, blank=True)
    pathao_password = models.CharField("Pathao merchant password", max_length=150, blank=True)
    pathao_store_id = models.CharField("Pathao store ID", max_length=30, blank=True)
    pathao_item_weight = models.DecimalField("Parcel weight (kg)", max_digits=5, decimal_places=2, default=Decimal("0.5"))
    courier_sms_on_dispatch = models.BooleanField(
        "SMS the tracking code", default=True,
        help_text="When a parcel is booked, send the customer one SMS with the tracking code. "
                  "Skipped if that number already received an SMS today.",
    )
    courier_dispatch_sms_text = models.CharField(
        "Dispatch SMS", max_length=160,
        default="Your WaRa BD order {order} is on the way with {courier}. Tracking code: {tracking}",
        help_text="{order}, {courier} and {tracking} are filled in.",
    )

    # SEO & sharing (Phase 6)
    share_image = models.ImageField(
        "Default share image", upload_to="seo/", blank=True, null=True,
        help_text="Shown when a page is shared on Facebook / WhatsApp and has no image of its own. 1200×630 works best.",
    )
    google_site_verification = models.CharField(
        max_length=100, blank=True, help_text="Only the code from Google Search Console's HTML tag (content=\"…\").",
    )

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def __str__(self):
        return self.name or "Site Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class SiteHighlight(models.Model):
    title = models.CharField(max_length=100)
    subtitle = models.CharField(max_length=200, blank=True)
    icon = models.CharField(max_length=50, default="star")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class SiteFeature(models.Model):
    SECTION_CHOICES = [
        ("home_mode", "Home Mode"),
        ("home_why", "Home Why"),
        ("about_mission", "About Mission"),
        ("about_why", "About Why"),
    ]
    title = models.CharField(max_length=100)
    section = models.CharField(max_length=50, choices=SECTION_CHOICES)
    icon = models.CharField(max_length=50, default="check")
    text = models.TextField(
        blank=True,
        help_text="For Home Mode cards, write one bullet point per line.",
    )
    badge = models.CharField(
        max_length=50, blank=True,
        help_text="Home Mode only — small label next to the title, e.g. 'Visitor password'.",
    )
    best_for = models.CharField(
        max_length=200, blank=True,
        help_text="Home Mode only — e.g. 'gyms, spas, hotels, schools, malls'.",
    )
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["section", "order"]

    def __str__(self):
        return f"[{self.get_section_display()}] {self.title}"


class UseCase(models.Model):
    CATEGORY_CHOICES = [
        ("home", "Home"),
        ("office", "Office"),
        ("hospitality", "Hospitality & Health"),
        ("public", "Public Spaces"),
        ("commercial", "Commercial"),
    ]
    MODE_CHOICES = [("private", "Private Mode"), ("public", "Public Mode")]

    title = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    mode = models.CharField(max_length=20, choices=MODE_CHOICES, default="private")
    place = models.CharField(max_length=100, blank=True)
    text = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="box")
    tone = models.CharField(max_length=20, blank=True, default="")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


class TimelineStep(models.Model):
    title = models.CharField(max_length=100)
    text = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="cart")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title

# ─────────────────────────────────────────────────────────────
# 5. PAGE TEXT, PAGE LISTS & POLICY PAGES (Phase 3)
# ─────────────────────────────────────────────────────────────
class ContentBlock(models.Model):
    """One editable piece of storefront text, e.g. "home.hero.title".

    Templates use {% cms "home.hero.title" %}default{% endcms %}: the value
    saved here (English or Bangla, by page language) replaces the default.
    Rows are created by `manage.py sync_content`.
    """

    PAGE_CHOICES = [
        ("home", "Home"),
        ("about", "About"),
        ("portfolio", "Portfolio"),
        ("contact", "Contact"),
        ("products", "Products"),
        ("cart", "Cart & checkout"),
        ("footer", "Header & footer"),
    ]

    key = models.CharField(max_length=100, unique=True)
    page = models.CharField(max_length=20, choices=PAGE_CHOICES, db_index=True)
    label = models.CharField(max_length=200, blank=True, help_text="Where this text appears on the page.")
    value = models.TextField(blank=True, help_text="Leave empty to show the built-in text.")
    allow_html = models.BooleanField(
        default=False,
        help_text="Keeps simple tags such as <strong> or the coloured <span> words in headings.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["page", "key"]
        verbose_name = "Page text"
        verbose_name_plural = "Page text"

    def __str__(self):
        return self.key


class ContentItem(models.Model):
    """A row in a repeatable list on a page: tiles, steps, numbers, bullet points."""

    GROUP_CHOICES = [
        ("home.hero_trust", "Home · badges under the hero (icon + text)"),
        ("home.spotlight_points", "Home · spotlight bullet points"),
        ("home.applications", "Home · 'where it works' tiles (icon + title)"),
        ("home.steps", "Home · setup steps (title + text)"),
        ("home.stats", "Home · numbers (value + title)"),
        ("about.story_points", "About · story check list"),
        ("portfolio.stats", "Portfolio · 'at a glance' numbers (value + title)"),
        ("contact.subjects", "Contact · message topics"),
        ("cart.trust", "Cart · trust badges (icon + text)"),
    ]

    group = models.CharField(max_length=40, choices=GROUP_CHOICES, db_index=True)
    icon = models.CharField(max_length=50, blank=True, help_text="e.g. shield, truck, award, cash, check, lock")
    value = models.CharField(max_length=60, blank=True, help_text="Big number for the stats rows, e.g. '1 + 3'.")
    title = models.CharField(max_length=200, blank=True)
    text = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["group", "order", "id"]
        verbose_name = "Page list item"
        verbose_name_plural = "Page list items"

    def __str__(self):
        return f"{self.get_group_display()} — {self.title or self.value or self.text[:40]}"


class Page(models.Model):
    """Information / policy page at /page/<slug>/ (privacy, terms, returns, FAQ …)."""

    KIND_TEXT = "text"
    KIND_FAQ = "faq"
    KIND_CHOICES = [(KIND_TEXT, "Text page"), (KIND_FAQ, "Questions & answers")]

    slug = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=200)
    intro = models.CharField(max_length=300, blank=True, help_text="One line under the title.")
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_TEXT)
    body = models.TextField(
        blank=True,
        help_text=(
            "Text page: write freely — headings, lists, tables and pictures from the editor toolbar. "
            "Questions & answers: one line 'Q: …', the next line 'A: …', for each question."
        ),
    )
    meta_description = models.CharField(max_length=300, blank=True)
    seo_title = models.CharField("SEO title", max_length=70, blank=True,
                                 help_text="Empty = “page title | shop name”.")
    share_image = models.ImageField("Share image", upload_to="seo/pages/", blank=True, null=True,
                                    help_text="Empty = the default share image from Site settings.")
    show_in_footer = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Policy / info page"
        verbose_name_plural = "Policy / info pages"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("web:page", kwargs={"slug": self.slug})


class PageSeo(models.Model):
    """Google title / description and share picture for the fixed site pages (home, products …)."""

    PAGES = [
        ("home", "Home page"),
        ("product_list", "Products (shop) page"),
        ("portfolio", "Portfolio page"),
        ("about", "About us page"),
        ("contact", "Contact page"),
    ]
    page = models.CharField(max_length=40, choices=PAGES, unique=True)
    title = models.CharField("SEO title", max_length=70, blank=True, help_text="Empty = the built-in title.")
    description = models.CharField("SEO description", max_length=170, blank=True,
                                   help_text="Empty = the built-in description.")
    share_image = models.ImageField("Share image", upload_to="seo/pages/", blank=True, null=True,
                                    help_text="Empty = the default share image from Site settings. 1200×630 works best.")
    noindex = models.BooleanField("Hide from Google", default=False)

    class Meta:
        ordering = ["id"]
        verbose_name = "Page SEO"
        verbose_name_plural = "Page SEO"

    def __str__(self):
        return self.get_page_display()


# ─────────────────────────────────────────────────────────────
# 6. DISTRICTS, THANAS & DELIVERY CHARGES
# ─────────────────────────────────────────────────────────────
class District(models.Model):
    """One of Bangladesh's 64 districts with its delivery charge.

    `name_en` is the canonical spelling stored on orders; the checkout picks
    the charge automatically from the district (and thana, if it has its own).
    """

    name = models.CharField(max_length=40, unique=True)
    division = models.CharField(max_length=20)
    delivery_fee = models.PositiveIntegerField("Delivery charge (৳)", default=120)
    delivery_eta = models.CharField("Delivery time", max_length=50, blank=True,
                                    help_text="e.g. 2–4 working days")
    is_active = models.BooleanField(default=True, help_text="Untick to stop delivering to this district.")
    pathao_city_id = models.PositiveIntegerField("Pathao city no.", null=True, blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "District delivery charge"
        verbose_name_plural = "Delivery charges (districts)"

    def __str__(self):
        return self.name


class Thana(models.Model):
    """Thana / upazila inside a district. A thana can have its own charge."""

    district = models.ForeignKey(District, on_delete=models.CASCADE, related_name="thanas")
    name = models.CharField(max_length=80)
    delivery_fee = models.PositiveIntegerField(
        "Own delivery charge (৳)", null=True, blank=True,
        help_text="Leave empty to use the district's charge.",
    )
    pathao_zone_id = models.PositiveIntegerField("Pathao zone no.", null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["district__name", "name"]
        unique_together = [("district", "name")]
        verbose_name = "Thana / upazila"
        verbose_name_plural = "Thanas / upazilas"

    def __str__(self):
        return f"{self.name}, {self.district}"

    @property
    def effective_fee(self):
        return self.delivery_fee if self.delivery_fee is not None else self.district.delivery_fee
