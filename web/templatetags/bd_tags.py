"""Bangladesh display helpers for templates: {% load bd_tags %}.

    {{ amount|taka }}     2035 -> ৳2,035   (৳২,০৩৫ on Bangla pages)
    {{ value|digits }}    "01958-666999" -> "০১৯৫৮-৬৬৬৯৯৯" on Bangla pages
    {{ phone|tel_href }}  "+880 1958-666999" -> "+8801958666999" (for tel: links)
"""

import re

from django import template
from django.utils.translation import get_language

from web.bd import format_taka

register = template.Library()

_BN_DIGITS = str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯")


def _is_bangla():
    return (get_language() or "").startswith("bn")


@register.filter
def digits(value):
    """Show 0-9 as Bangla digits on Bangla pages; unchanged in English."""
    if value is None:
        return ""
    return str(value).translate(_BN_DIGITS) if _is_bangla() else value


@register.filter
def taka(value):
    """2035 -> ৳2,035 ; 150000 -> ৳1,50,000 (Bangla digits on Bangla pages)."""
    try:
        text = format_taka(value)
    except (TypeError, ValueError, ArithmeticError):
        return value
    return digits(text)


@register.filter
def tel_href(value):
    """Digits and a leading + only, for href="tel:..."."""
    return re.sub(r"[^\d+]", "", str(value or ""))
