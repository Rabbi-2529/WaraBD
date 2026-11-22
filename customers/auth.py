"""Customer login sessions (separate from staff /admin/ logins).

A logged-in customer is stored as `customer_id` in the session; the
middleware exposes it as `request.customer` (None when logged out).
Numbers verified by SMS in this browser today are remembered in
`verified_phones`, so the same number is not sent another code today.
"""

from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

SESSION_KEY = "customer_id"
VERIFIED_KEY = "verified_phones"


def get_customer(request):
    from .models import Customer

    customer_id = request.session.get(SESSION_KEY)
    if not customer_id:
        return None
    customer = Customer.objects.filter(pk=customer_id, is_active=True).first()
    if customer is None:
        request.session.pop(SESSION_KEY, None)
    return customer


def login_customer(request, customer):
    request.session.cycle_key()  # new session id on login (session fixation)
    request.session[SESSION_KEY] = customer.pk
    customer.last_login = timezone.now()
    customer.save(update_fields=["last_login"])
    request.customer = customer
    remember_verified_phone(request, customer.phone)


def logout_customer(request):
    request.session.pop(SESSION_KEY, None)
    request.session.pop(VERIFIED_KEY, None)
    request.session.cycle_key()
    request.customer = None


def _today():
    return timezone.localdate().isoformat()


def remember_verified_phone(request, phone):
    verified = {p: d for p, d in request.session.get(VERIFIED_KEY, {}).items() if d == _today()}
    verified[phone] = _today()
    request.session[VERIFIED_KEY] = verified


def phone_verified_today(request, phone):
    """True when this browser verified `phone` by SMS today, or it is the logged-in customer's number."""
    customer = getattr(request, "customer", None)
    if customer and customer.phone == phone:  # lazy object: truthy only when logged in
        return True
    return request.session.get(VERIFIED_KEY, {}).get(phone) == _today()


def customer_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not getattr(request, "customer", None):
            messages.info(request, _("Please log in with your mobile number."))
            return redirect(f"{reverse('customers:login')}?next={request.get_full_path()}")
        return view(request, *args, **kwargs)

    return wrapper
