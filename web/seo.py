"""Page titles, descriptions, canonical links, share cards and structured data (Phase 6).

Every storefront page gets, from one place (layout.html → {% seo_data as seo %}):

* <title> and meta description — product / policy page fields, the "Page SEO"
  rows for fixed pages (home, products, portfolio, about, contact), or the
  built-in text below;
* canonical URL and hreflang (English at /, Bangla at /bn/);
* Open Graph + Twitter card tags, so Facebook / WhatsApp / Messenger show a
  title, text and picture when a link is shared;
* JSON-LD: Organization + WebSite on the home page, Product + BreadcrumbList
  on product pages (price in BDT, stock).
"""

import json

from django.conf import settings
from django.utils.html import strip_tags
from django.utils.text import Truncator
from django.utils.translation import gettext as _

from .models import Page, PageSeo, Product, SiteSettings

DEFAULTS = {
    # url name: (title, description) — same msgids as before, so the Bangla catalog keeps working.
    "product_list": (
        lambda: _("Products"),
        lambda: _("Shop WaRa smart security products in Bangladesh — keypad cabinet and drawer locks with cash on delivery and official warranty."),  # noqa: E501
    ),
    "portfolio": (
        lambda: _("Product Portfolio"),
        lambda: _("See the WaRa FT-SCL029 keypad lock in action — product gallery and use cases for homes, offices, hotels, hospitals, gyms and shops."),  # noqa: E501
    ),
    "about": (
        lambda: _("About Us"),
        lambda: _("WaRa BD brings WaRa smart cabinet and drawer locks to homes and businesses across Bangladesh."),
    ),
    "contact": (
        lambda: _("Contact Us"),
        lambda: _("Contact WaRa BD for orders, installation help, warranty support and bulk quotes for the FT-SCL029 cabinet lock."),  # noqa: E501
    ),
}
OG_LOCALES = {"en": "en_US", "bn": "bn_BD"}


def _base_url(request):
    site_url = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    return site_url or request.build_absolute_uri("/").rstrip("/")


def absolute(request, url):
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    return _base_url(request) + (url if url.startswith("/") else "/" + url)


def _file_url(field):
    try:
        return field.url if field else ""
    except ValueError:
        return ""


def _clean(text, limit):
    text = " ".join(strip_tags(str(text or "")).split())
    return Truncator(text).chars(limit) if text else ""


def build(context):
    request = context.get("request")
    site = context.get("site_settings") or SiteSettings.load()
    if request is None:
        return {"title": site.meta_title, "description": site.meta_description}
    lang = context.get("lang") or "en"
    name = site.name or "WaRa BD"
    match = getattr(request, "resolver_match", None)
    url_name = match.url_name if match else ""

    seo = {
        "title": site.meta_title or name,
        "description": site.meta_description or "",
        "image": _file_url(site.share_image) or _file_url(site.logo),
        "image_alt": name,
        "type": "website",
        "noindex": False,
        "site_name": name,
        "locale": OG_LOCALES.get(lang, "en_US"),
        "alt_locales": [v for k, v in OG_LOCALES.items() if k != lang],
        "jsonld": [],
    }

    product = context.get("product")
    page = context.get("page")
    if url_name == "product_detail" and isinstance(product, Product):
        title = product.name + (f" ({product.model_number})" if product.model_number else "")
        seo.update({
            "title": product.seo_title or f"{title} | {name}",
            "description": _clean(product.seo_description or product.short_description or product.description
                                  or product.name, 160),
            "image": _file_url(product.share_image) or _file_url(product.image) or _first_gallery(product) or seo["image"],
            "image_alt": product.name,
            "type": "product",
        })
        seo["jsonld"] = _product_jsonld(request, product, site, seo)
    elif url_name == "page" and isinstance(page, Page):
        seo.update({
            "title": page.seo_title or f"{page.title} | {name}",
            "description": _clean(page.meta_description or page.intro or page.title, 160),
            "image": _file_url(page.share_image) or seo["image"],
            "type": "article",
        })
    else:
        row = PageSeo.objects.filter(page=url_name).first() if url_name in dict(PageSeo.PAGES) else None
        if url_name in DEFAULTS:
            title, description = DEFAULTS[url_name]
            seo["title"] = f"{title()} | {name}"
            seo["description"] = description()
        if row:
            seo["title"] = row.title or seo["title"]
            seo["description"] = row.description or seo["description"]
            seo["image"] = _file_url(row.share_image) or seo["image"]
            seo["noindex"] = row.noindex
        if url_name == "home":
            seo["jsonld"] = _home_jsonld(request, site, seo)

    seo["description"] = _clean(seo["description"], 300)
    seo["image"] = absolute(request, seo["image"])
    links = context.get("language_links") or []
    current = next((l for l in links if l.get("active")), None)
    seo["canonical"] = absolute(request, current["url"].split("?")[0]) if current else absolute(request, request.path)
    seo["jsonld"] = [json.dumps(item, ensure_ascii=False) for item in seo["jsonld"]]
    return seo


def _first_gallery(product):
    first = product.gallery.first() if hasattr(product, "gallery") else None
    return _file_url(first.image) if first else ""


def _home_jsonld(request, site, seo):
    base = _base_url(request)
    org = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": site.name,
        "url": base + "/",
        "telephone": site.phone,
        "email": site.email,
        "address": {"@type": "PostalAddress", "addressLocality": site.address, "addressCountry": "BD"},
        "sameAs": [u for u in (site.facebook, site.instagram, site.youtube) if u and u.startswith("http")],
    }
    logo = _file_url(site.logo)
    if logo:
        org["logo"] = absolute(request, logo)
    website = {"@context": "https://schema.org", "@type": "WebSite", "name": site.name, "url": base + "/"}
    return [org, website]


def _product_jsonld(request, product, site, seo):
    from django.urls import reverse

    url = absolute(request, request.path)
    availability = {
        Product.STOCK_OUT: "https://schema.org/OutOfStock",
        Product.STOCK_UPCOMING: "https://schema.org/PreOrder",
    }.get(product.stock_status, "https://schema.org/InStock")
    if product.stock_status == Product.STOCK_IN and not product.stock:
        availability = "https://schema.org/OutOfStock"
    data = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": product.name,
        "description": seo["description"],
        "sku": product.sku or product.model_number or product.slug,
        "brand": {"@type": "Brand", "name": product.brand or site.name},
        "url": url,
        "offers": {
            "@type": "Offer",
            "url": url,
            "priceCurrency": "BDT",
            "price": f"{product.current_price:.2f}",
            "availability": availability,
            "itemCondition": "https://schema.org/NewCondition",
            "seller": {"@type": "Organization", "name": site.name},
        },
    }
    if product.model_number:
        data["mpn"] = product.model_number
    images = [absolute(request, u) for u in (_file_url(product.image), _first_gallery(product)) if u]
    if images:
        data["image"] = images
    lang_prefix = "/bn" if request.path.startswith("/bn/") else ""
    crumbs = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": _("Home"), "item": absolute(request, lang_prefix + "/")},
            {"@type": "ListItem", "position": 2, "name": _("Products"),
             "item": absolute(request, reverse("web:product_list"))},
            {"@type": "ListItem", "position": 3, "name": product.name, "item": url},
        ],
    }
    return [data, crumbs]
