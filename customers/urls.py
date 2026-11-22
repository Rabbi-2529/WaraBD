from django.urls import path

from . import views

app_name = "customers"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("verify/", views.otp_view, name="otp"),
    path("verify/resend/", views.otp_resend, name="otp_resend"),
    path("verify/change-number/", views.otp_change_number, name="otp_change_number"),
    path("", views.account_view, name="account"),
    path("orders/", views.orders_view, name="orders"),
    path("orders/<str:order_number>/", views.order_detail_view, name="order_detail"),
    path("profile/", views.profile_view, name="profile"),
    path("addresses/", views.addresses_view, name="addresses"),
    path("addresses/new/", views.address_edit_view, name="address_add"),
    path("addresses/<int:pk>/edit/", views.address_edit_view, name="address_edit"),
    path("addresses/<int:pk>/delete/", views.address_delete_view, name="address_delete"),
    path("addresses/<int:pk>/default/", views.address_default_view, name="address_default"),
]
