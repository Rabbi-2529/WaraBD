# web/context_processors.py
from .cart import Cart
from .models import Product, SiteSettings

def cart_summary(request):
    cart = Cart(request)
    return {"cart_count": len(cart), "cart_total": cart.get_total()}

def site_settings(request):
    return {"site_settings": SiteSettings.load()}

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
            "category": p.category.name if p.category else "Products",
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
            "short": p.short_description or (p.description[:200] if p.description else ""),
            "images": images,  # 🟢 Now includes gallery
            "highlights": p.highlights or [],
            "descriptionTitle": p.description_title or "",
            "description": [p.description] if p.description else [],
            "tags": p.tags or [],
            "specs": p.specs or [],
            "features": p.features or [],
            "applications": p.applications or {},
            "steps": p.steps or [],
            "faq": p.faq or [],
        })
    return {"products_json": data}