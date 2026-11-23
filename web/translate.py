"""English → Bangla with Google Cloud Translation (admin "Translate from English" buttons).

POST /admin/translate/  {"texts": ["...", ...], "format": "text" | "html"}
  -> {"translations": ["...", ...]}  or  {"error": "..."}

Staff only. The API key lives in Site settings → Translation (never sent to the browser).
Google's free tier covers about 500,000 characters a month.
"""

import html
import json
import logging
import urllib.error
import urllib.parse
import urllib.request

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import SiteSettings

logger = logging.getLogger(__name__)

API_URL = "https://translation.googleapis.com/language/translate/v2"
MAX_TEXTS = 100
MAX_CHARS = 30000


class TranslateError(Exception):
    """Message for the admin user."""


def translate_texts(texts, fmt="text", key=None):
    """Translate English strings to Bangla. Raises TranslateError."""
    key = (key if key is not None else SiteSettings.load().google_translate_api_key or "").strip()
    if not key:
        raise TranslateError("Add your Google Translate API key in Site settings → Translation first.")
    if not texts:
        return []
    body = json.dumps({"q": texts, "source": "en", "target": "bn",
                       "format": "html" if fmt == "html" else "text"}).encode("utf-8")
    req = urllib.request.Request(f"{API_URL}?key={urllib.parse.quote(key)}", data=body,
                                 headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", "")
        except (ValueError, AttributeError):
            message = ""
        logger.warning("Google Translate error %s: %s", exc.code, message)
        raise TranslateError(f"Google Translate refused the request ({exc.code}). {message}".strip())
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise TranslateError(f"Could not reach Google Translate: {exc}")
    out = [t.get("translatedText", "") for t in data.get("data", {}).get("translations", [])]
    if fmt != "html":
        out = [html.unescape(t) for t in out]
    return out


@staff_member_required
@require_POST
def translate_view(request):
    try:
        payload = json.loads(request.body or b"{}")
    except ValueError:
        return JsonResponse({"error": "Bad request."}, status=400)
    texts = payload.get("texts")
    if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
        return JsonResponse({"error": "Bad request."}, status=400)
    if len(texts) > MAX_TEXTS or sum(len(t) for t in texts) > MAX_CHARS:
        return JsonResponse({"error": "Too much text at once. Translate one box at a time."}, status=400)
    try:
        return JsonResponse({"translations": translate_texts(texts, payload.get("format", "text"))})
    except TranslateError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
