
# web/admin.py

import csv
from datetime import datetime
from decimal import Decimal

from django import forms
from django.contrib import admin
from django.template.response import TemplateResponse
from django.db.models import Count
from django.http import HttpResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Category,
    ContentBlock,
    ContentItem,
    District,
    PageSeo,
    Page,
    Product,
    SeoKeyword,
    ProductImage,
    PortfolioProject,
    ContactMessage,
    Order,
    OrderItem,
    SiteSettings,
    Thana,
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

from modeltranslation.admin import TranslationAdmin, TranslationTabularInline

from django.db import models as dj_models

from .admin_datatables import DataTablesAdminMixin
from .forms import (PRODUCT_LIST_FIELDS, PRODUCT_TEXT_FIELDS, CategoryAdminForm, PageAdminForm, PageSeoAdminForm,
                    ProductOrganizeForm, product_form_fields)
from .views import admin_invoice_view
from .widgets import RichTextarea


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
class SiteSettingsAdmin(TranslationAdmin):

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
                "description": 'Charges customers pay now come from <a href="../../../district/">Delivery → District charges</a>. '
                               "These two numbers are only the product page's “Inside / Outside Dhaka” lines.",
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
                "description": "Switch payment methods on or off. The checkout always shows at least one.",
                "fields": (
                    ("pay_cod_enabled", "pay_bkash_enabled", "pay_nagad_enabled"),
                    "pay_default",
                    "bkash_number",
                    "nagad_number",
                    "invoice_terms",
                )
            },
        ),
        (
            "Translation (Google)",
            {
                "description": "With a key here, every বাংলা box in the admin gets a “Translate from English” "
                               "button, and an empty বাংলা box is filled when you finish the English one.",
                "fields": ("google_translate_api_key",),
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
            "SEO & sharing",
            {
                "description": "Home page title and description for Google, and the picture shown when a link is shared. "
                               'Each page has its own SEO in <a href="../../../pageseo/">Website → Page SEO</a>; each product in its own form.',
                "fields": (
                    "meta_title",
                    "meta_description",
                    "share_image",
                    "google_site_verification",
                )
            },
        ),
        (
            "Branding",
            {"fields": ("logo", "favicon")},
        ),
        (
            "Phone login / OTP",
            {
                "description": "Customers log in and confirm orders with a 6-digit SMS code. "
                               "The daily limits stop the same number getting many SMS in one day.",
                "fields": (
                    "otp_for_orders",
                    "sms_daily_limit_per_number",
                    "sms_daily_limit_per_ip",
                    "otp_valid_minutes",
                    "otp_resend_seconds",
                    "otp_max_attempts",
                    "otp_sms_text",
                ),
            },
        ),
        (
            "SMS gateway",
            {
                "description": 'IGL Web SMS (api_key, contacts, senderid, msg). Save, then '
                               '<a href="sms-test/">send a test SMS</a> to check the key and sender ID.',
                "fields": (
                    "sms_enabled",
                    "sms_api_url",
                    "sms_api_key",
                    "sms_sender_id",
                    "sms_number_format",
                ),
            },
        ),
        (
            "Courier",
            {
                "description": 'Book parcels straight from an order with “Send to courier”. Save, then '
                               '<a href="courier-test/">test the courier keys</a>. '
                               "Pathao also needs its city / zone numbers: on Delivery → District charges choose "
                               "“Match Pathao cities & zones”.",
                "fields": (
                    "courier_provider",
                    "steadfast_api_url",
                    "steadfast_api_key",
                    "steadfast_secret_key",
                    "pathao_api_url",
                    "pathao_client_id",
                    "pathao_client_secret",
                    "pathao_username",
                    "pathao_password",
                    "pathao_store_id",
                    "pathao_item_weight",
                    "courier_sms_on_dispatch",
                    "courier_dispatch_sms_text",
                ),
            },
        ),
    )

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in ("sms_api_key", "steadfast_api_key", "steadfast_secret_key", "pathao_client_secret",
                             "pathao_password", "google_translate_api_key"):
            kwargs["widget"] = forms.PasswordInput(render_value=True, attrs={"autocomplete": "off", "class": "vTextField"})
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def get_urls(self):
        custom = [
            path("<path:object_id>/sms-test/", self.admin_site.admin_view(self.sms_test_view),
                 name="web_sitesettings_sms_test"),
            path("<path:object_id>/courier-test/", self.admin_site.admin_view(self.courier_test_view),
                 name="web_sitesettings_courier_test"),
        ]
        return custom + super().get_urls()

    def sms_test_view(self, request, object_id):
        """Send one test SMS with the saved gateway settings and show the gateway's answer."""
        from customers.sms import gateway_ready, send_sms
        from .bd import normalize_bd_phone

        result = None
        error = ""
        phone_value = request.POST.get("phone", "")
        if request.method == "POST":
            try:
                phone = normalize_bd_phone(phone_value)
            except ValueError as exc:
                error = str(exc)
            else:
                result = send_sms(phone, "WaRa BD test message. Your SMS gateway is working.", purpose="test")
        context = {
            **self.admin_site.each_context(request),
            "title": "Send a test SMS",
            "ready": gateway_ready(),
            "result": result,
            "error": error,
            "phone_value": phone_value,
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/web/sitesettings/sms_test.html", context)

    def courier_test_view(self, request, object_id):
        """Check the saved courier keys (Steadfast: balance, Pathao: login) and report back."""
        from django.contrib import messages
        from django.shortcuts import redirect

        from . import courier

        site = SiteSettings.load()
        ok, reason = courier.ready(site)
        back = redirect("admin:web_sitesettings_change", object_id)
        if not ok:
            messages.error(request, reason)
            return back
        try:
            if site.courier_provider == courier.STEADFAST:
                balance = courier.steadfast_balance(site)
                messages.success(request, f"Steadfast keys work. Current balance: ৳{balance}.")
            else:
                courier.pathao_token(site, fresh=True)
                messages.success(request, "Pathao login works. Next: match Pathao cities & zones on the District charges list.")
        except courier.CourierError as exc:
            messages.error(request, f"Courier test failed: {exc}")
        return back

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


# CKEditor for every long text box (descriptions, page bodies, card text).
RICH_TEXT = {dj_models.TextField: {"widget": RichTextarea}}
RICH_TEXT_COMPACT = {dj_models.TextField: {"widget": RichTextarea(compact=True)}}


# ============================================================
# HOMEPAGE CONTENT BLOCKS
# ============================================================

@admin.register(SiteHighlight)
class SiteHighlightAdmin(TranslationAdmin):

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
class SiteFeatureAdmin(TranslationAdmin):
    formfield_overrides = RICH_TEXT_COMPACT

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
class UseCaseAdmin(TranslationAdmin):
    formfield_overrides = RICH_TEXT_COMPACT

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
class TimelineStepAdmin(TranslationAdmin):
    formfield_overrides = RICH_TEXT_COMPACT

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

class ProductImageInline(TranslationTabularInline):

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
        "slug": ("name_en",),
    }

    form = ProductOrganizeForm

    add_form_template = (
        "admin/web/product/add_form.html"
    )

    change_form_template = (
        "admin/web/product/add_form.html"
    )

    # Every field here must be rendered by add_form.html, otherwise saving
    # the form would blank it. The list lives next to the form definition.
    fields = product_form_fields()

    def render_change_form(self, request, context, *args, **kwargs):
        # English/Bangla pairs for the "Product page content" card.
        form = context["adminform"].form
        context["text_rows"] = [
            (label, form[f"{field}_en"], form[f"{field}_bn"])
            for field, label, _widget in PRODUCT_TEXT_FIELDS
        ]
        context["list_rows"] = [
            (label, form[f"{field}_en"], form[f"{field}_bn"])
            for field, label, _cls in PRODUCT_LIST_FIELDS
            if field != "faq"  # the FAQ has its own card with English / Bangla tabs
        ]
        return super().render_change_form(request, context, *args, **kwargs)

    def save_model(self, request, obj, form, change):
        super().save_model(
            request,
            obj,
            form,
            change,
        )
        if obj.is_featured:
            # "Show on home page" is for one product: take the tick off the others.
            others = Product.objects.filter(is_featured=True).exclude(pk=obj.pk)
            names = list(others.values_list("name", flat=True)[:3])
            if names:
                others.update(is_featured=False)
                from django.contrib import messages

                messages.info(request, f"Now on the home page: {obj.name}. Taken off: {', '.join(names)}.")


# ============================================================
# CATEGORIES
# ============================================================

SEO_HELP = ("What Google shows and the card people see when the link is shared on Facebook / WhatsApp. "
            "Empty boxes use the built-in text.")
FAQ_HELP = "Questions and answers shown on this page (and given to Google as FAQ data)."


@admin.register(Category)
class CategoryAdmin(TranslationAdmin):
    formfield_overrides = RICH_TEXT
    form = CategoryAdminForm
    fieldsets = (
        ("Category", {"fields": ("name", "slug", "description", "is_active")}),
        ("FAQ", {"description": FAQ_HELP, "fields": ("faq",)}),
        ("SEO & sharing", {"description": SEO_HELP,
                           "fields": ("seo_title", "seo_description", "seo_keywords", "share_image")}),
    )

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
class PortfolioProjectAdmin(TranslationAdmin):
    formfield_overrides = RICH_TEXT

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

    # No date_hierarchy: on MySQL/MariaDB without time-zone tables (XAMPP's
    # default) it crashes the list page. The created_at filter covers it.

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
        "thana",
        "postal_code",
        "country",
        "delivery_zone",
        "courier",
        "courier_tracking_code",
        "courier_tracking_url",
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
        "send_to_courier",
        "refresh_courier_status",
        "mark_paid",
        "mark_shipped",
        "mark_delivered",
        "mark_cancelled",
    ]

    @admin.action(description="🚚 Send selected orders to the courier")
    def send_to_courier(self, request, queryset):
        from django.contrib import messages

        from . import courier

        sent, failed = 0, []
        for order in queryset.order_by("created_at"):
            try:
                courier.book(order)
                sent += 1
            except courier.CourierError as exc:
                failed.append(f"{order.order_number}: {exc}")
        if sent:
            messages.success(request, f"{sent} order(s) sent to the courier.")
        for line in failed[:10]:
            messages.error(request, line)

    @admin.action(description="🔄 Refresh courier status")
    def refresh_courier_status(self, request, queryset):
        from django.contrib import messages

        from . import courier

        done, failed = 0, []
        for order in queryset.exclude(courier_consignment_id=""):
            try:
                courier.refresh(order)
                done += 1
            except courier.CourierError as exc:
                failed.append(f"{order.order_number}: {exc}")
        messages.info(request, f"Courier status checked for {done} order(s).")
        for line in failed[:10]:
            messages.error(request, line)

    def courier_view(self, request, object_id, action):
        """POST from the order page: action = send | refresh."""
        from django.contrib import messages
        from django.shortcuts import get_object_or_404, redirect

        from . import courier

        order = get_object_or_404(Order, pk=object_id)
        back = redirect("admin:web_order_change", order.pk)
        if request.method != "POST" or not self.has_change_permission(request, order):
            return back
        try:
            if action == "send":
                courier.book(order)
                messages.success(request, f"Sent to {courier.courier_label(order)}. Tracking code: "
                                          f"{order.courier_tracking_code or order.courier_consignment_id}.")
            else:
                status = courier.refresh(order)
                messages.info(request, f"Courier status: {status}.")
        except courier.CourierError as exc:
            messages.error(request, str(exc))
        return back

    # Fields the custom order page (admin/web/order/change_form.html) actually posts.
    CHANGE_PAGE_FIELDS = (
        "status", "payment_status", "notes", "full_name", "email", "phone",
        "address_line1", "thana", "city", "postal_code",
        "courier", "courier_tracking_code", "courier_tracking_url",
    )

    def get_fields(self, request, obj=None):
        from .admin_orders import ORDER_CREATE_FIELDS

        if obj is not None:
            return self.CHANGE_PAGE_FIELDS
        return ORDER_CREATE_FIELDS

    def get_form(self, request, obj=None, change=False, **kwargs):
        from .admin_orders import AdminOrderChangeForm, AdminOrderCreateForm

        kwargs["form"] = AdminOrderCreateForm if obj is None else AdminOrderChangeForm
        return super().get_form(request, obj, change=change, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields if obj is not None else ()

    def render_change_form(self, request, context, *args, **kwargs):
        from . import courier

        obj = context.get("original")
        if obj is None:
            from .admin_orders import posted_items
            from .delivery import locations_payload

            context.update({
                "next_order_number": Order.next_order_number(),
                "delivery_locations": locations_payload(),
                "order_lines": posted_items(request) if request.method == "POST" else [],
                "order_search_url": reverse("admin:web_order_product_search"),
                "order_lookup_url": reverse("admin:web_order_customer_lookup"),
            })
        if obj is not None:
            from .delivery import locations_payload

            ok, reason = courier.ready()
            context.update({
                "delivery_locations": locations_payload(),
                "phone_orders": Order.objects.filter(phone=obj.phone).count(),
                "courier_ready": ok,
                "courier_reason": reason,
                "courier_name": courier.NAMES.get(courier.provider(), ""),
                "courier_label": courier.courier_label(obj),
                "courier_link": courier.tracking_url(obj),
                "courier_cod": courier.cod_amount(obj),
            })
        return super().render_change_form(request, context, *args, **kwargs)

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
        queryset.filter(delivered_at__isnull=True).update(delivered_at=timezone.now())
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

        if not change and getattr(form, "items", None) is not None:
            # Create order: totals come from the product lines; the delivery
            # charge from the district / thana (staff may type another one).
            from customers.models import Customer

            quote = form.quote or {}
            obj.delivery_zone = quote.get("zone", obj.delivery_zone)
            obj.subtotal = form.subtotal
            obj.discount = form.discount
            obj.shipping = form.cleaned_data.get("shipping") or Decimal("0")
            obj.total = obj.subtotal - obj.discount + obj.shipping
            obj.customer = Customer.objects.filter(phone=obj.phone).first()
            obj.country = "Bangladesh"
            obj.created_by = request.user

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

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        if change or not getattr(form, "items", None):
            return
        from django.contrib import messages

        order = form.instance
        needed = {}
        for product, qty, price in form.items:
            OrderItem.objects.create(order=order, product=product, quantity=qty, price=price)
            needed[product.pk] = (product, needed.get(product.pk, (product, 0))[1] + qty)
        short = []
        for product, qty in needed.values():
            if product.stock < qty:
                short.append(f"{product.name} (had {product.stock})")
            Product.objects.filter(pk=product.pk).update(stock=max(0, product.stock - qty))
        if short:
            messages.warning(request, "Not enough stock for: " + ", ".join(short) + ". Stock was set to 0.")

    def get_urls(self):
        from .admin_orders import customer_lookup, product_search

        urls = super().get_urls()

        custom_urls = [
            path("product-search/", self.admin_site.admin_view(product_search), name="web_order_product_search"),
            path("customer-lookup/", self.admin_site.admin_view(customer_lookup), name="web_order_customer_lookup"),
            path(
                "<path:object_id>/invoice/",
                self.admin_site.admin_view(
                    admin_invoice_view
                ),
                name="web_order_invoice",
            ),
            path("<path:object_id>/courier/<str:action>/",
                 self.admin_site.admin_view(self.courier_view), name="web_order_courier"),
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


# ============================================================
# PAGE TEXT, PAGE LISTS & POLICY PAGES (Phase 3)
# ============================================================

@admin.register(ContentBlock)
class ContentBlockAdmin(TranslationAdmin):
    """Every heading/paragraph on the storefront. Rows come from the templates
    (`manage.py sync_content`), so they can be edited but not added here.
    Clearing a value shows the built-in text again.

    The list is a text editor (templates/admin/web/contentblock/editor.html):
    English and Bangla side by side, saved as you type (quick_save_view)."""

    PAGE_URLS = {"home": "web:home", "about": "web:about", "portfolio": "web:portfolio", "contact": "web:contact",
                 "products": "web:product_list", "cart": "web:cart", "footer": "web:home"}

    list_display = ("key", "page", "preview_en", "preview_bn", "updated_at")
    list_filter = ("page",)
    search_fields = ("key", "label", "value_en", "value_bn")
    readonly_fields = ("key", "page", "allow_html")
    fields = ("key", "page", "label", "value", "allow_html")
    list_per_page = 100

    @admin.display(description="English")
    def preview_en(self, obj):
        return (obj.value_en or "")[:70]

    @admin.display(description="বাংলা")
    def preview_bn(self, obj):
        return (obj.value_bn or "—")[:70]

    def has_add_permission(self, request):
        return False

    def get_urls(self):
        return [
            path("<int:pk>/quick-save/", self.admin_site.admin_view(self.quick_save_view),
                 name="web_contentblock_quick_save"),
        ] + super().get_urls()

    def changelist_view(self, request, extra_context=None):
        blocks = list(ContentBlock.objects.order_by("page", "key"))
        groups = []
        for code, name in ContentBlock.PAGE_CHOICES:
            rows = [b for b in blocks if b.page == code]
            if not rows:
                continue
            for b in rows:
                parts = b.key.split(".")
                b.section = parts[1].replace("_", " ").replace("-", " ").title() if len(parts) > 2 else ""
                b.search = " ".join([b.key, b.label, b.value_en or "", b.value_bn or ""]).lower()
            groups.append({"code": code, "name": name, "rows": rows, "url": reverse(self.PAGE_URLS.get(code, "web:home")),
                           "missing_bn": sum(1 for b in rows if not (b.value_bn or "").strip())})
        context = {
            **self.admin_site.each_context(request),
            "title": "Page text",
            "opts": self.model._meta,
            "groups": groups,
            "total": len(blocks),
            "missing_bn": sum(g["missing_bn"] for g in groups),
            "has_change_permission": self.has_change_permission(request),
            **(extra_context or {}),
        }
        return TemplateResponse(request, "admin/web/contentblock/editor.html", context)

    def quick_save_view(self, request, pk):
        """POST value_en / value_bn → saved at once (from the Page text editor)."""
        from django.http import JsonResponse
        from django.shortcuts import get_object_or_404

        if request.method != "POST":
            return JsonResponse({"ok": False, "error": "POST only"}, status=405)
        block = get_object_or_404(ContentBlock, pk=pk)
        if not self.has_change_permission(request, block):
            return JsonResponse({"ok": False, "error": "You may not change page text."}, status=403)
        changed = []
        for field in ("value_en", "value_bn"):
            if field in request.POST:
                value = request.POST[field].replace("\r\n", "\n").strip()[:5000]
                if value != (getattr(block, field) or ""):
                    setattr(block, field, value)
                    changed.append(field)
        if changed:
            block.save(update_fields=changed + ["updated_at"])
            self.log_change(request, block, [{"changed": {"fields": changed}}])
        return JsonResponse({"ok": True, "changed": changed,
                             "updated": timezone.localtime(block.updated_at).strftime("%d %b, %I:%M %p")})


@admin.register(ContentItem)
class ContentItemAdmin(TranslationAdmin):
    formfield_overrides = RICH_TEXT_COMPACT
    list_display = ("group", "order", "icon", "value", "title", "is_active")
    list_display_links = ("title",)
    list_editable = ("order", "is_active")
    list_filter = ("group", "is_active")
    search_fields = ("title_en", "title_bn", "text_en", "text_bn")
    fields = ("group", "order", "icon", "value", "title", "text", "is_active")


@admin.register(Page)
class PageAdmin(TranslationAdmin):
    formfield_overrides = RICH_TEXT
    form = PageAdminForm
    list_display = ("title", "slug", "kind", "show_in_footer", "is_active", "order", "updated_at")
    list_editable = ("show_in_footer", "is_active", "order")
    prepopulated_fields = {"slug": ("title",)}
    fieldsets = (
        ("Page", {"fields": ("title", "slug", "kind", "intro")}),
        ("Text", {"fields": ("body",)}),
        ("FAQ", {"description": FAQ_HELP + " For a “Questions & answers” page, the questions in the text box above are shown too.",
                 "fields": ("faq",)}),
        ("SEO & sharing", {"description": SEO_HELP,
                           "fields": ("seo_title", "meta_description", "seo_keywords", "share_image")}),
        ("Settings", {"fields": ("show_in_footer", "is_active", "order")}),
    )


@admin.register(PageSeo)
class PageSeoAdmin(TranslationAdmin):
    """Google title / description and share picture for Home, Products, Portfolio, About and Contact."""

    form = PageSeoAdminForm
    list_display = ("page", "title_used", "description_used", "keyword_count", "faq_count", "has_image", "noindex")
    fieldsets = (
        ("Page", {"fields": ("page", "noindex")}),
        ("SEO & sharing", {"description": SEO_HELP,
                           "fields": ("title", "description", "seo_keywords", "share_image")}),
        ("FAQ", {"description": FAQ_HELP, "fields": ("faq",)}),
    )
    readonly_fields = ("page",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(n_keywords=Count("seo_keywords"))

    @admin.display(description="Keywords", ordering="n_keywords")
    def keyword_count(self, obj):
        return obj.n_keywords

    @admin.display(description="FAQ")
    def faq_count(self, obj):
        return len(obj.faq_en or [])

    @admin.display(description="Title")
    def title_used(self, obj):
        return obj.title or "— built-in —"

    @admin.display(description="Description")
    def description_used(self, obj):
        return (obj.description[:80] + "…") if len(obj.description) > 80 else (obj.description or "— built-in —")

    @admin.display(description="Share image", boolean=True)
    def has_image(self, obj):
        return bool(obj.share_image)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SeoKeyword)
class SeoKeywordAdmin(admin.ModelAdmin):
    """Every SEO keyword typed anywhere. Renaming one renames it everywhere it is used."""

    list_display = ("name", "used_on", "created_at")
    search_fields = ("name",)
    fields = ("name",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            n_products=Count("products", distinct=True), n_categories=Count("categories", distinct=True),
            n_pages=Count("pages", distinct=True), n_site_pages=Count("site_pages", distinct=True))

    @admin.display(description="Used on")
    def used_on(self, obj):
        parts = [(obj.n_products, "product"), (obj.n_categories, "category"), (obj.n_pages, "policy page"),
                 (obj.n_site_pages, "site page")]
        text = ", ".join(f"{n} {label}{'' if n == 1 else 's'}" for n, label in parts if n)
        return text or "— not used —"


# ============================================================
# DELIVERY CHARGES: DISTRICTS & THANAS (DataTables, inline fee editing)
# ============================================================

def _fee_input(url, value, placeholder=""):
    return format_html(
        '<input type="number" min="0" step="5" class="dt-fee" value="{}" placeholder="{}" data-url="{}" '
        'aria-label="Delivery charge">',
        "" if value is None else value, placeholder, url,
    )


class _SetFeeMixin:
    """POST <pk>/set-fee/ with fee=<number> (empty = use district charge, thanas only)."""

    fee_can_be_empty = False

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        return [
            path("<int:pk>/set-fee/", self.admin_site.admin_view(self.set_fee_view), name="%s_%s_set_fee" % info),
        ] + super().get_urls()

    def set_fee_view(self, request, pk):
        from django.http import JsonResponse

        obj = self.get_object(request, str(pk))
        if request.method != "POST" or obj is None or not self.has_change_permission(request, obj):
            return JsonResponse({"ok": False, "error": "Not allowed"}, status=403)
        raw = (request.POST.get("fee") or "").strip()
        if raw == "" and self.fee_can_be_empty:
            obj.delivery_fee = None
        else:
            try:
                fee = int(raw)
                if fee < 0:
                    raise ValueError
            except ValueError:
                return JsonResponse({"ok": False, "error": "Enter a whole number of taka (0 or more)."}, status=400)
            obj.delivery_fee = fee
        obj.save(update_fields=["delivery_fee"])
        self.log_change(request, obj, f"Delivery charge set to {obj.delivery_fee}")
        return JsonResponse({"ok": True, "fee": obj.delivery_fee})


class ThanaInline(TranslationTabularInline):
    model = Thana
    extra = 1
    fields = ("name", "delivery_fee", "is_active", "pathao_zone_id")


@admin.register(District)
class DistrictAdmin(_SetFeeMixin, DataTablesAdminMixin, TranslationAdmin):
    list_display = ("name", "division", "fee_column", "delivery_eta", "thana_count", "is_active")
    list_filter = ("division", "is_active")
    search_fields = ("name_en", "name_bn")
    ordering = ("name_en",)
    fields = ("name", "division", "delivery_fee", "delivery_eta", "is_active", "pathao_city_id")
    inlines = [ThanaInline]
    actions = ["match_pathao"]

    @admin.action(description="Match Pathao cities & zones (all districts)")
    def match_pathao(self, request, queryset):
        from django.contrib import messages

        from . import courier

        try:
            summary = courier.match_pathao_locations()
        except courier.CourierError as exc:
            messages.error(request, f"Pathao: {exc}")
            return
        messages.success(request, f"Pathao numbers saved for {summary['districts']} districts and {summary['thanas']} thanas.")
        if summary["missing_districts"] or summary["missing_thanas"]:
            messages.warning(request, "Not matched — type these numbers by hand: "
                             + ", ".join(summary["missing_districts"][:15])
                             + (f" · {summary['missing_thanas']} thanas" if summary["missing_thanas"] else ""))

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_thanas=Count("thanas"))

    @admin.display(description="Delivery charge (৳)", ordering="delivery_fee")
    def fee_column(self, obj):
        return _fee_input(reverse("admin:web_district_set_fee", args=[obj.pk]), obj.delivery_fee)

    @admin.display(description="Thanas", ordering="_thanas")
    def thana_count(self, obj):
        url = reverse("admin:web_thana_changelist") + f"?district__id__exact={obj.pk}"
        return format_html('<a href="{}">{}</a>', url, obj._thanas)

    def has_delete_permission(self, request, obj=None):
        return False  # untick "active" instead; orders refer to districts by name


@admin.register(Thana)
class ThanaAdmin(_SetFeeMixin, DataTablesAdminMixin, TranslationAdmin):
    fee_can_be_empty = True
    list_display = ("name", "district", "fee_column", "charge_used", "is_active")
    list_filter = ("district__division", "district", "is_active")
    search_fields = ("name_en", "name_bn", "district__name_en", "district__name_bn")
    list_select_related = ("district",)
    ordering = ("district__name_en", "name_en")
    fields = ("district", "name", "delivery_fee", "is_active", "pathao_zone_id")
    autocomplete_fields = ()

    @admin.display(description="Own charge (৳) — empty = district's", ordering="delivery_fee")
    def fee_column(self, obj):
        return _fee_input(reverse("admin:web_thana_set_fee", args=[obj.pk]), obj.delivery_fee,
                          placeholder=str(obj.district.delivery_fee))

    @admin.display(description="Customer pays")
    def charge_used(self, obj):
        return f"৳{obj.effective_fee}"


# Admin titles (browser tab, dashboard heading).
admin.site.site_header = "WaRa BD"
admin.site.site_title = "WaRa Admin"
admin.site.index_title = "Dashboard"
