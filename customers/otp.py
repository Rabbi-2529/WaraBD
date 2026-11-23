"""SMS one-time codes for login, registration, orders and number changes.

Rules (all editable in admin → Site Settings → "Phone login / OTP"):
  * 6-digit code, valid `otp_valid_minutes`, at most `otp_max_attempts` wrong tries
  * "Resend code" only after `otp_resend_seconds`
  * at most `sms_daily_limit_per_number` SMS per number and
    `sms_daily_limit_per_ip` per internet connection per day (Dhaka time)
  * guests get a new code for every order (logged-in customers never need one);
    a number verified in this browser today may fill in its last address at
    checkout (see customers.auth.phone_verified_today)
Failed SMS do not count toward the limits.
"""

import re
import secrets
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext as _
from django.utils.translation import ngettext

from web.models import SiteSettings

from .auth import remember_verified_phone
from .models import OtpCode, SmsLog
from .sms import gateway_ready, send_sms

PENDING_KEY = "otp_pending_id"
TEST_CODE_KEY = "otp_test_code"
_COUNTED = (SmsLog.STATUS_SENT, SmsLog.STATUS_TEST)
_BN_TO_ASCII = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")
DEFAULT_SMS_TEXT = "{code} is your WaRa BD verification code. It expires in {minutes} minutes. Do not share it."


class OtpError(Exception):
    """A message to show the customer (already translated)."""


def sms_mode(site=None):
    """"live" = real SMS, "test" = not sent but flow works (DEBUG only), "off" = unavailable."""
    if gateway_ready(site):
        return "live"
    return "test" if settings.DEBUG else "off"


def client_ip(request):
    return request.META.get("REMOTE_ADDR") or None


def _day_start():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def seconds_until_resend(phone, site=None):
    site = site or SiteSettings.load()
    last = SmsLog.objects.filter(phone=phone, status__in=_COUNTED).order_by("-created_at").first()
    if not last:
        return 0
    elapsed = (timezone.now() - last.created_at).total_seconds()
    return max(0, int(site.otp_resend_seconds - elapsed + 0.999))


def _sms_text(site, code):
    try:
        return site.otp_sms_text.format(code=code, minutes=site.otp_valid_minutes)
    except (KeyError, IndexError, ValueError):
        return DEFAULT_SMS_TEXT.format(code=code, minutes=site.otp_valid_minutes)


def request_otp(request, *, phone, purpose, payload=None):
    """Create a code, send it by SMS and remember it in the session. Raises OtpError."""
    site = SiteSettings.load()
    if sms_mode(site) == "off":
        raise OtpError(_("SMS codes are not available right now. Please call us and we will help you."))

    wait = seconds_until_resend(phone, site)
    if wait:
        raise OtpError(ngettext(
            "Please wait %(n)s second before asking for a new code.",
            "Please wait %(n)s seconds before asking for a new code.",
            wait,
        ) % {"n": wait})

    today = SmsLog.objects.filter(created_at__gte=_day_start(), status__in=_COUNTED)
    if today.filter(phone=phone).count() >= site.sms_daily_limit_per_number:
        raise OtpError(_("This number has reached today's SMS limit. Please try again tomorrow or call us."))
    ip = client_ip(request)
    if ip and today.filter(ip=ip).count() >= site.sms_daily_limit_per_ip:
        raise OtpError(_("Too many SMS codes were requested from this connection today. Please try again tomorrow or call us."))

    # Only one open code per number and purpose.
    OtpCode.objects.filter(phone=phone, purpose=purpose, verified_at__isnull=True, cancelled=False).update(cancelled=True)

    code = f"{secrets.randbelow(10 ** 6):06d}"
    otp = OtpCode(phone=phone, purpose=purpose, payload=payload or {}, ip=ip,
                  expires_at=timezone.now() + timedelta(minutes=site.otp_valid_minutes))
    otp.set_code(code)
    otp.save()

    text = _sms_text(site, code)
    log = send_sms(phone, text, purpose=purpose, ip=ip, log_message=text.replace(code, "******"))
    if log.status == SmsLog.STATUS_FAILED:
        otp.cancelled = True
        otp.save(update_fields=["cancelled"])
        raise OtpError(_("We couldn't send the SMS. Please try again in a minute or call us."))

    request.session[PENDING_KEY] = otp.pk
    if log.status == SmsLog.STATUS_TEST:
        request.session[TEST_CODE_KEY] = code  # shown on the OTP page (DEBUG test mode only)
    else:
        request.session.pop(TEST_CODE_KEY, None)
    return otp


def pending_otp(request):
    otp_id = request.session.get(PENDING_KEY)
    if not otp_id:
        return None
    return OtpCode.objects.filter(pk=otp_id, verified_at__isnull=True, cancelled=False).first()


def clear_pending(request):
    request.session.pop(PENDING_KEY, None)
    request.session.pop(TEST_CODE_KEY, None)


def verify_otp(request, otp, code):
    """Check `code` for `otp`. Returns the verified OtpCode or raises OtpError."""
    site = SiteSettings.load()
    code = re.sub(r"\s", "", str(code or "")).translate(_BN_TO_ASCII)

    if otp.verified_at or otp.cancelled:
        raise OtpError(_("This code is no longer valid. Please request a new one."))
    if otp.is_expired:
        raise OtpError(_("This code has expired. Tap “Resend code” to get a new one."))
    if otp.attempts >= site.otp_max_attempts:
        raise OtpError(_("Too many wrong codes. Tap “Resend code” to get a new one."))

    if not re.fullmatch(r"\d{6}", code) or not otp.matches(code):
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        left = site.otp_max_attempts - otp.attempts
        if left <= 0:
            raise OtpError(_("Too many wrong codes. Tap “Resend code” to get a new one."))
        raise OtpError(ngettext(
            "Wrong code. %(n)s try left.",
            "Wrong code. %(n)s tries left.",
            left,
        ) % {"n": left})

    # Mark it used in one step, so the same code sent twice at once (double tap)
    # can never place two orders: only the first one gets through.
    now = timezone.now()
    used = OtpCode.objects.filter(pk=otp.pk, verified_at__isnull=True, cancelled=False).update(verified_at=now)
    if not used:
        raise OtpError(_("This code is no longer valid. Please request a new one."))
    otp.verified_at = now
    remember_verified_phone(request, otp.phone)
    clear_pending(request)
    return otp


def otp_needed_for_order(request, phone):
    """Guests confirm their number with a new SMS code for every order, even the
    same number again the same day (Site Settings → OTP for orders)."""
    site = SiteSettings.load()
    if not site.otp_for_orders or sms_mode(site) == "off":
        return False
    return not getattr(request, "customer", None)  # logged in = number already verified
