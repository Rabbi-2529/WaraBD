
# web/views.py

import json
import logging
import re

from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import product_page
from .bd import clean_bd_district, normalize_bd_phone
from .cart import Cart
from .emails import send_admin_new_order, send_order_confirmation
from .forms import CheckoutForm, ContactForm
from .models import (
    Category,
    Order,
    PortfolioProject,
    Product,
    SiteHighlight,
    SiteFeature,
    TimelineStep,
    UseCase,
    ContactMessage,
)
from .services import cancel_order, place_order


logger = logging.getLogger(__name__)


# ==============================================================================
# PRODUCT DATA HELPERS
# ==============================================================================

def _get_image_url(image_field):
    """
    Safely return an image URL.
    Returns an empty string when no image is uploaded.
    """
    if not image_field:
        return ""

    try:
        return image_field.url
    except (ValueError, AttributeError):
        return ""


def _build_product_data(product):
    """
    Convert a Django Product instance into the JavaScript product format.

    The product slug is used as the ID because the checkout API
    identifies products using their slug.
    """

    original_price = float(product.price or 0)
    current_price = float(product.current_price or 0)

    # Main product image.
    images = []

    main_image_url = _get_image_url(product.image)

    if main_image_url:
        images.append({
            "src": main_image_url,
            "caption": product.name,
        })

    # Additional gallery images.
    for gallery_image in product.gallery.all():
        gallery_url = _get_image_url(gallery_image.image)

        if gallery_url:
            images.append({
                "src": gallery_url,
                "caption": gallery_image.caption or product.name,
            })

    # Safely handle JSONField values.
    tags = product.tags if isinstance(product.tags, list) else []
    highlights = (
        product.highlights
        if isinstance(product.highlights, list)
        else []
    )

    # Only display the original price when the current price is lower.
    old_price = (
        original_price
        if current_price < original_price
        else None
    )

    return {
        # Basic information
        "id": product.slug,
        "slug": product.slug,
        "name": product.name,
        "subtitle": product.subtitle or "",
        "short": product.short_description or "",

        # Product details
        "brand": product.brand or "",
        "category": (
            product.category.name
            if product.category
            else ""
        ),
        "subCategory": product.sub_category or "",
        "sub_category": product.sub_category or "",
        "model": product.model_number or "",
        "sku": product.sku or "",
        "color": product.color or "",
        "warranty": product.warranty or "",

        # Pricing
        "price": current_price,
        "oldPrice": old_price,

        # Stock
        "stock": product.stock_status,
        "stockQuantity": product.stock,

        # Product status
        "featured": product.is_featured,
        "isActive": product.is_active,

        # Product metadata
        "tags": tags,
        "highlights": highlights,
        "added": (
            product.created_at.date().isoformat()
            if product.created_at
            else ""
        ),

        # Product images
        "images": images,

        # Additional product information
        "description": product.description or "",
    }


def _build_use_case_data(use_case):
    """
    Convert a UseCase model instance into a JavaScript-friendly object.
    """

    return {
        "title": use_case.title,
        # app.js filters and labels portfolio cards by `cat`.
        "cat": use_case.category,
        "category": use_case.category,
        "mode": use_case.mode,
        "place": use_case.place or "",
        "text": use_case.text or "",
        "icon": use_case.icon or "box",
        "tone": use_case.tone or "",
    }


# ==============================================================================
# SEO: ROBOTS.TXT
# ==============================================================================

ROBOTS_DISALLOW = (
    "/admin/",
    "/admin-invoice/",
    "/accounts/",
    "/api/",
    "/cart/",
    "/checkout/",
    "/order/",
)


def robots_txt(request):
    site_url = (getattr(django_settings, "SITE_URL", "") or "").rstrip("/")
    sitemap_url = (site_url + "/sitemap.xml") if site_url else request.build_absolute_uri("/sitemap.xml")
    lines = ["User-agent: *"]
    lines += [f"Disallow: {path}" for path in ROBOTS_DISALLOW]
    lines += ["", f"Sitemap: {sitemap_url}", ""]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


# ==============================================================================
# HOME & BASIC PAGES
# ==============================================================================

def home(request):
    return render(request, "web/index.html", {
        "featured_products": Product.objects.filter(
            is_active=True,
            is_featured=True,
        )[:6],

        "featured_projects": PortfolioProject.objects.filter(
            is_active=True,
            is_featured=True,
        )[:3],

        "categories": Category.objects.filter(is_active=True),

        "highlights": SiteHighlight.objects.filter(
            is_active=True,
        ),

        "home_modes": SiteFeature.objects.filter(
            section="home_mode",
            is_active=True,
        ),

        "home_whys": SiteFeature.objects.filter(
            section="home_why",
            is_active=True,
        ),
    })


def product_list(request):
    """
    Product listing page.

    Loads active Django products and converts them into JSON-compatible
    dictionaries for products.js and app.js.
    """

    qs = (
        Product.objects
        .filter(is_active=True)
        .select_related("category")
        .prefetch_related("gallery")
    )

    category_slug = request.GET.get("category")

    if category_slug:
        qs = qs.filter(category__slug=category_slug)

    # Build JavaScript product data from Django database records.
    products_json = [
        _build_product_data(product)
        for product in qs
    ]

    # Build JavaScript use-case data.
    use_cases_json = [
        _build_use_case_data(use_case)
        for use_case in UseCase.objects.filter(is_active=True)
    ]

    return render(request, "web/products.html", {
        # Keep the original queryset available to the template.
        "products": qs,

        # Data consumed by _products_bridge.html.
        "products_json": products_json,
        "use_cases_json": use_cases_json,

        # Existing category functionality.
        "categories": Category.objects.filter(is_active=True),
        "active_category": category_slug,
    })


def product_detail(request, slug):
    product = get_object_or_404(
        Product,
        slug=slug,
        is_active=True,
    )

    related_qs = (
        Product.objects
        .filter(is_active=True)
        .exclude(pk=product.pk)
        .select_related("category")
        .prefetch_related("gallery")
    )
    if product.category:
        related_qs = related_qs.filter(category=product.category)

    related = []
    for item in related_qs[:4]:
        current = item.current_price
        related.append({
            "product": item,
            "image": product_page.card_image(item),
            "price_now": current,
            "price_old": item.price if current < item.price else None,
            "save": item.price - current if current < item.price else 0,
            "can_buy": item.stock_status == Product.STOCK_IN,
        })

    context = {"product": product, "related": related}
    context.update(product_page.build_context(product))
    return render(request, "web/product.html", context)


def portfolio(request):
    use_cases = UseCase.objects.filter(is_active=True)
    return render(request, "web/portfolio.html", {
        "projects": PortfolioProject.objects.filter(is_active=True),
        "use_cases": use_cases,
        # Read by _products_bridge.html -> app.js (#pfGrid cards).
        "use_cases_json": [_build_use_case_data(u) for u in use_cases],
    })


def about(request):
    return render(request, "web/about.html", {
        "about_missions": SiteFeature.objects.filter(
            section="about_mission",
            is_active=True,
        ),

        "about_whys": SiteFeature.objects.filter(
            section="about_why",
            is_active=True,
        ),

        "timeline_steps": TimelineStep.objects.filter(
            is_active=True,
        ),
    })


def contact(request):
    if request.method == "POST":
        form = ContactForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Thanks! Your message has been sent.",
            )
            return redirect("web:contact")

    else:
        form = ContactForm()

    return render(request, "web/contact.html", {
        "form": form,
    })


# ==============================================================================
# CART
# ==============================================================================

def cart_detail(request):
    return render(request, "web/cart.html", {
        "cart": Cart(request),
    })


@require_POST
def cart_add(request, product_id):
    cart = Cart(request)

    product = get_object_or_404(
        Product,
        pk=product_id,
        is_active=True,
    )

    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1

    qty = max(1, qty)

    cart.add(product, qty)

    messages.success(
        request,
        f'"{product.name}" added to cart.',
    )

    return redirect(
        request.POST.get("next") or "web:cart"
    )


@require_POST
def cart_update(request, product_id):
    cart = Cart(request)

    product = get_object_or_404(
        Product,
        pk=product_id,
    )

    try:
        qty = int(request.POST.get("quantity", 1))
    except (TypeError, ValueError):
        qty = 1

    if qty <= 0:
        cart.remove(product)
    else:
        cart.update(product, qty)

    return redirect("web:cart")


@require_POST
def cart_remove(request, product_id):
    cart = Cart(request)

    product = get_object_or_404(
        Product,
        pk=product_id,
    )

    cart.remove(product)

    messages.info(
        request,
        f'"{product.name}" removed.',
    )

    return redirect("web:cart")


# ==============================================================================
# CHECKOUT & API
# ==============================================================================

def checkout(request):
    form = CheckoutForm()

    return render(request, "web/checkout.html", {
        "cart": {},
        "form": form,
    })


def _json_error(message, status=400, errors=None):
    payload = {"success": False, "error": message}
    if errors:
        payload["errors"] = errors
    return JsonResponse(payload, status=status)


def _read_json(request):
    try:
        data = json.loads(request.body or b"{}")
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _clean_text(data, key, max_length):
    return str(data.get(key) or "").strip()[:max_length]


_TRX_RE = re.compile(r"^[A-Z0-9]{6,20}$")


def _validate_checkout(data):
    """Return (cleaned, errors). Every rule here mirrors the form in app.js."""
    errors = {}
    cleaned = {}

    cleaned["name"] = _clean_text(data, "name", 200)
    if len(cleaned["name"]) < 3:
        errors["name"] = "Please enter your full name."

    try:
        cleaned["phone"] = normalize_bd_phone(data.get("phone"))
    except ValueError as exc:
        errors["phone"] = str(exc)

    cleaned["email"] = _clean_text(data, "email", 254)
    if cleaned["email"]:
        try:
            validate_email(cleaned["email"])
        except DjangoValidationError:
            errors["email"] = "Enter a valid email address."

    try:
        cleaned["district"] = clean_bd_district(data.get("district"))
    except ValueError as exc:
        errors["district"] = str(exc)

    cleaned["address"] = _clean_text(data, "address", 255)
    if len(cleaned["address"]) < 10:
        errors["address"] = "Please enter your full address (house, road, area / thana)."

    cleaned["note"] = _clean_text(data, "note", 1000)

    cleaned["zone"] = str(data.get("zone") or Order.ZONE_INSIDE)
    if cleaned["zone"] not in dict(Order.ZONE_CHOICES):
        errors["zone"] = "Please choose a delivery area."

    cleaned["payment"] = str(data.get("payment") or "cod")
    if cleaned["payment"] not in dict(Order.PAYMENT_METHOD_CHOICES):
        errors["payment"] = "Please choose a payment method."

    cleaned["sender"] = ""
    cleaned["trx"] = ""
    if cleaned["payment"] in Order.MOBILE_PAYMENT_METHODS:
        try:
            cleaned["sender"] = normalize_bd_phone(data.get("sender"))
        except ValueError as exc:
            errors["sender"] = str(exc)
        cleaned["trx"] = re.sub(r"\s", "", str(data.get("trx") or "")).upper()
        if not _TRX_RE.match(cleaned["trx"]):
            errors["trx"] = "Enter the transaction ID (TrxID) from your payment SMS."

    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        errors["lines"] = "Your cart is empty."
        cleaned["lines"] = []
    else:
        cleaned["lines"] = lines

    return cleaned, errors


@require_POST
def api_checkout(request):
    data = _read_json(request)
    if data is None:
        return _json_error("Invalid request.")

    cleaned, errors = _validate_checkout(data)
    if errors:
        return _json_error(next(iter(errors.values())), errors=errors)

    cart = Cart(request)
    cart.clear()

    for item in cleaned["lines"]:
        if not isinstance(item, dict):
            return _json_error("Invalid cart item.")
        try:
            qty = int(item.get("qty", 0))
        except (TypeError, ValueError):
            return _json_error("Invalid product quantity.")
        product = Product.objects.filter(slug=str(item.get("id") or "")).first()
        if product is None:
            return _json_error(
                "A product in your cart is no longer available. Please refresh your cart."
            )
        cart.add(product, qty)

    try:
        order = place_order(
            cart=cart,
            customer_data={
                "full_name": cleaned["name"],
                "phone": cleaned["phone"],
                "email": cleaned["email"],
                "address_line1": cleaned["address"],
                "city": cleaned["district"],
                "country": "Bangladesh",
                "notes": cleaned["note"],
            },
            user=request.user if request.user.is_authenticated else None,
            delivery_zone=cleaned["zone"],
            payment_method=cleaned["payment"],
            payment_sender=cleaned["sender"],
            transaction_id=cleaned["trx"],
        )
    except DjangoValidationError as exc:  # includes StockError
        cart.clear()
        return _json_error(" ".join(exc.messages))
    except Exception:
        cart.clear()
        logger.exception("Checkout failed")
        return _json_error("Something went wrong. Please try again or call us.", status=500)

    cart.clear()

    try:
        if order.email:
            send_order_confirmation(order)
        send_admin_new_order(order)
    except Exception:
        logger.exception("Failed to send email for order %s", order.order_number)

    return JsonResponse({
        "success": True,
        "order_number": order.order_number,
    })


def order_success(request, order_number):
    order = get_object_or_404(
        Order,
        order_number=order_number,
    )

    return render(request, "web/order_success.html", {
        "order": order,
    })


def order_failed(request):
    order_number = request.GET.get("cancel")

    if order_number:
        try:
            order = Order.objects.get(
                order_number=order_number,
                status=Order.STATUS_PENDING,
            )

            cancel_order(order)

            messages.info(
                request,
                f"Order {order_number} cancelled.",
            )

        except Order.DoesNotExist:
            pass

    return render(request, "web/order_failed.html")


@require_POST
def api_contact(request):
    data = _read_json(request)
    if data is None:
        return _json_error("Invalid request.")

    errors = {}
    name = _clean_text(data, "name", 150)
    if len(name) < 3:
        errors["name"] = "Please enter your full name."

    try:
        phone = normalize_bd_phone(data.get("phone"))
    except ValueError as exc:
        errors["phone"] = str(exc)
        phone = ""

    email = _clean_text(data, "email", 254)
    if email:
        try:
            validate_email(email)
        except DjangoValidationError:
            errors["email"] = "Enter a valid email address."

    subject = _clean_text(data, "subject", 200)
    if not subject:
        errors["subject"] = "Please select an option."

    message = _clean_text(data, "message", 5000)
    if len(message) < 10:
        errors["message"] = "Please write at least 10 characters."

    if errors:
        return _json_error(next(iter(errors.values())), errors=errors)

    ContactMessage.objects.create(
        name=name,
        email=email,
        phone=phone,
        subject=subject,
        message=message,
    )
    return JsonResponse({"success": True})


# ==============================================================================
# ADMIN EXTRAS (INVOICE)
# ==============================================================================

@staff_member_required
def admin_invoice_view(request, object_id):
    order = get_object_or_404(
        Order,
        id=object_id,
    )

    return render(request, "admin/invoice.html", {
        "order": order,
    })
