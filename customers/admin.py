from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from web.admin_datatables import DataTablesAdminMixin

from .models import Customer, CustomerAddress, OtpCode, SmsLog


class CustomerAddressInline(admin.TabularInline):
    model = CustomerAddress
    extra = 0
    fields = ("label", "name", "phone", "district", "thana", "address", "is_default")


@admin.register(Customer)
class CustomerAdmin(DataTablesAdminMixin, admin.ModelAdmin):
    list_display = ("name", "phone", "email", "order_count", "is_active", "created_at", "last_login")
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "phone", "email")
    readonly_fields = ("created_at", "last_login", "orders_link")
    fields = ("name", "phone", "email", "is_active", "orders_link", "created_at", "last_login")
    inlines = [CustomerAddressInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_orders=Count("orders"))

    @admin.display(description="Orders", ordering="_orders")
    def order_count(self, obj):
        return obj._orders

    @admin.display(description="Orders")
    def orders_link(self, obj):
        if not obj.pk:
            return "—"
        url = reverse("admin:web_order_changelist") + f"?q={obj.phone}"
        return format_html('<a href="{}">{} order(s) for {}</a>', url, obj.orders.count(), obj.phone)


class _ReadOnlyAdmin(DataTablesAdminMixin, admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(SmsLog)
class SmsLogAdmin(_ReadOnlyAdmin):
    list_display = ("created_at", "phone", "purpose", "status", "short_message", "ip")
    list_filter = ("status", "purpose", "created_at")
    search_fields = ("phone", "ip")
    readonly_fields = ("created_at", "phone", "purpose", "status", "message", "response", "ip")
    # No date_hierarchy: needs MySQL time-zone tables, which XAMPP does not install.

    @admin.display(description="Message")
    def short_message(self, obj):
        return obj.message[:60]


@admin.register(OtpCode)
class OtpCodeAdmin(_ReadOnlyAdmin):
    """Codes are stored hashed: staff can see that a code was sent and used, never the code."""

    list_display = ("created_at", "phone", "purpose", "state", "attempts", "ip")
    list_filter = ("purpose", "created_at")
    search_fields = ("phone",)
    readonly_fields = ("created_at", "phone", "purpose", "attempts", "expires_at", "verified_at", "cancelled", "ip")
    exclude = ("salt", "code_hash", "payload")

    @admin.display(description="State")
    def state(self, obj):
        if obj.verified_at:
            return "Used"
        if obj.cancelled:
            return "Cancelled"
        if obj.is_expired:
            return "Expired"
        return "Waiting"
