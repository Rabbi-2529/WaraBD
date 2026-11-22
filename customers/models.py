"""Shop customers (phone + SMS code login), their addresses, OTP codes and SMS log.

Customers are separate from staff accounts (users.User, email + password,
used for /admin/). A customer has no password: they log in with their
Bangladeshi mobile number and a one-time SMS code.
"""

import hashlib
import hmac
import secrets

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from web.bd import BD_DISTRICTS


class Customer(models.Model):
    phone = models.CharField(_("Mobile number"), max_length=11, unique=True, help_text="01XXXXXXXXX")
    name = models.CharField(_("Name"), max_length=150)
    email = models.EmailField(_("Email"), blank=True)
    is_active = models.BooleanField(default=True, help_text="Untick to block this customer from logging in.")
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.phone})"

    @property
    def default_address(self):
        return self.addresses.order_by("-is_default", "-updated_at").first()


DISTRICT_CHOICES = [(d, d) for d in BD_DISTRICTS]


class CustomerAddress(models.Model):
    """Bangladesh address: district → thana / upazila → house, road, area."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(_("Label"), max_length=40, blank=True, help_text=_("e.g. Home, Office"))
    name = models.CharField(_("Receiver's name"), max_length=150)
    phone = models.CharField(_("Receiver's mobile"), max_length=11)
    district = models.CharField(_("District"), max_length=40, choices=DISTRICT_CHOICES)
    thana = models.CharField(_("Thana / Upazila"), max_length=80, blank=True)
    address = models.CharField(_("House, road, area"), max_length=255)
    is_default = models.BooleanField(_("Default address"), default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "-updated_at"]
        verbose_name_plural = "customer addresses"

    def __str__(self):
        return f"{self.label or self.name}: {self.one_line}"

    @property
    def one_line(self):
        parts = [self.address, self.thana, self.district]
        return ", ".join(p for p in parts if p)


class OtpCode(models.Model):
    """One SMS code. Only a salted HMAC of the code is stored."""

    PURPOSE_LOGIN = "login"
    PURPOSE_REGISTER = "register"
    PURPOSE_CHECKOUT = "checkout"
    PURPOSE_CHANGE_PHONE = "change_phone"
    PURPOSE_CHOICES = [
        (PURPOSE_LOGIN, "Login"),
        (PURPOSE_REGISTER, "Registration"),
        (PURPOSE_CHECKOUT, "Order"),
        (PURPOSE_CHANGE_PHONE, "Change mobile number"),
    ]

    phone = models.CharField(max_length=11, db_index=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    salt = models.CharField(max_length=32, editable=False)
    code_hash = models.CharField(max_length=64, editable=False)
    payload = models.JSONField(default=dict, blank=True, help_text="Form data to finish after verification.")
    attempts = models.PositiveSmallIntegerField(default=0)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    cancelled = models.BooleanField(default=False, help_text="Customer chose 'Change number'.")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "OTP code"

    def __str__(self):
        return f"{self.get_purpose_display()} code for {self.phone}"

    @staticmethod
    def _digest(salt, code):
        key = settings.SECRET_KEY.encode()
        return hmac.new(key, f"{salt}:{code}".encode(), hashlib.sha256).hexdigest()

    def set_code(self, code):
        self.salt = secrets.token_hex(16)
        self.code_hash = self._digest(self.salt, code)

    def matches(self, code):
        return hmac.compare_digest(self.code_hash, self._digest(self.salt, str(code)))

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_open(self):
        return not self.verified_at and not self.cancelled and not self.is_expired


class SmsLog(models.Model):
    """Every SMS the shop sends (or refuses to send). Daily limits count these rows."""

    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_TEST = "test"
    STATUS_CHOICES = [
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
        (STATUS_TEST, "Test mode (not sent)"),
    ]

    phone = models.CharField(max_length=11, db_index=True)
    purpose = models.CharField(max_length=20, blank=True)
    message = models.CharField(max_length=320, help_text="Codes are hidden (******).")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES)
    response = models.TextField(blank=True, help_text="What the SMS gateway answered.")
    ip = models.GenericIPAddressField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "SMS log entry"
        verbose_name_plural = "SMS log"

    def __str__(self):
        return f"{self.phone} · {self.get_status_display()} · {self.created_at:%d %b %Y %H:%M}"
