# web/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Product, PortfolioProject


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.updated_at


class PortfolioSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return PortfolioProject.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.created_at


class StaticViewSitemap(Sitemap):
    changefreq = "monthly"
    priority = 1.0

    def items(self):
        return ["web:home", "web:product_list", "web:portfolio", "web:about", "web:contact"]

    def location(self, item):
        return reverse(item)