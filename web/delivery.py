"""Delivery charge by district / thana (admin → Delivery → District charges / Thana).

The customer never chooses the charge: it follows the district they pick,
or the thana when that thana has its own charge. The server always works
it out again from the database — the browser's number is only a preview.
"""

from decimal import Decimal

from django.db.models import Prefetch
from django.utils.translation import gettext as _

from .models import District, Order, Thana


class DeliveryError(ValueError):
    """Message for the customer (translated)."""


def delivery_quote(district_name, thana_name=""):
    district = District.objects.filter(name_en__iexact=str(district_name or "").strip(), is_active=True).first()
    if district is None:
        raise DeliveryError(_("We do not deliver to this district yet. Please call us."))
    thana = None
    if thana_name:
        thana = district.thanas.filter(name_en__iexact=str(thana_name).strip(), is_active=True).first()
    fee = thana.effective_fee if thana else district.delivery_fee
    return {
        "fee": Decimal(fee),
        "eta": district.delivery_eta,
        "zone": Order.ZONE_INSIDE if district.name_en == "Dhaka" else Order.ZONE_OUTSIDE,
        "district": district,
        "thana": thana,
    }


def locations_payload():
    """Districts + thanas + charges for the checkout / address dropdowns (current language)."""
    districts = District.objects.filter(is_active=True).prefetch_related(
        Prefetch("thanas", queryset=Thana.objects.filter(is_active=True).order_by("name_en"))
    ).order_by("name_en")
    return [
        {
            "v": d.name_en,
            "l": d.name,
            "f": d.delivery_fee,
            "e": d.delivery_eta or "",
            "t": [[t.name_en, t.name, t.delivery_fee] for t in d.thanas.all()],
        }
        for d in districts
    ]
