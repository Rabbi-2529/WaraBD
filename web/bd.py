"""Bangladesh formats: mobile numbers, districts and money.

Every place that accepts a phone number or district (checkout, contact,
and later login/OTP and courier) must go through these helpers, so the
database only ever holds one format.
"""

import re
from decimal import Decimal

from django.utils.translation import gettext_lazy as _lazy

_ASCII_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


# Mobile numbers: 11 digits, starting 013–019 (GP, Banglalink, Robi,
# Airtel, Teletalk). Accepts +880 / 880 / 0 prefixes, spaces and dashes.
_BD_MOBILE_RE = re.compile(r"^(?:\+?88)?(01[3-9]\d{8})$")

PHONE_ERROR = _lazy("Enter a valid Bangladeshi mobile number (01XXXXXXXXX).")


def normalize_bd_phone(value):
    """Return the number as 01XXXXXXXXX, or raise ValueError."""
    raw = re.sub(r"[\s\-().]", "", str(value or "").translate(_ASCII_DIGITS))
    match = _BD_MOBILE_RE.match(raw)
    if not match:
        raise ValueError(str(PHONE_ERROR))
    return match.group(1)


def is_bd_phone(value):
    try:
        normalize_bd_phone(value)
    except ValueError:
        return False
    return True


def bd_phone_international(value):
    """01XXXXXXXXX -> 8801XXXXXXXXX (the format SMS gateways expect)."""
    return "88" + normalize_bd_phone(value)


# All 64 districts, in the spelling the storefront dropdown uses.
BD_DISTRICTS = (
    "Bagerhat", "Bandarban", "Barguna", "Barishal", "Bhola", "Bogura",
    "Brahmanbaria", "Chandpur", "Chapai Nawabganj", "Chattogram", "Chuadanga",
    "Cox's Bazar", "Cumilla", "Dhaka", "Dinajpur", "Faridpur", "Feni",
    "Gaibandha", "Gazipur", "Gopalganj", "Habiganj", "Jamalpur", "Jashore",
    "Jhalokathi", "Jhenaidah", "Joypurhat", "Khagrachhari", "Khulna",
    "Kishoreganj", "Kurigram", "Kushtia", "Lakshmipur", "Lalmonirhat",
    "Madaripur", "Magura", "Manikganj", "Meherpur", "Moulvibazar",
    "Munshiganj", "Mymensingh", "Naogaon", "Narail", "Narayanganj",
    "Narsingdi", "Natore", "Netrokona", "Nilphamari", "Noakhali", "Pabna",
    "Panchagarh", "Patuakhali", "Pirojpur", "Rajbari", "Rajshahi",
    "Rangamati", "Rangpur", "Satkhira", "Shariatpur", "Sherpur",
    "Sirajganj", "Sunamganj", "Sylhet", "Tangail", "Thakurgaon",
)

_DISTRICT_LOOKUP = {d.casefold(): d for d in BD_DISTRICTS}

DISTRICT_ERROR = _lazy("Please select your district.")


def clean_bd_district(value):
    """Return the canonical district name, or raise ValueError."""
    district = _DISTRICT_LOOKUP.get(str(value or "").strip().casefold())
    if not district:
        raise ValueError(str(DISTRICT_ERROR))
    return district


def format_taka(amount):
    """1975 -> '৳1,975'; 150000 -> '৳1,50,000' (Bangladeshi lakh grouping)."""
    value = Decimal(str(amount or 0)).quantize(Decimal("1"))
    sign = "-" if value < 0 else ""
    digits = str(abs(int(value)))
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups) + "," + tail
    return f"{sign}৳{digits}"
