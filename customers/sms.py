"""Send SMS through the gateway configured in the admin (Site Settings → SMS gateway).

Default gateway: IGL Web SMS
    http://sms.iglweb.com/api/v1/send?api_key=…&contacts=…&senderid=…&msg=…
The four values go in the URL exactly like that: the gateway does not read a
POST body (it answers {"code":"445010","message":"Missing api key"}).

While "Send real SMS" is off, or the API key / sender ID are empty, nothing
is sent: the SMS is logged with status "test" so the whole flow can be
tried without spending SMS credit.
"""

import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from web.bd import normalize_bd_phone
from web.models import SiteSettings

from .models import SmsLog

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15
_FAIL_WORDS = {"error", "failed", "failure", "false", "invalid"}
# Gateway answers such as {"code":"445010","message":"Missing api key"}: only a
# message that says the SMS went out counts as sent.
_OK_MESSAGE = re.compile(r"success|submitted|sent|queued|accepted|delivered", re.I)
_BAD_MESSAGE = re.compile(r"missing|invalid|error|fail|insufficient|denied|expired|blocked|wrong|not ", re.I)


def gateway_ready(site=None):
    site = site or SiteSettings.load()
    return bool(site.sms_enabled and site.sms_api_url and site.sms_api_key and site.sms_sender_id)


def _number(phone, site):
    local = normalize_bd_phone(phone)
    return local if site.sms_number_format == "0" else "88" + local


def _looks_failed(body):
    """The gateway answered 2xx; check the body for an error report."""
    try:
        data = json.loads(body)
    except (TypeError, ValueError):
        return bool(re.search(r"\b(error|invalid|failed)\b", body or "", re.I))
    if isinstance(data, dict):
        if data.get("error") or data.get("errors"):
            return True
        for key in ("status", "success", "result"):
            if str(data.get(key, "")).strip().lower() in _FAIL_WORDS:
                return True
        message = str(data.get("message") or data.get("msg") or "")
        if message and _BAD_MESSAGE.search(message):
            return True
        if "code" in data and not _OK_MESSAGE.search(message):
            return True
    return False


def send_sms(phone, message, *, purpose="", ip=None, log_message=None):
    """Send one SMS and record it in SmsLog. Returns the SmsLog row.

    `log_message` is what gets stored (e.g. with the code hidden).
    """
    site = SiteSettings.load()
    stored = (log_message or message)[:320]

    if not gateway_ready(site):
        logger.warning("SMS test mode (not sent) to %s: %s", phone, message)
        return SmsLog.objects.create(phone=phone, purpose=purpose, message=stored,
                                     status=SmsLog.STATUS_TEST, ip=ip,
                                     response="Test mode — SMS gateway is switched off in Site Settings.")

    query = urllib.parse.urlencode({
        "api_key": site.sms_api_key.strip(),
        "contacts": _number(phone, site),
        "senderid": site.sms_sender_id.strip(),
        "msg": message,
    })
    base = site.sms_api_url.strip()
    url = base + ("&" if "?" in base else "?") + query
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:
            body = resp.read(2000).decode("utf-8", "replace")
            ok = 200 <= resp.status < 300 and not _looks_failed(body)
    except urllib.error.HTTPError as exc:
        body, ok = f"HTTP {exc.code}: {exc.read(500).decode('utf-8', 'replace')}", False
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        body, ok = f"Could not reach the SMS gateway: {exc}", False

    if not ok:
        logger.error("SMS to %s failed: %s", phone, body)
    return SmsLog.objects.create(phone=phone, purpose=purpose, message=stored,
                                 status=SmsLog.STATUS_SENT if ok else SmsLog.STATUS_FAILED,
                                 response=body[:2000], ip=ip)
