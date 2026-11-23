"""Customer pages: phone login / registration with SMS code, OTP page, My Account."""

from datetime import timedelta

from django.contrib import messages
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from web.checkout import PLACED_KEY, place_checkout_order
from web.delivery import locations_payload
from web.models import Order, SiteSettings
from web.views import order_progress

from .auth import customer_required, login_customer, logout_customer
from .forms import AddressForm, ChangePhoneForm, LoginForm, NewNumberForm, OtpForm, ProfileForm, RegisterForm
from .models import Customer, CustomerAddress, OtpCode
from .otp import (
    OtpError,
    TEST_CODE_KEY,
    clear_pending,
    pending_otp,
    request_otp,
    seconds_until_resend,
    sms_mode,
    verify_otp,
)

DRAFT_KEY = "otp_draft"  # form values kept while the customer changes the number


def _safe_next(request, fallback):
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()},
                                                  require_https=request.is_secure()):
        return target
    return fallback


def _draft(request, purpose):
    draft = request.session.get(DRAFT_KEY) or {}
    return draft.get("data", {}) if draft.get("purpose") == purpose else {}


def _send_to_new_number(request, otp, phone):
    """Send the pending code's purpose to another number (already 01XXXXXXXXX).

    Returns an error message, or None when the new code was sent. If anything
    fails, the old code stays valid."""
    if phone == otp.phone:
        return _("That is the same number. Enter the code we sent, or tap Resend code.")
    if otp.purpose == OtpCode.PURPOSE_LOGIN and not Customer.objects.filter(phone=phone, is_active=True).exists():
        return _("No account uses this number yet. Create an account instead.")
    if otp.purpose == OtpCode.PURPOSE_REGISTER and Customer.objects.filter(phone=phone).exists():
        return _("This number already has an account. Please log in.")
    if otp.purpose == OtpCode.PURPOSE_CHANGE_PHONE and Customer.objects.filter(phone=phone).exists():
        return _("This number already belongs to another account.")

    payload = dict(otp.payload or {})
    if otp.purpose == OtpCode.PURPOSE_CHECKOUT and isinstance(payload.get("checkout"), dict):
        payload["checkout"] = {**payload["checkout"], "phone": phone}
    try:
        request_otp(request, phone=phone, purpose=otp.purpose, payload=payload)
    except OtpError as exc:
        return str(exc)
    otp.cancelled = True
    otp.save(update_fields=["cancelled"])
    messages.success(request, _("A new code has been sent to %(phone)s.") % {"phone": phone})
    return None


# ------------------------------------------------------------------------------
# Login & registration
# ------------------------------------------------------------------------------

def login_view(request):
    if request.customer:
        return redirect("customers:account")
    next_url = _safe_next(request, reverse("customers:account"))
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data["phone"]
            if not Customer.objects.filter(phone=phone, is_active=True).exists():
                form.add_error("phone", _("No account uses this number yet. Create an account instead."))
            else:
                try:
                    request_otp(request, phone=phone, purpose=OtpCode.PURPOSE_LOGIN, payload={"next": next_url})
                except OtpError as exc:
                    form.add_error("phone", str(exc))
                else:
                    return redirect("customers:otp")
    else:
        form = LoginForm(initial=_draft(request, OtpCode.PURPOSE_LOGIN))
    return render(request, "customers/login.html", {"form": form, "next": next_url})


def register_view(request):
    if request.customer:
        return redirect("customers:account")
    next_url = _safe_next(request, reverse("customers:account"))
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if Customer.objects.filter(phone=data["phone"]).exists():
                form.add_error("phone", _("This number already has an account. Please log in."))
            else:
                try:
                    request_otp(request, phone=data["phone"], purpose=OtpCode.PURPOSE_REGISTER,
                                payload={"name": data["name"], "email": data["email"], "next": next_url})
                except OtpError as exc:
                    form.add_error("phone", str(exc))
                else:
                    return redirect("customers:otp")
    else:
        form = RegisterForm(initial=_draft(request, OtpCode.PURPOSE_REGISTER))
    return render(request, "customers/register.html", {"form": form, "next": next_url})


@require_POST
def logout_view(request):
    logout_customer(request)
    messages.success(request, _("You have been logged out."))
    return redirect("web:home")


# ------------------------------------------------------------------------------
# OTP page (shared by login, registration, orders and number changes)
# ------------------------------------------------------------------------------

def _order_just_placed(request):
    """The order this browser placed in the last 15 minutes, if any.

    A second tap on "Confirm & place order" (or going back to the code page)
    arrives after the code was used: show that order again, not "code expired"."""
    placed = request.session.get(PLACED_KEY) or []
    if not placed:
        return None
    since = timezone.now() - timedelta(minutes=15)
    return Order.objects.filter(order_number=placed[-1], created_at__gte=since).first()


def otp_view(request):
    otp = pending_otp(request)
    if otp is None:
        order = _order_just_placed(request)
        if order:
            return redirect(f"{reverse('web:order_success', args=[order.order_number])}?placed=1")
        messages.info(request, _("Your code has expired or was already used. Please start again."))
        return redirect("customers:login")

    site = SiteSettings.load()
    form = OtpForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            verify_otp(request, otp, form.cleaned_data["code"])
        except OtpError as exc:
            form.add_error("code", str(exc))
        else:
            request.session.pop(DRAFT_KEY, None)
            return _finish(request, otp)

    return render(request, "customers/otp.html", {
        "form": form,
        "otp": otp,
        "resend_in": seconds_until_resend(otp.phone, site),
        "valid_minutes": site.otp_valid_minutes,
        "test_code": request.session.get(TEST_CODE_KEY) if sms_mode(site) == "test" else None,
    })


def _finish(request, otp):
    """What happens after the right code was entered."""
    payload = otp.payload or {}

    if otp.purpose == OtpCode.PURPOSE_LOGIN:
        customer = Customer.objects.filter(phone=otp.phone, is_active=True).first()
        if customer is None:
            messages.error(request, _("This account is not available. Please contact us."))
            return redirect("customers:login")
        login_customer(request, customer)
        messages.success(request, _("Welcome back, %(name)s!") % {"name": customer.name})
        return redirect(payload.get("next") or "customers:account")

    if otp.purpose == OtpCode.PURPOSE_REGISTER:
        customer, created = Customer.objects.get_or_create(
            phone=otp.phone, defaults={"name": payload.get("name", ""), "email": payload.get("email", "")},
        )
        login_customer(request, customer)
        messages.success(request, _("Your account is ready, %(name)s!") % {"name": customer.name}
                         if created else _("Welcome back, %(name)s!") % {"name": customer.name})
        return redirect(payload.get("next") or "customers:account")

    if otp.purpose == OtpCode.PURPOSE_CHECKOUT:
        customer = request.customer or Customer.objects.filter(phone=otp.phone, is_active=True).first()
        order, error, _status = place_checkout_order(request, payload.get("checkout") or {}, customer=customer)
        if error:
            messages.error(request, error)
            return redirect("web:checkout")
        return redirect(f"{reverse('web:order_success', args=[order.order_number])}?placed=1")

    if otp.purpose == OtpCode.PURPOSE_CHANGE_PHONE:
        customer = request.customer
        if not customer or customer.pk != payload.get("customer_id"):
            raise Http404
        if Customer.objects.filter(phone=otp.phone).exclude(pk=customer.pk).exists():
            messages.error(request, _("This number already belongs to another account."))
            return redirect("customers:profile")
        customer.phone = otp.phone
        customer.save(update_fields=["phone"])
        messages.success(request, _("Your mobile number has been changed."))
        return redirect("customers:profile")

    raise Http404


@require_POST
def otp_resend(request):
    otp = pending_otp(request)
    if otp is None:
        return redirect("customers:login")
    try:
        request_otp(request, phone=otp.phone, purpose=otp.purpose, payload=otp.payload)
    except OtpError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, _("A new code has been sent."))
    return redirect("customers:otp")


def otp_change_number(request):
    """Code page → "Change number": a page with only the mobile number box.

    A new code goes to the new number and the customer is back on the code page;
    everything else they typed (name, address, cart …) is kept.
    """
    otp = pending_otp(request)
    if otp is None:
        return redirect("customers:login")
    if request.method == "POST" and "phone" not in request.POST:
        return _cancel_and_go_back(request, otp)
    form = NewNumberForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        error = _send_to_new_number(request, otp, form.cleaned_data["phone"])
        if error is None:
            return redirect("customers:otp")
        form.add_error("phone", error)
    return render(request, "customers/otp_change.html", {"form": form, "otp": otp})


def _cancel_and_go_back(request, otp):
    """Old "Change number" behaviour: cancel the code and return to the form the customer came from."""
    otp.cancelled = True
    otp.save(update_fields=["cancelled"])
    clear_pending(request)
    payload = dict(otp.payload or {})

    if otp.purpose == OtpCode.PURPOSE_CHECKOUT:
        # The checkout form refills itself from the browser (app.js) and focuses the phone field.
        return redirect(f"{reverse('web:checkout')}?change=phone")
    if otp.purpose == OtpCode.PURPOSE_CHANGE_PHONE:
        return redirect(f"{reverse('customers:profile')}#change-number")

    keep = {k: payload[k] for k in ("name", "email") if payload.get(k)}
    keep["phone"] = otp.phone
    request.session[DRAFT_KEY] = {"purpose": otp.purpose, "data": keep}
    target = "customers:register" if otp.purpose == OtpCode.PURPOSE_REGISTER else "customers:login"
    return redirect(f"{reverse(target)}?change=phone")


# ------------------------------------------------------------------------------
# My Account
# ------------------------------------------------------------------------------

@customer_required
def account_view(request):
    orders = request.customer.orders.order_by("-created_at")
    return render(request, "customers/account.html", {
        "recent_orders": orders[:3],
        "order_count": orders.count(),
        "address": request.customer.default_address,
        "section": "dashboard",
    })


@customer_required
def orders_view(request):
    return render(request, "customers/orders.html", {
        "orders": request.customer.orders.order_by("-created_at").prefetch_related("items"),
        "section": "orders",
    })


@customer_required
def order_detail_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number, customer=request.customer)
    return render(request, "customers/order_detail.html", {
        "order": order, "progress": order_progress(order), "section": "orders",
    })


@customer_required
def profile_view(request):
    customer = request.customer
    profile_form = ProfileForm(initial={"name": customer.name, "email": customer.email})
    phone_form = ChangePhoneForm()
    if request.method == "POST" and request.POST.get("form") == "profile":
        profile_form = ProfileForm(request.POST)
        if profile_form.is_valid():
            customer.name = profile_form.cleaned_data["name"]
            customer.email = profile_form.cleaned_data["email"]
            customer.save(update_fields=["name", "email"])
            messages.success(request, _("Your profile has been saved."))
            return redirect("customers:profile")
    elif request.method == "POST" and request.POST.get("form") == "phone":
        phone_form = ChangePhoneForm(request.POST)
        if phone_form.is_valid():
            phone = phone_form.cleaned_data["phone"]
            if phone == customer.phone:
                phone_form.add_error("phone", _("This is already your number."))
            elif Customer.objects.filter(phone=phone).exists():
                phone_form.add_error("phone", _("This number already belongs to another account."))
            else:
                try:
                    request_otp(request, phone=phone, purpose=OtpCode.PURPOSE_CHANGE_PHONE,
                                payload={"customer_id": customer.pk})
                except OtpError as exc:
                    phone_form.add_error("phone", str(exc))
                else:
                    return redirect("customers:otp")
    return render(request, "customers/profile.html", {
        "profile_form": profile_form, "phone_form": phone_form, "section": "profile",
    })


@customer_required
def addresses_view(request):
    return render(request, "customers/addresses.html", {
        "addresses": request.customer.addresses.all(), "section": "addresses",
    })


@customer_required
def address_edit_view(request, pk=None):
    customer = request.customer
    address = get_object_or_404(CustomerAddress, pk=pk, customer=customer) if pk else None
    initial = {} if address else {"name": customer.name, "phone": customer.phone,
                                  "is_default": not customer.addresses.exists()}
    form = AddressForm(request.POST or None, instance=address, initial=initial)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        saved.customer = customer
        saved.save()
        if saved.is_default:
            customer.addresses.exclude(pk=saved.pk).update(is_default=False)
        messages.success(request, _("Address saved."))
        return redirect("customers:addresses")
    return render(request, "customers/address_form.html", {
        "form": form, "address": address, "section": "addresses",
        "delivery_locations": locations_payload(),
    })


@customer_required
@require_POST
def address_delete_view(request, pk):
    address = get_object_or_404(CustomerAddress, pk=pk, customer=request.customer)
    was_default = address.is_default
    address.delete()
    if was_default:
        first = request.customer.addresses.first()
        if first:
            first.is_default = True
            first.save(update_fields=["is_default"])
    messages.success(request, _("Address deleted."))
    return redirect("customers:addresses")


@customer_required
@require_POST
def address_default_view(request, pk):
    address = get_object_or_404(CustomerAddress, pk=pk, customer=request.customer)
    request.customer.addresses.update(is_default=False)
    address.is_default = True
    address.save(update_fields=["is_default"])
    return redirect("customers:addresses")
