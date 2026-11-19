"""Bangladesh display helpers for templates: {% load bd_tags %} then {{ amount|taka }}."""

from django import template

from web.bd import format_taka

register = template.Library()


@register.filter
def taka(value):
    """2035 -> ৳2,035 ; 150000 -> ৳1,50,000"""
    try:
        return format_taka(value)
    except (TypeError, ValueError, ArithmeticError):
        return value
