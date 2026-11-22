# web/context_processors.py
from django.conf import settings
from django.urls import translate_url
from django.utils.translation import get_language, gettext

from .cart import Cart
from .i18n_js import js_catalog
from .models import Page, Product, SiteSettings
from .richtext import plain


def i18n_links(request):
    """Language switcher links and hreflang alternates for the current page.

    English lives at "/", Bangla at "/bn/"; translate_url maps the current
    path (query string included) to the same page in the other language.
    """
    current = (get_language() or settings.LANGUAGE_CODE).split("-")[0]
    path = request.get_full_path()
    site_url = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    links = []
    for code, label in settings.LANGUAGES:
        url = translate_url(path, code)
        links.append({
            "code": code,
            "label": label,
            "url": url,
            "absolute_url": (site_url + url) if site_url else request.build_absolute_uri(url),
            "active": code == current,
        })
    return {
        "lang": current,
        "language_links": links,
        "other_language": next((l for l in links if not l["active"]), None),
        "js_i18n": js_catalog(),
    }

def cart_summary(request):
    cart = Cart(request)
    return {"cart_count": len(cart), "cart_total": cart.get_total()}

def site_settings(request):
    # Featured product: used by the hero/footer product links.
    featured = (
        Product.objects.filter(is_active=True).order_by("-is_featured", "-created_at").first()
    )
    return {
        "site_settings": SiteSettings.load(),
        "featured_product": featured,
        # Policy / info pages ticked "Show in footer".
        "footer_pages": Page.objects.filter(is_active=True, show_in_footer=True),
    }

def products_json(request):
    products = Product.objects.filter(is_active=True).select_related("category").prefetch_related("gallery")
    data = []
    for p in products:
        # 🟢 NEW: Build gallery with main image + extras
        images = []
        if p.image:
            images.append({"src": p.image.url, "caption": p.name})
        for gi in p.gallery.all():
            images.append({"src": gi.image.url, "caption": gi.caption or p.name})
        
        data.append({
            "id": p.slug,
            "featured": p.is_featured,
            "brand": p.brand or "WaRa",
            "category": p.category.name if p.category else gettext("Products"),
            # 🟢 NEW: sub_category, discount_type
            "sub_category": p.sub_category,
            "discount_type": p.discount_type,
            "name": p.name,
            "subtitle": p.subtitle or "",
            "model": p.model_number or p.slug.upper(),
            "sku": p.sku or "",
            "color": p.color or "",
            "price": float(p.current_price),
            "oldPrice": float(p.price) if p.discount_price else None,
            "stock": p.stock_status,
            "warranty": p.warranty or "1 Year",
            "added": p.created_at.strftime("%Y-%m-%d"),
            "short": p.short_description or plain(p.description)[:200],
            "images": images,  # 🟢 Now includes gallery
            "highlights": p.highlights or [],
            "descriptionTitle": p.description_title or "",
            "description": [plain(p.description)] if p.description else [],
            "tags": p.tags or [],
            "specs": p.specs or [],
            "features": p.features or [],
            "applications": p.applications or {},
            "steps": p.steps or [],
            "faq": p.faq or [],
        })
    return {"products_json": data}