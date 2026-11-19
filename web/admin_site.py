# web/admin_site.py
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from .models import Product, Order, ContactMessage

class RizzAdminSite(AdminSite):
    site_header = "WaRa BD"
    site_title = "WaRa Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        User = get_user_model()

        # 1. KPI Stats
        total_revenue = Order.objects.exclude(status=Order.STATUS_CANCELLED).aggregate(total=Sum('total'))['total'] or 0
        total_orders = Order.objects.count()
        total_products = Product.objects.filter(is_active=True).count()
        unread_messages = ContactMessage.objects.filter(is_read=False).count()
        
        # 2. Recent Activity
        recent_orders = Order.objects.order_by('-created_at')[:5]
        
        # 3. Chart Data (Last 6 Months)
        six_months_ago = timezone.now() - timedelta(days=180)
        monthly_qs = Order.objects.filter(created_at__gte=six_months_ago) \
            .annotate(month=TruncMonth('created_at')) \
            .values('month') \
            .annotate(revenue=Sum('total'), orders=Count('id')) \
            .order_by('month')

        chart_months = [item['month'].strftime('%b') for item in monthly_qs]
        chart_revenue = [float(item['revenue'] or 0) for item in monthly_qs]
        chart_orders = [item['orders'] for item in monthly_qs]

        extra_context.update({
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "total_products": total_products,
            "unread_messages": unread_messages,
            "recent_orders": recent_orders,
            
            # Pass chart data to template
            "chart_months": chart_months,
            "chart_revenue": chart_revenue,
            "chart_orders": chart_orders,
        })
        return super().index(request, extra_context=extra_context)