
# web/views.py

import json
import logging
import traceback

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

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
from .services import StockError, cancel_order, place_order


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
        "category": use_case.category,
        "mode": use_case.mode,
        "place": use_case.place or "",
        "text": use_case.text or "",
        "icon": use_case.icon or "box",
        "tone": use_case.tone or "",
    }


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

    if product.category:
        related = (
            Product.objects
            .filter(
                is_active=True,
                category=product.category,
            )
            .exclude(pk=product.pk)[:4]
        )
    else:
        related = Product.objects.none()

    return render(request, "web/product.html", {
        "product": product,
        "related": related,
    })


def portfolio(request):
    return render(request, "web/portfolio.html", {
        "projects": PortfolioProject.objects.filter(is_active=True),
        "use_cases": UseCase.objects.filter(is_active=True),
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


@csrf_exempt
def api_checkout(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            customer_data = {
                "full_name": data.get("name"),
                "phone": data.get("phone"),
                "email": data.get("email") or "no-email@warabd.com",
                "address_line1": data.get("address"),
                "address_line2": "",
                "city": data.get("district"),
                "postal_code": data.get("district"),
                "country": "Bangladesh",
                "notes": data.get("note", ""),
            }

            cart = Cart(request)
            cart.clear()

            for item in data.get("lines", []):
                try:
                    product = Product.objects.get(
                        slug=item["id"],
                    )

                    cart.add(
                        product,
                        item["qty"],
                    )

                except Product.DoesNotExist:
                    return JsonResponse({
                        "success": False,
                        "error": (
                            f"Product '{item['id']}' not found."
                        ),
                    }, status=400)

            try:
                order = place_order(
                    cart=cart,
                    customer_data=customer_data,
                    user=(
                        request.user
                        if request.user.is_authenticated
                        else None
                    ),
                )

            except StockError as e:
                return JsonResponse({
                    "success": False,
                    "error": str(e),
                }, status=400)

            # Auto-mark payment status based on method.
            payment_method = data.get("payment", "cod")

            order.payment_method = payment_method
            order.payment_status = (
                "unpaid"
                if payment_method == "cod"
                else "paid"
            )

            order.save()

            try:
                send_order_confirmation(order)
                send_admin_new_order(order)

            except Exception:
                logger.exception(
                    "Failed to send email for order %s",
                    order.order_number,
                )

            cart.clear()

            return JsonResponse({
                "success": True,
                "order_number": order.order_number,
            })

        except Exception as e:
            traceback.print_exc()

            return JsonResponse({
                "success": False,
                "error": str(e),
            }, status=500)

    return JsonResponse({
        "success": False,
        "error": "Invalid request method",
    }, status=405)


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


@csrf_exempt
def api_contact(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)

            ContactMessage.objects.create(
                name=data.get("name"),
                email=data.get("email"),
                phone=data.get("phone", ""),
                subject=data.get("subject"),
                message=data.get("message"),
            )

            return JsonResponse({
                "success": True,
            })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "error": str(e),
            }, status=400)

    return JsonResponse({
        "success": False,
        "error": "Invalid request",
    }, status=405)


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
