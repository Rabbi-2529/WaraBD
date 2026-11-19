
# web/admin.py

import csv
from datetime import datetime

from django.contrib import admin
from django.db.models import Count
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Category,
    Product,
    ProductImage,
    PortfolioProject,
    ContactMessage,
    Order,
    OrderItem,
    SiteSettings,
    SiteHighlight,
    SiteFeature,
    UseCase,
    TimelineStep,
)

from .admin_filters import (
    PriceRangeFilter,
    StockStatusFilter,
    HasDiscountFilter,
    OrderDateRangeFilter,
    ReadStatusFilter,
)

from .forms import ProductOrganizeForm
from .views import admin_invoice_view


# ============================================================
# CSV EXPORT
# ============================================================

class ExportCsvMixin:

    @admin.action(description="⬇ Export selected as CSV")
    def export_as_csv(self, request, queryset):
        meta = queryset.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="{meta.model_name}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(field_names)

        for obj in queryset:
            writer.writerow([
                getattr(obj, field, "")
                for field in field_names
            ])

        return response


# ============================================================
# SITE SETTINGS
# ============================================================

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):

    fieldsets = (
        (
            "Business Identity",
            {
                "fields": (
                    "name",
                    "phone",
                    "whatsapp",
                    "email",
                )
            },
        ),
        (
            "Location & Hours",
            {
                "fields": (
                    "address",
                    "map_query",
                    "hours",
                )
            },
        ),
        (
            "Homepage Announcement",
            {
                "fields": ("announcement",)
            },
        ),
        (
            "Delivery Settings",
            {
                "fields": (
                    "delivery_inside_fee",
                    "delivery_outside_fee",
                    "delivery_inside_eta",
                    "delivery_outside_eta",
                )
            },
        ),
        (
            "Payment (shown at checkout)",
            {
                "fields": (
                    "bkash_number",
                    "nagad_number",
                )
            },
        ),
        (
            "Social Links",
            {
                "fields": (
                    "facebook",
                    "instagram",
                    "youtube",
                )
            },
        ),
        (
            "SEO Metadata",
            {
                "fields": (
                    "meta_title",
                    "meta_description",
                )
            },
        ),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# ============================================================
# HOMEPAGE CONTENT BLOCKS
# ============================================================

@admin.register(SiteHighlight)
class SiteHighlightAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "subtitle",
        "icon",
        "order",
        "is_active",
    )

    list_editable = (
        "order",
        "is_active",
    )


@admin.register(SiteFeature)
class SiteFeatureAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "section",
        "icon",
        "badge",
        "order",
        "is_active",
    )

    list_filter = (
        "section",
        "is_active",
    )

    fields = (
        "section",
        "title",
        "icon",
        "text",
        "badge",
        "best_for",
        "order",
        "is_active",
    )

    list_editable = (
        "order",
        "is_active",
    )


@admin.register(UseCase)
class UseCaseAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "category",
        "mode",
        "place",
        "order",
        "is_active",
    )

    list_filter = (
        "category",
        "mode",
        "is_active",
    )

    list_editable = (
        "order",
        "is_active",
    )


@admin.register(TimelineStep)
class TimelineStepAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "icon",
        "order",
        "is_active",
    )

    list_editable = (
        "order",
        "is_active",
    )


# ============================================================
# PRODUCTS
# ============================================================

class ProductImageInline(admin.TabularInline):

    model = ProductImage
    extra = 3

    fields = (
        "image",
        "caption",
        "order",
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "category",
        "current_price",
        "stock",
        "is_active",
    )

    inlines = [
        ProductImageInline,
    ]

    prepopulated_fields = {
        "slug": ("name",),
    }

    form = ProductOrganizeForm

    add_form_template = (
        "admin/web/product/add_form.html"
    )

    change_form_template = (
        "admin/web/product/add_form.html"
    )

    fields = (
        "name",
        "slug",
        "sku",
        "stock",
        "stock_status",
        "description",
        "image",
        "price",
        "discount_type",
        "discount_price",
        "brand",
        "category",
        "sub_category",
        "is_active",
        "tags",
    )

    def save_model(self, request, obj, form, change):
        super().save_model(
            request,
            obj,
            form,
            change,
        )


# ============================================================
# CATEGORIES
# ============================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "slug",
        "is_active",
    )

    list_editable = (
        "is_active",
    )

    prepopulated_fields = {
        "slug": ("name",),
    }

    def has_add_permission(self, request):
        return True


# ============================================================
# PORTFOLIO PROJECTS
# ============================================================

@admin.register(PortfolioProject)
class PortfolioProjectAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "client",
        "is_active",
    )

    prepopulated_fields = {
        "slug": ("title",),
    }


# ============================================================
# CONTACT MESSAGES
# ============================================================

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "email",
        "subject",
        "is_read",
        "created_at",
    )

    list_filter = (
        "is_read",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "subject",
        "message",
    )

    readonly_fields = (
        "name",
        "email",
        "phone",
        "subject",
        "message",
        "created_at",
    )

    list_editable = (
        "is_read",
    )

    date_hierarchy = "created_at"

    fieldsets = (
        (
            "Status",
            {
                "fields": ("is_read",)
            },
        ),
    )

    def has_add_permission(self, request):
        return False


# ============================================================
# ORDERS
# ============================================================

class OrderItemInline(admin.TabularInline):

    model = OrderItem
    extra = 0

    fields = (
        "product",
        "quantity",
        "price",
        "line_total",
    )

    readonly_fields = (
        "product",
        "quantity",
        "price",
        "line_total",
    )

    can_delete = False

    @admin.display(description="Line total")
    def line_total(self, obj):
        if obj.pk:
            return format_html(
                "৳ {}",
                obj.line_total,
            )

        return "—"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):

    list_display = (
        "order_number",
        "full_name",
        "total",
        "status",
        "payment_status",
        "created_at",
    )

    list_filter = (
        "status",
        "payment_status",
        "payment_method",
        "delivery_zone",
        "created_at",
    )

    search_fields = (
        "order_number",
        "full_name",
        "email",
        "phone",
        "transaction_id",
    )

    fields = (
        "order_number",
        "status",
        "payment_status",
        "payment_method",
        "payment_sender",
        "transaction_id",
        "notes",
        "full_name",
        "email",
        "phone",
        "address_line1",
        "address_line2",
        "city",
        "postal_code",
        "country",
        "delivery_zone",
    )

    readonly_fields = (
        "subtotal",
        "shipping",
        "total",
    )

    add_form_template = (
        "admin/web/order/add_form.html"
    )

    change_form_template = (
        "admin/web/order/change_form.html"
    )

    actions = [
        "mark_paid",
        "mark_shipped",
        "mark_delivered",
        "mark_cancelled",
    ]

    @admin.action(
        description="✅ Mark selected orders as PAID"
    )
    def mark_paid(self, request, queryset):
        queryset.update(
            payment_status="paid"
        )

    @admin.action(
        description="📦 Mark selected orders as SHIPPED"
    )
    def mark_shipped(self, request, queryset):
        queryset.update(
            status="shipped"
        )

    @admin.action(
        description="🚚 Mark selected orders as DELIVERED"
    )
    def mark_delivered(self, request, queryset):
        queryset.update(
            status="delivered"
        )

    @admin.action(
        description="❌ Mark selected orders as CANCELLED"
    )
    def mark_cancelled(self, request, queryset):
        queryset.update(
            status="cancelled"
        )

    def save_model(self, request, obj, form, change):

        date_str = request.POST.get(
            "created_at_date"
        )

        if date_str:
            try:
                parsed_date = datetime.strptime(
                    date_str,
                    "%Y-%m-%d",
                )

                obj.created_at = timezone.make_aware(
                    parsed_date
                )

            except ValueError:
                pass

        super().save_model(
            request,
            obj,
            form,
            change,
        )

    def get_urls(self):

        urls = super().get_urls()

        custom_urls = [
            path(
                "<path:object_id>/invoice/",
                self.admin_site.admin_view(
                    admin_invoice_view
                ),
                name="web_order_invoice",
            ),
        ]

        return custom_urls + urls

    def changelist_view(
        self,
        request,
        extra_context=None,
    ):

        extra_context = extra_context or {}

        extra_context["kpi_completed"] = (
            Order.objects.filter(
                status="delivered"
            ).count()
        )

        extra_context["kpi_pending"] = (
            Order.objects.filter(
                status="pending"
            ).count()
        )

        extra_context["kpi_canceled"] = (
            Order.objects.filter(
                status="cancelled"
            ).count()
        )

        extra_context["kpi_new"] = (
            Order.objects.filter(
                status="paid"
            ).count()
        )

        extra_context["kpi_returned"] = 0

        return super().changelist_view(
            request,
            extra_context=extra_context,
        )
