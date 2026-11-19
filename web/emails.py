# web/emails.py
"""Order-related email notifications."""
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .bd import format_taka


def send_order_confirmation(order):
    """Send HTML + plaintext confirmation to the customer."""
    subject = f"Order confirmation — {order.order_number}"

    context = {"order": order, "site_url": getattr(settings, "SITE_URL", "http://localhost:8000")}
    html_body = render_to_string("web/emails/order_confirmation.html", context)
    text_body = strip_tags(html_body)

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[order.email],
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)


def send_admin_new_order(order):
    """Notify admin staff of a new order."""
    subject = f"[New Order] {order.order_number} — {format_taka(order.total)}"

    context = {"order": order, "site_url": getattr(settings, "SITE_URL", "http://localhost:8000")}
    html_body = render_to_string("web/emails/admin_new_order.html", context)
    text_body = strip_tags(html_body)

    recipients = getattr(settings, "ADMIN_ORDER_EMAILS", None)
    if not recipients:
        # fall back to MANAGERS setting (cookiecutter defines it)
        recipients = [email for _, email in getattr(settings, "MANAGERS", [])]
    if not recipients:
        return  # no configured recipient → skip silently

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=True)  # admin notification should never crash checkout