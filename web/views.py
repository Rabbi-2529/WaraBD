
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
from django.utils.translation import gettext as _
from django.shortcuts import get_object_or_404, redirect, render
from django.http import Http404
from django.urls import Resolver404, resolve, reverse
from django.views.decorators.http import require_POST

from customers.models import Customer, OtpCode
from customers.auth import phone_verified_today
from customers.otp import OtpError, otp_needed_for_order, request_otp

from . import product_page
from .bd import clean_bd_district, normalize_bd_phone
from .checkout import can_view_order, place_checkout_order
from .delivery import DeliveryError, delivery_quote, locations_payload
from .richtext import plain as plain_text
from .cart import Cart
from .emails import send_admin_new_order, send_order_confirmation
from .forms import CheckoutForm, ContactForm
from .models import (
    Category,
    Order,
    Page,
    PortfolioProject,
    Product,
    SiteHighlight,
    SiteSettings,
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
        "description": plain_text(product.description),
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
        "text": plain_text(use_case.text),
        "icon": use_case.icon or "box",
        "tone": use_case.tone or "",
    }


# ==============================================================================
# SEO: ROBOTS.TXT
# ==============================================================================

ROBOTS_DISALLOW = (
    "/admin/",
    "/accounts/",
)
# Storefront pages that must stay out of search results, in every language
# ("/cart/" and "/bn/cart/" ...).
ROBOTS_DISALLOW_STORE = (
    "/admin-invoice/",
    "/api/",
    "/cart/",
    "/checkout/",
    "/order/",
)


def robots_txt(request):
    site_url = (getattr(django_settings, "SITE_URL", "") or "").rstrip("/")
    sitemap_url = (site_url + "/sitemap.xml") if site_url else request.build_absolute_uri("/sitemap.xml")
    prefixes = [""] + [f"/{code}" for code, _name in django_settings.LANGUAGES if code != django_settings.LANGUAGE_CODE]
    lines = ["User-agent: *"]
    lines += [f"Disallow: {path}" for path in ROBOTS_DISALLOW]
    lines += [f"Disallow: {prefix}{path}" for prefix in prefixes for path in ROBOTS_DISALLOW_STORE]
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
    category_slug = request.GET.get("category")
    if category_slug and Category.objects.filter(slug=category_slug, is_active=True).exists():
        # Old ?category= links → the category's own page (its own title, text and FAQ).
        return redirect("web:category", slug=category_slug, permanent=True)
    return _product_list_page(request)


def category_detail(request, slug):
    """/category/<slug>/ — the shop page limited to one category, with its own SEO and FAQ."""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    return _product_list_page(request, category)


def _product_list_page(request, category=None):
    qs = (
        Product.objects
        .filter(is_active=True)
        .select_related("category")
        .prefetch_related("gallery")
    )

    category_slug = category.slug if category else None

    if category:
        qs = qs.filter(category=category)

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
        "category": category,
    })


def product_old_url(request, slug):
    """/products/<slug>/ (old address) → /<slug> permanently, keeping #fragment-free query."""
    target = reverse("web:product_detail", kwargs={"slug": slug})
    if request.META.get("QUERY_STRING"):
        target += "?" + request.META["QUERY_STRING"]
    return redirect(target, permanent=True)


def product_detail(request, slug):
    product = Product.objects.filter(slug=slug, is_active=True).first()
    if product is None:
        # "/about" (no slash) lands here because product URLs have no trailing
        # slash: send it to "/about/" if that page exists, otherwise 404.
        try:
            resolve(request.path_info + "/")
        except Resolver404:
            raise Http404("Product not found")
        return redirect(request.path + "/", permanent=True)

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
                _("Thanks! Your message has been sent."),
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
        _('"%(name)s" added to cart.') % {"name": product.name},
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
        _('"%(name)s" removed.') % {"name": product.name},
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
        # Logged-in customers get their default address filled in.
        "checkout_address": request.customer.default_address if request.customer else None,
        # Districts → thanas → delivery charges for the dropdowns.
        "delivery_locations": locations_payload(),
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
        errors["name"] = _("Please enter your full name.")

    try:
        cleaned["phone"] = normalize_bd_phone(data.get("phone"))
    except ValueError as exc:
        errors["phone"] = str(exc)

    cleaned["email"] = _clean_text(data, "email", 254)
    if cleaned["email"]:
        try:
            validate_email(cleaned["email"])
        except DjangoValidationError:
            errors["email"] = _("Enter a valid email address.")

    try:
        cleaned["district"] = clean_bd_district(data.get("district"))
    except ValueError as exc:
        errors["district"] = str(exc)

    # Thana / upazila: picked from the district's list (or typed when missing).
    cleaned["thana"] = _clean_text(data, "thana", 80)
    if not cleaned["thana"]:
        errors["thana"] = _("Please select your thana / upazila.")

    # Delivery charge follows the district (or thana) — the customer does not choose it.
    if "district" not in errors:
        try:
            quote = delivery_quote(cleaned["district"], cleaned["thana"])
        except DeliveryError as exc:
            errors["district"] = str(exc)
        else:
            cleaned["zone"] = quote["zone"]
            if quote["thana"] is not None:
                cleaned["thana"] = quote["thana"].name_en  # canonical English spelling

    cleaned["address"] = _clean_text(data, "address", 255)
    if len(cleaned["address"]) < 10:
        errors["address"] = _("Please enter your full address (house, road, area / thana).")

    cleaned["note"] = _clean_text(data, "note", 1000)

    cleaned["payment"] = str(data.get("payment") or SiteSettings.load().default_payment_method)
    if cleaned["payment"] not in SiteSettings.load().payment_methods():
        errors["payment"] = _("Please choose a payment method.")

    cleaned["sender"] = ""
    cleaned["trx"] = ""
    if cleaned["payment"] in Order.MOBILE_PAYMENT_METHODS:
        try:
            cleaned["sender"] = normalize_bd_phone(data.get("sender"))
        except ValueError as exc:
            errors["sender"] = str(exc)
        cleaned["trx"] = re.sub(r"\s", "", str(data.get("trx") or "")).upper()
        if not _TRX_RE.match(cleaned["trx"]):
            errors["trx"] = _("Enter the transaction ID (TrxID) from your payment SMS.")

    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        errors["lines"] = _("Your cart is empty.")
        cleaned["lines"] = []
    else:
        cleaned["lines"] = lines

    return cleaned, errors


@require_POST
def api_checkout_lookup(request):
    """Checkout, mobile number typed first → the details of that customer's last order.

    Only answered for the logged-in customer's own number, or a number this browser
    confirmed by SMS today; anyone else gets {"found": false}, so nobody can look up
    a stranger's address by typing their number.
    """
    data = _read_json(request) or {}
    try:
        phone = normalize_bd_phone(data.get("phone"))
    except ValueError:
        return JsonResponse({"found": False})
    if not phone_verified_today(request, phone):
        return JsonResponse({"found": False})
    details = {}
    order = Order.objects.filter(phone=phone).order_by("-created_at").first()
    if order:
        details = {"name": order.full_name, "email": order.email, "district": order.city,
                   "thana": order.thana, "address": order.address_line1}
    customer = request.customer if request.customer and request.customer.phone == phone else None
    if customer:
        address = customer.default_address
        details.setdefault("name", customer.name)
        details["email"] = details.get("email") or customer.email
        if address and not order:
            details.update({"district": address.district, "thana": address.thana, "address": address.address})
    return JsonResponse({"found": bool(details), **details})


@require_POST
def api_checkout(request):
    data = _read_json(request)
    if data is None:
        return _json_error(_("Invalid request."))

    cleaned, errors = _validate_checkout(data)
    if errors:
        return _json_error(next(iter(errors.values())), errors=errors)

    # Guests confirm their mobile number with an SMS code first (once per day
    # per browser; logged-in customers never need it). The OTP page places
    # the order after the right code is entered.
    if otp_needed_for_order(request, cleaned["phone"]):
        try:
            request_otp(request, phone=cleaned["phone"], purpose=OtpCode.PURPOSE_CHECKOUT,
                        payload={"checkout": cleaned})
        except OtpError as exc:
            return _json_error(str(exc), status=429, errors={"phone": str(exc)})
        return JsonResponse({"success": False, "otp_required": True, "redirect": reverse("customers:otp")})

    order, error, status = place_checkout_order(request, cleaned, customer=order_customer(request, cleaned["phone"]))
    if error:
        return _json_error(error, status=status)
    return JsonResponse({
        "success": True,
        "order_number": order.order_number,
    })


def order_success(request, order_number):
    order = get_object_or_404(
        Order,
        order_number=order_number,
    )
    if not can_view_order(request, order):
        messages.info(request, _("For your privacy, enter your order number and mobile number to see this order."))
        return redirect("web:track_order")

    return render(request, "web/order_success.html", {
        "order": order,
    })


def render_invoice(request, order, back_url=""):
    """The printable invoice (web/invoice.html), always in English."""
    from django.utils import translation

    site = SiteSettings.load()
    with translation.override("en"):
        context = {
            "order": order,
            "site": site,
            "items": order.items.select_related("product"),
            "address": ", ".join(p for p in (order.address_line1, order.address_line2, order.thana, order.city) if p),
            "payment_label": str(order.get_payment_method_display()),
            "website": (getattr(django_settings, "SITE_URL", "") or request.build_absolute_uri("/")).rstrip("/"),
            "back_url": back_url,
        }
        return render(request, "web/invoice.html", context)


def order_invoice(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    if not can_view_order(request, order):
        messages.info(request, _("For your privacy, enter your order number and mobile number to see this order."))
        return redirect("web:track_order")
    return render_invoice(request, order, back_url=request.META.get("HTTP_REFERER", ""))


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
                _("Order %(number)s cancelled.") % {"number": order_number},
            )

        except Order.DoesNotExist:
            pass

    return render(request, "web/order_failed.html")


@require_POST
def api_contact(request):
    data = _read_json(request)
    if data is None:
        return _json_error(_("Invalid request."))

    errors = {}
    name = _clean_text(data, "name", 150)
    if len(name) < 3:
        errors["name"] = _("Please enter your full name.")

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
            errors["email"] = _("Enter a valid email address.")

    subject = _clean_text(data, "subject", 200)
    if not subject:
        errors["subject"] = _("Please select an option.")

    message = _clean_text(data, "message", 5000)
    if len(message) < 10:
        errors["message"] = _("Please write at least 10 characters.")

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
    return render_invoice(request, order, back_url=reverse("admin:web_order_change", args=[order.pk]))


# ==============================================================================
# POLICY / INFO PAGES & ORDER TRACKING (Phase 3 / 4)
# ==============================================================================

def page_detail(request, slug):
    page = get_object_or_404(Page, slug=slug, is_active=True)
    return render(request, "web/page.html", {"page": page})


def order_progress(order):
    """Steps for the order tracker: [(label, state)] with state done/current/todo."""
    if order.status == Order.STATUS_CANCELLED:
        return [(_("Order placed"), "done"), (_("Cancelled"), "failed")]
    reached = {
        Order.STATUS_PENDING: 1,
        Order.STATUS_PAID: 2,
        Order.STATUS_SHIPPED: 3,
        Order.STATUS_DELIVERED: 4,
    }.get(order.status, 1)
    labels = [_("Order placed"), _("Confirmed"), _("Shipped"), _("Delivered")]
    steps = []
    for index, label in enumerate(labels, 1):
        state = "done" if index < reached or reached == 4 else ("current" if index == reached else "todo")
        steps.append((label, state))
    return steps


def track_order(request):
    """Guests look up an order with its order number + the phone used to order.

    POST (not GET) so phone numbers never appear in URLs or server logs.
    """
    order, error = None, ""
    number = phone_input = ""
    if request.method == "POST":
        number = _clean_text(request.POST, "order_number", 32).upper()
        phone_input = _clean_text(request.POST, "phone", 20)
        try:
            phone = normalize_bd_phone(phone_input)
        except ValueError as exc:
            error = str(exc)
        else:
            order = Order.objects.filter(order_number__iexact=number, phone=phone).first()
            if order is None:
                error = _("No order found with this order number and mobile number.")
    return render(request, "web/track_order.html", {
        "order": order,
        "progress": order_progress(order) if order else [],
        "error": error,
        "number": number,
        "phone_input": phone_input,
    })


def order_customer(request, phone):
    """Customer account to attach an order to: the logged-in customer, or the
    account owning `phone` when that number was verified in this browser today."""
    from customers.auth import phone_verified_today

    if request.customer:
        return request.customer
    if phone_verified_today(request, phone):
        return Customer.objects.filter(phone=phone, is_active=True).first()
    return None
