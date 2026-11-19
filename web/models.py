# web/models.py
from django.conf import settings as django_settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils import timezone
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
            (STOCK_IN, "In stock"),
            (STOCK_OUT, "Out of stock"),
            (STOCK_UPCOMING, "Upcoming"),
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
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_SHIPPED, "Shipped"),
        (STATUS_DELIVERED, "Delivered"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PAYMENT_UNPAID = "unpaid"
    PAYMENT_VERIFYING = "verifying"
    PAYMENT_PAID = "paid"
    PAYMENT_CHOICES = [
        (PAYMENT_UNPAID, "Unpaid"),
        # bKash / Nagad: customer sent money and gave a TrxID; staff must
        # check it in the merchant app before marking the order paid.
        (PAYMENT_VERIFYING, "Awaiting verification"),
        (PAYMENT_PAID, "Paid"),
        ("refunded", "Refunded"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cod", "Cash on Delivery"),
        ("bkash", "bKash"),
        ("nagad", "Nagad"),
    ]
    MOBILE_PAYMENT_METHODS = ("bkash", "nagad")

    ZONE_INSIDE = "inside"
    ZONE_OUTSIDE = "outside"
    ZONE_CHOICES = [
        (ZONE_INSIDE, "Inside Dhaka"),
        (ZONE_OUTSIDE, "Outside Dhaka"),
    ]

    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
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