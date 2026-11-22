"""Translations for strings shown by web/static/web/js/app.js.

app.js wraps every visible string in T('...') or TF('...'). This module
finds those strings in the file itself (so the list can never drift), adds
the 64 district names (shown translated in the checkout dropdown), and
returns {english: translated} for the active language. The translations
live in locale/bn/LC_MESSAGES/django.po like every other string.
"""

import re
from functools import lru_cache
from pathlib import Path

from django.utils.translation import get_language, gettext

from .bd import BD_DISTRICTS

APP_JS = Path(__file__).resolve().parent / "static" / "web" / "js" / "app.js"

# T('...') / TF('...') with a single-quoted literal first argument.
JS_MSGID_RE = re.compile(r"\bTF?\(\s*'((?:[^'\\]|\\.)*)'")


@lru_cache(maxsize=1)
def js_msgids():
    try:
        source = APP_JS.read_text(encoding="utf-8")
    except OSError:
        source = ""
    found = {m.replace("\\'", "'") for m in JS_MSGID_RE.findall(source)}
    return tuple(sorted(found)) + tuple(BD_DISTRICTS)


def js_catalog():
    """{english: translation} for the active language ({} for English)."""
    if (get_language() or "en").startswith("en"):
        return {}
    catalog = {}
    for msgid in js_msgids():
        translated = gettext(msgid)
        if translated != msgid:
            catalog[msgid] = translated
    return catalog
