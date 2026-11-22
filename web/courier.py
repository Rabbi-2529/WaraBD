"""Courier booking and tracking (Phase 5).

Pick the courier and fill in its keys in the admin: Site settings → Courier.

* Steadfast Courier  — API key + secret key  (https://portal.packzy.com/api/v1)
* Pathao Courier     — client id/secret, merchant email/password, store id
                       (https://api-hermes.pathao.com). Pathao needs its own
                       city / zone numbers: use "Match Pathao cities & zones"
                       on the District charges list once.
* Any other courier  — leave "Courier" empty and type the courier name and
                       tracking code on the order page.

Nothing here runs by itself: staff press "Send to courier" on an order (or
use the bulk action), and "Refresh status" / `manage.py courier_sync` pulls
the latest delivery status.
"""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

from django.core.cache import cache
from django.utils import timezone

from .models import District, Order, SiteSettings, Thana

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 20

STEADFAST = "steadfast"
PATHAO = "pathao"
NAMES = {STEADFAST: "Steadfast", PATHAO: "Pathao"}
TRACKING_URLS = {
    STEADFAST: "https://steadfast.com.bd/t/{code}",
    PATHAO: "https://merchant.pathao.com/tracking?consignment_id={code}&phone={phone}",
}

# Courier status words → our order status. Anything else only updates the courier status text.
DELIVERED_WORDS = {"delivered", "partial_delivered"}
CANCELLED_WORDS = {"cancelled", "pickup_cancelled", "return", "returned", "paid_return"}


class CourierError(Exception):
    """A message staff can read (shown on the order page)."""


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def _request(method, url, *, headers=None, payload=None):
    body = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=body, method=method, headers={
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "WaRaBD-Store/1.0",
        **(headers or {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            raw = resp.read(200_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read(20_000).decode("utf-8", "replace")
        raise CourierError(_api_message(raw) or f"Courier answered HTTP {exc.code}.") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise CourierError(f"Could not reach the courier ({exc}). Check the internet connection and API URL.") from exc
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise CourierError("The courier sent back something that is not JSON.") from exc


def _api_message(raw):
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return ""
    if not isinstance(data, dict):
        return ""
    parts = [str(data.get("message") or "")]
    errors = data.get("errors")
    if isinstance(errors, dict):
        for key, value in errors.items():
            parts.append(f"{key}: {', '.join(value) if isinstance(value, list) else value}")
    return " — ".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# Order helpers
# ---------------------------------------------------------------------------

def provider(site=None):
    site = site or SiteSettings.load()
    return site.courier_provider or ""


def ready(site=None):
    """(ok, reason) — is the chosen courier filled in enough to book parcels?"""
    site = site or SiteSettings.load()
    name = provider(site)
    if not name:
        return False, "No courier is connected. Choose one in Site settings → Courier, or type the tracking code by hand."
    if name == STEADFAST and not (site.steadfast_api_key and site.steadfast_secret_key):
        return False, "Fill in the Steadfast API key and secret key in Site settings → Courier."
    if name == PATHAO and not all([site.pathao_client_id, site.pathao_client_secret, site.pathao_username,
                                   site.pathao_password, site.pathao_store_id]):
        return False, "Fill in all Pathao fields (client id, secret, email, password, store id) in Site settings → Courier."
    return True, ""


def cod_amount(order):
    """What the rider collects: the order total unless it is already paid."""
    if order.payment_status == Order.PAYMENT_PAID:
        return Decimal("0")
    return order.total or Decimal("0")


def full_address(order):
    parts = [order.address_line1, order.address_line2, order.thana, order.city]
    return ", ".join(p.strip() for p in parts if p and p.strip())


def item_summary(order):
    items = list(order.items.select_related("product"))
    text = ", ".join(f"{i.product.name} x{i.quantity}" for i in items)
    return text[:240], sum(i.quantity for i in items) or 1


def tracking_url(order):
    if order.courier_tracking_url:
        return order.courier_tracking_url
    template = TRACKING_URLS.get(order.courier)
    code = order.courier_tracking_code or order.courier_consignment_id
    if not (template and code):
        return ""
    return template.format(code=urllib.parse.quote(str(code)), phone=urllib.parse.quote(order.phone or ""))


def courier_label(order):
    return NAMES.get(order.courier, order.courier)


# ---------------------------------------------------------------------------
# Steadfast
# ---------------------------------------------------------------------------

def _steadfast_headers(site):
    return {"Api-Key": site.steadfast_api_key, "Secret-Key": site.steadfast_secret_key}


def _steadfast_book(order, site):
    url = site.steadfast_api_url.rstrip("/") + "/create_order"
    note = order.notes[:200] if order.notes else ""
    data = _request("POST", url, headers=_steadfast_headers(site), payload={
        "invoice": order.order_number,
        "recipient_name": order.full_name[:100],
        "recipient_phone": order.phone,
        "recipient_address": full_address(order)[:250],
        "cod_amount": float(cod_amount(order)),
        "note": note,
    })
    consignment = data.get("consignment") if isinstance(data, dict) else None
    if not consignment or int(data.get("status") or 0) != 200:
        raise CourierError(_api_message(json.dumps(data)) or "Steadfast did not accept the parcel.")
    return {
        "consignment_id": str(consignment.get("consignment_id") or ""),
        "tracking_code": str(consignment.get("tracking_code") or ""),
        "status": str(consignment.get("status") or "in_review"),
    }


def _steadfast_status(order, site):
    base = site.steadfast_api_url.rstrip("/")
    if order.courier_consignment_id:
        url = f"{base}/status_by_cid/{urllib.parse.quote(order.courier_consignment_id)}"
    else:
        url = f"{base}/status_by_invoice/{urllib.parse.quote(order.order_number)}"
    data = _request("GET", url, headers=_steadfast_headers(site))
    status = data.get("delivery_status") if isinstance(data, dict) else None
    if not status:
        raise CourierError(_api_message(json.dumps(data)) or "Steadfast did not return a status.")
    return str(status)


def steadfast_balance(site=None):
    site = site or SiteSettings.load()
    data = _request("GET", site.steadfast_api_url.rstrip("/") + "/get_balance", headers=_steadfast_headers(site))
    if not isinstance(data, dict) or "current_balance" not in data:
        raise CourierError(_api_message(json.dumps(data)) or "Steadfast did not accept these keys.")
    return data["current_balance"]


# ---------------------------------------------------------------------------
# Pathao
# ---------------------------------------------------------------------------

def _pathao_url(site, path):
    return site.pathao_api_url.rstrip("/") + path


def pathao_token(site=None, *, fresh=False):
    site = site or SiteSettings.load()
    key = f"pathao-token:{site.pathao_client_id}:{site.pathao_username}"
    token = None if fresh else cache.get(key)
    if token:
        return token
    data = _request("POST", _pathao_url(site, "/aladdin/api/v1/issue-token"), payload={
        "client_id": site.pathao_client_id,
        "client_secret": site.pathao_client_secret,
        "username": site.pathao_username,
        "password": site.pathao_password,
        "grant_type": "password",
    })
    token = data.get("access_token") if isinstance(data, dict) else None
    if not token:
        raise CourierError(_api_message(json.dumps(data)) or "Pathao did not accept these login details.")
    cache.set(key, token, max(60, int(data.get("expires_in") or 3600) - 300))
    return token


def _pathao_get(site, path):
    return _request("GET", _pathao_url(site, path), headers={"Authorization": f"Bearer {pathao_token(site)}"})


def _pathao_location(order):
    district = District.objects.filter(name_en__iexact=order.city).first()
    thana = district.thanas.filter(name_en__iexact=order.thana).first() if district and order.thana else None
    if not district or not district.pathao_city_id:
        raise CourierError(
            f"No Pathao city number for district “{order.city}”. Open Delivery → District charges and run "
            "“Match Pathao cities & zones”, or type the number on the district."
        )
    if not thana or not thana.pathao_zone_id:
        raise CourierError(
            f"No Pathao zone number for thana “{order.thana or '—'}” in {order.city}. Run “Match Pathao cities & zones” "
            "or type the zone number on the thana."
        )
    return district.pathao_city_id, thana.pathao_zone_id


def _pathao_book(order, site):
    city_id, zone_id = _pathao_location(order)
    description, quantity = item_summary(order)
    data = _request("POST", _pathao_url(site, "/aladdin/api/v1/orders"),
                    headers={"Authorization": f"Bearer {pathao_token(site)}"}, payload={
        "store_id": int(site.pathao_store_id),
        "merchant_order_id": order.order_number,
        "recipient_name": order.full_name[:100],
        "recipient_phone": order.phone,
        "recipient_address": full_address(order)[:220],
        "recipient_city": city_id,
        "recipient_zone": zone_id,
        "delivery_type": 48,      # normal delivery
        "item_type": 2,           # parcel
        "special_instruction": (order.notes or "")[:200],
        "item_quantity": quantity,
        "item_weight": float(site.pathao_item_weight or Decimal("0.5")),
        "amount_to_collect": int(cod_amount(order)),
        "item_description": description,
    })
    info = data.get("data") if isinstance(data, dict) else None
    if not info or not info.get("consignment_id"):
        raise CourierError(_api_message(json.dumps(data)) or "Pathao did not accept the parcel.")
    return {
        "consignment_id": str(info["consignment_id"]),
        "tracking_code": str(info["consignment_id"]),
        "status": str(info.get("order_status") or "Pending"),
    }


def _pathao_status(order, site):
    if not order.courier_consignment_id:
        raise CourierError("This order has no Pathao consignment id yet.")
    data = _pathao_get(site, f"/aladdin/api/v1/orders/{urllib.parse.quote(order.courier_consignment_id)}/info")
    info = data.get("data") if isinstance(data, dict) else None
    status = (info or {}).get("order_status") or (info or {}).get("order_status_slug")
    if not status:
        raise CourierError(_api_message(json.dumps(data)) or "Pathao did not return a status.")
    return str(status)


# Pathao still uses older English spellings for some districts.
PATHAO_ALIASES = {
    "chattogram": "chittagong", "cumilla": "comilla", "barishal": "barisal", "jashore": "jessore",
    "bogura": "bogra", "chapai nawabganj": "chapainawabganj", "coxs bazar": "cox's bazar",
    "jhalakathi": "jhalokati", "moulvibazar": "moulvi bazar", "netrokona": "netrakona",
    "brahmanbaria": "brahmanbaria", "narsingdi": "narshingdi",
}


def _norm(name):
    name = (name or "").lower().replace("’", "'")
    name = re.sub(r"\b(sadar|city|thana|upazila|zone)\b", " ", name)
    name = re.sub(r"[^a-z0-9' ]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _rows(data):
    inner = data.get("data") if isinstance(data, dict) else None
    if isinstance(inner, dict):
        inner = inner.get("data")
    return inner if isinstance(inner, list) else []


def match_pathao_locations(site=None):
    """Fill District.pathao_city_id and Thana.pathao_zone_id by name. Returns a summary dict."""
    site = site or SiteSettings.load()
    cities = {_norm(c.get("city_name")): c.get("city_id") for c in _rows(_pathao_get(site, "/aladdin/api/v1/city-list"))}
    summary = {"districts": 0, "thanas": 0, "missing_districts": [], "missing_thanas": 0}
    for district in District.objects.filter(is_active=True).prefetch_related("thanas"):
        key = _norm(district.name_en)
        city_id = cities.get(key) or cities.get(_norm(PATHAO_ALIASES.get(key, key)))
        if not city_id:
            summary["missing_districts"].append(district.name_en)
            continue
        if district.pathao_city_id != city_id:
            district.pathao_city_id = city_id
            district.save(update_fields=["pathao_city_id"])
        summary["districts"] += 1
        zones = {_norm(z.get("zone_name")): z.get("zone_id")
                 for z in _rows(_pathao_get(site, f"/aladdin/api/v1/cities/{city_id}/zone-list"))}
        for thana in district.thanas.all():
            zone_id = zones.get(_norm(thana.name_en))
            if not zone_id and _norm(thana.name_en) in ("", _norm(district.name_en)):
                zone_id = zones.get(_norm(district.name_en))
            if zone_id:
                if thana.pathao_zone_id != zone_id:
                    thana.pathao_zone_id = zone_id
                    thana.save(update_fields=["pathao_zone_id"])
                summary["thanas"] += 1
            else:
                summary["missing_thanas"] += 1
    return summary


# ---------------------------------------------------------------------------
# Public actions
# ---------------------------------------------------------------------------

def book(order, *, site=None, notify=True):
    """Send the order to the chosen courier. Saves consignment / tracking on the order."""
    site = site or SiteSettings.load()
    ok, reason = ready(site)
    if not ok:
        raise CourierError(reason)
    if order.courier_consignment_id:
        raise CourierError(f"Already sent to {courier_label(order)} (consignment {order.courier_consignment_id}).")
    if order.status == Order.STATUS_CANCELLED:
        raise CourierError("This order is cancelled.")

    name = provider(site)
    result = _steadfast_book(order, site) if name == STEADFAST else _pathao_book(order, site)

    order.courier = name
    order.courier_consignment_id = result["consignment_id"]
    order.courier_tracking_code = result["tracking_code"]
    order.courier_status = result["status"]
    order.courier_sent_at = timezone.now()
    order.courier_checked_at = timezone.now()
    if order.status in (Order.STATUS_PENDING, Order.STATUS_PAID):
        order.status = Order.STATUS_SHIPPED
    order.save(update_fields=["courier", "courier_consignment_id", "courier_tracking_code", "courier_status",
                              "courier_sent_at", "courier_checked_at", "status", "updated_at"])
    if notify:
        notify_customer(order, site)
    return order


def refresh(order, *, site=None):
    """Ask the courier for the latest status; move the order to Delivered when it is."""
    site = site or SiteSettings.load()
    if order.courier not in (STEADFAST, PATHAO) or not (order.courier_consignment_id or order.courier == STEADFAST):
        raise CourierError("This order was not booked through a connected courier.")
    status = _steadfast_status(order, site) if order.courier == STEADFAST else _pathao_status(order, site)
    order.courier_status = status
    order.courier_checked_at = timezone.now()
    fields = ["courier_status", "courier_checked_at", "updated_at"]
    word = status.strip().lower().replace(" ", "_")
    if word in DELIVERED_WORDS and order.status != Order.STATUS_DELIVERED:
        order.status = Order.STATUS_DELIVERED
        fields.append("status")
        if order.payment_method == "cod" and order.payment_status != Order.PAYMENT_PAID and word == "delivered":
            order.payment_status = Order.PAYMENT_PAID   # the rider collected the cash
            fields.append("payment_status")
    order.save(update_fields=fields)
    return status


def notify_customer(order, site=None):
    """One SMS with the tracking code — never a second SMS to the same number on the same day."""
    site = site or SiteSettings.load()
    if not site.courier_sms_on_dispatch or not order.phone:
        return None
    from customers.models import SmsLog
    from customers.otp import _day_start as today_start
    from customers.sms import send_sms

    if SmsLog.objects.filter(phone=order.phone, created_at__gte=today_start()).exclude(status=SmsLog.STATUS_FAILED).exists():
        logger.info("Dispatch SMS skipped for %s: already sent an SMS today.", order.phone)
        return None
    text = (site.courier_dispatch_sms_text or "").format(
        order=order.order_number, courier=courier_label(order),
        tracking=order.courier_tracking_code or order.courier_consignment_id or "-",
    )
    return send_sms(order.phone, text[:300], purpose="dispatch")
