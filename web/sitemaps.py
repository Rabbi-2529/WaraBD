# web/sitemaps.py
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Product


class _SiteUrlSitemap(Sitemap):
    """Build absolute URLs from settings.SITE_URL (e.g. https://warabd.com).

    The sites framework still holds the default "example.com", so without
    this every sitemap link would point at the wrong domain.
    """

    def _site(self):
        return urlsplit(getattr(settings, "SITE_URL", "") or "")

    def get_domain(self, site=None):
        return self._site().netloc or super().get_domain(site)

    def get_protocol(self, protocol=None):
        return self._site().scheme or super().get_protocol(protocol)


class ProductSitemap(_SiteUrlSitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True).order_by("pk")

    def lastmod(self, obj):
        return obj.updated_at


class StaticViewSitemap(_SiteUrlSitemap):
    changefreq = "monthly"
    priority = 1.0

    def items(self):
        return ["web:home", "web:product_list", "web:portfolio", "web:about", "web:contact"]

    def location(self, item):
        return reverse(item)


SITEMAPS = {
    "static": StaticViewSitemap,
    "products": ProductSitemap,
}
