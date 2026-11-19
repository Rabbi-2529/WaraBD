# web/urls.py
from django.urls import path
from . import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("products/<slug:slug>/", views.product_detail, name="product_detail"),
    path("portfolio/", views.portfolio, name="portfolio"),
    path("about/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("api/contact/", views.api_contact, name="api_contact"),
    
    # Cart
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:product_id>/", views.cart_add, name="cart_add"),
    path("cart/update/<int:product_id>/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:product_id>/", views.cart_remove, name="cart_remove"),
    
    # Checkout & Orders
    path("checkout/", views.checkout, name="checkout"),
    path("api/checkout/", views.api_checkout, name="api_checkout"),
    path("order/success/<str:order_number>/", views.order_success, name="order_success"),
    path("order/failed/", views.order_failed, name="order_failed"),
    
    # 🟢 FIXED: Uses object_id
    path("admin-invoice/<int:object_id>/", views.admin_invoice_view, name="admin_invoice"),
]