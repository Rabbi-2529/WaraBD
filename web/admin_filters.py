# web/admin_filters.py
from django.contrib import admin
from django.utils import timezone
from datetime import timedelta

class PriceRangeFilter(admin.SimpleListFilter):
    title = "Price range"
    parameter_name = "price_range"
    def lookups(self, request, model_admin):
        return (("0-50", "Under $50"), ("50-100", "$50 – $100"), ("100-500", "$100 – $500"), ("500+", "$500+"))
    def queryset(self, request, queryset):
        if self.value() == "0-50": return queryset.filter(price__lt=50)
        if self.value() == "50-100": return queryset.filter(price__gte=50, price__lt=100)
        if self.value() == "100-500": return queryset.filter(price__gte=100, price__lt=500)
        if self.value() == "500+": return queryset.filter(price__gte=500)
        return queryset

class StockStatusFilter(admin.SimpleListFilter):
    title = "Stock status"
    parameter_name = "stock_status"
    def lookups(self, request, model_admin):
        return (("in", "In stock"), ("out", "Out of stock"), ("low", "Low stock (< 5)"))
    def queryset(self, request, queryset):
        if self.value() == "in": return queryset.filter(stock__gt=0)
        if self.value() == "out": return queryset.filter(stock=0)
        if self.value() == "low": return queryset.filter(stock__gt=0, stock__lt=5)
        return queryset

class HasDiscountFilter(admin.SimpleListFilter):
    title = "Discount"
    parameter_name = "has_discount"
    def lookups(self, request, model_admin):
        return (("yes", "Has discount"), ("no", "No discount"))
    def queryset(self, request, queryset):
        if self.value() == "yes": return queryset.filter(discount_price__isnull=False)
        if self.value() == "no": return queryset.filter(discount_price__isnull=True)
        return queryset

class OrderDateRangeFilter(admin.SimpleListFilter):
    title = "Order date"
    parameter_name = "date_range"
    def lookups(self, request, model_admin):
        return (("today", "Today"), ("week", "Last 7 days"), ("month", "Last 30 days"), ("quarter", "Last 90 days"))
    def queryset(self, request, queryset):
        now = timezone.now()
        if self.value() == "today": return queryset.filter(created_at__gte=now - timedelta(days=1))
        if self.value() == "week": return queryset.filter(created_at__gte=now - timedelta(days=7))
        if self.value() == "month": return queryset.filter(created_at__gte=now - timedelta(days=30))
        if self.value() == "quarter": return queryset.filter(created_at__gte=now - timedelta(days=90))
        return queryset

class ReadStatusFilter(admin.SimpleListFilter):
    title = "Read status"
    parameter_name = "read_status"
    def lookups(self, request, model_admin):
        return (("unread", "Unread"), ("read", "Read"))
    def queryset(self, request, queryset):
        if self.value() == "unread": return queryset.filter(is_read=False)
        if self.value() == "read": return queryset.filter(is_read=True)
        return queryset