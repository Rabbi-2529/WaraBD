# web/urls.py
from django.urls import path
from . import views

app_name = "web"

urlpatterns = [
    path("", views.home, name="home"),
    path("products/", views.product_list, name="product_list"),
    path("category/<slug:slug>/", views.category_detail, name="category"),
    # Old product address (/products/<slug>/) → permanent redirect to /<slug>
    path("products/<slug:slug>/", views.product_old_url, name="product_old_url"),
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
    path("api/checkout/lookup/", views.api_checkout_lookup, name="api_checkout_lookup"),
    path("order/success/<str:order_number>/", views.order_success, name="order_success"),
    path("order/<str:order_number>/invoice/", views.order_invoice, name="order_invoice"),
    path("order/failed/", views.order_failed, name="order_failed"),
    path("track-order/", views.track_order, name="track_order"),

    # Policy / info pages (privacy, terms, returns, warranty & delivery, FAQ …)
    path("page/<slug:slug>/", views.page_detail, name="page"),
    
    # 🟢 FIXED: Uses object_id
    path("admin-invoice/<int:object_id>/", views.admin_invoice_view, name="admin_invoice"),

    # Product pages live at the site root, StarTech style: /huion-420-H420
    # (no trailing slash). Must stay LAST so it never hides another page.
    path("<slug:slug>", views.product_detail, name="product_detail"),
]