from datetime import timedelta
from decimal import Decimal

from django import template
from django.contrib.admin.templatetags.admin_list import result_headers
from django.db.models import Count, Q, Sum
from django.utils import timezone

register = template.Library()


@register.simple_tag
def dt_headers(cl):
    """Column headers for the DataTables admin list (same columns as list_display)."""
    return list(result_headers(cl))


def _local_midnight(dt):
    return timezone.localtime(dt).replace(hour=0, minute=0, second=0, microsecond=0)


@register.simple_tag
def admin_counts():
    """Small numbers for the sidebar badges (one query per model)."""
    from web.models import ContactMessage, Order

    orders = Order.objects.aggregate(
        pending=Count("id", filter=Q(status=Order.STATUS_PENDING)),
        verifying=Count("id", filter=Q(payment_status=Order.PAYMENT_VERIFYING)),
    )
    return {
        "orders_pending": orders["pending"],
        "payments_verifying": orders["verifying"],
        "messages_unread": ContactMessage.objects.filter(is_read=False).count(),
    }


@register.simple_tag
def admin_dashboard():
    """Everything the admin home page shows.

    Month grouping is done in Python: MySQL on XAMPP has no time-zone tables,
    so database-side TruncMonth / __date lookups return NULL there.
    """
    from customers.models import Customer, SmsLog
    from web.models import ContactMessage, Order, Product

    now = timezone.now()
    today = _local_midnight(now)
    month_start = today.replace(day=1)
    live = Order.objects.exclude(status=Order.STATUS_CANCELLED)

    def total(qs):
        return qs.aggregate(t=Sum("total"))["t"] or Decimal("0")

    # Last 6 calendar months, oldest first.
    months = []
    cursor = month_start
    for _ in range(6):
        months.insert(0, cursor)
        cursor = (cursor - timedelta(days=1)).replace(day=1)
    revenue = {m: Decimal("0") for m in months}
    counts = {m: 0 for m in months}
    for created, amount in live.filter(created_at__gte=months[0]).values_list("created_at", "total"):
        key = _local_midnight(created).replace(day=1)
        if key in revenue:
            revenue[key] += amount or 0
            counts[key] += 1

    status_rows = dict(Order.objects.values_list("status").annotate(n=Count("id")))
    status_labels = dict(Order.STATUS_CHOICES)

    top_districts = (
        live.exclude(city="").values("city").annotate(n=Count("id"), amount=Sum("total")).order_by("-n")[:5]
    )

    return {
        "orders_today": Order.objects.filter(created_at__gte=today).count(),
        "revenue_today": total(live.filter(created_at__gte=today)),
        "revenue_month": total(live.filter(created_at__gte=month_start)),
        "revenue_total": total(live),
        "orders_total": Order.objects.count(),
        "orders_pending": status_rows.get(Order.STATUS_PENDING, 0),
        "payments_verifying": Order.objects.filter(payment_status=Order.PAYMENT_VERIFYING).count(),
        "products_active": Product.objects.filter(is_active=True).count(),
        "products_out": Product.objects.filter(is_active=True).filter(
            Q(stock_status=Product.STOCK_OUT) | Q(stock=0)
        ).count(),
        "customers_total": Customer.objects.count(),
        "customers_new": Customer.objects.filter(created_at__gte=month_start).count(),
        "messages_unread": ContactMessage.objects.filter(is_read=False).count(),
        "sms_today": SmsLog.objects.filter(created_at__gte=today, status=SmsLog.STATUS_SENT).count(),
        "sms_failed_today": SmsLog.objects.filter(created_at__gte=today, status=SmsLog.STATUS_FAILED).count(),
        "chart_months": [m.strftime("%b %Y") for m in months],
        "chart_revenue": [float(revenue[m]) for m in months],
        "chart_orders": [counts[m] for m in months],
        "status_breakdown": [
            {"key": key, "label": str(label), "n": status_rows.get(key, 0)} for key, label in Order.STATUS_CHOICES
        ],
        "status_labels": status_labels,
        "top_districts": list(top_districts),
        "recent_orders": list(Order.objects.order_by("-created_at")[:8]),
        "low_stock": list(
            Product.objects.filter(is_active=True, stock__lte=3).order_by("stock", "name")[:6]
        ),
    }


@register.filter
def wf_wide(admin_field):
    """True when a form field needs the whole row: text boxes, editors, keyword pickers, uploads."""
    from django import forms

    bound = getattr(admin_field, "field", None)
    widget = getattr(getattr(bound, "field", None), "widget", None)
    if widget is None:  # read-only value
        return False
    widget = getattr(widget, "widget", widget)  # "add another" wrapper around selects
    return isinstance(widget, (forms.Textarea, forms.SelectMultiple, forms.ClearableFileInput,
                               forms.CheckboxSelectMultiple))


@register.filter
def wf_has(classes, name):
    """'collapse wide'|wf_has:'collapse' -> True"""
    return name in str(classes or "").split()
