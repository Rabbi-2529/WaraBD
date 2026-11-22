"""Collect every translatable string into locale/<lang>/LC_MESSAGES/django.po.

    python manage.py i18n_sync            # update locale/bn/LC_MESSAGES/django.po
    python manage.py i18n_sync --missing  # also list strings still untranslated

Works without GNU gettext (Django's makemessages needs it; Windows rarely
has it). Sources:
  * storefront templates (web/templates/web/**.html): {% translate %},
    {% blocktranslate trimmed %} and _("...") inside tags
  * Python in web/: _(), gettext(), gettext_lazy(), _lazy()
  * app.js strings wrapped in T('...') / TF('...') plus district names
Existing translations are kept; strings no longer used are marked obsolete.
Then run `python manage.py i18n_compile`.
"""

import ast
import re
from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.translation import trim_whitespace

from web.i18n_js import js_msgids

WEB_DIR = Path(__file__).resolve().parents[2]

TRANS_RE = re.compile(r"""\{%\s*(?:trans|translate)\s+(["'])(.*?)\1[^%]*%\}""")
LITERAL_RE = re.compile(r"""(?<![\w.])_\((["'])(.*?)\1\)""")
BLOCK_RE = re.compile(
    r"\{%\s*(?:blocktrans|blocktranslate)\b(.*?)%\}(.*?)\{%\s*(?:endblocktrans|endblocktranslate)\s*%\}",
    re.DOTALL,
)
VAR_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")
PY_RE = re.compile(r"""\b(?:_|gettext|gettext_lazy|_lazy)\(\s*((["'])(?:\\.|(?!\2).)*\2)\s*[,)]""")
# ngettext("one", "many", n) -> plural entry
PLURAL_RE = re.compile(
    r"""\bngettext(?:_lazy)?\(\s*((["'])(?:\\.|(?!\2).)*\2)\s*,\s*((["'])(?:\\.|(?!\4).)*\4)""",
    re.DOTALL,
)

# Apps whose templates and Python code the storefront shows to customers.
APP_DIRS = [WEB_DIR, WEB_DIR.parent / "customers"]


def _block_msgid(options, body):
    """Build the msgid exactly like Django's {% blocktranslate %} does."""
    if "trimmed" in options.split():
        body = trim_whitespace(body)
    out, pos = [], 0
    for match in VAR_RE.finditer(body):
        out.append(body[pos:match.start()].replace("%", "%%"))
        out.append(f"%({match.group(1)})s")
        pos = match.end()
    out.append(body[pos:].replace("%", "%%"))
    return "".join(out)


def template_msgids(path):
    text = path.read_text(encoding="utf-8")
    found = [m.group(2) for m in TRANS_RE.finditer(text)]
    found += [m.group(2) for m in LITERAL_RE.finditer(text)]
    found += [_block_msgid(m.group(1), m.group(2)) for m in BLOCK_RE.finditer(text)]
    return found


def python_msgids(path):
    found = []
    for match in PY_RE.finditer(path.read_text(encoding="utf-8")):
        try:
            found.append(ast.literal_eval(match.group(1)))
        except (ValueError, SyntaxError):
            continue
    return found


def python_plurals(path):
    """[(singular, plural)] from ngettext(...) calls."""
    found = []
    for match in PLURAL_RE.finditer(path.read_text(encoding="utf-8")):
        try:
            found.append((ast.literal_eval(match.group(1)), ast.literal_eval(match.group(3))))
        except (ValueError, SyntaxError):
            continue
    return found


def collect(plurals=None):
    """{msgid: [source, ...]} for every string the storefront can show.

    Pass a dict as `plurals` to also receive {singular: plural} from ngettext().
    """
    sources = {}
    root = WEB_DIR.parent

    def add(msgid, where):
        if msgid and msgid.strip():
            sources.setdefault(msgid, [])
            if where not in sources[msgid]:
                sources[msgid].append(where)

    for app_dir in APP_DIRS:
        for path in sorted((app_dir / "templates").rglob("*.html")):
            for msgid in template_msgids(path):
                add(msgid, path.relative_to(root).as_posix())
        for path in sorted(app_dir.glob("*.py")):
            where = path.relative_to(root).as_posix()
            for msgid in python_msgids(path):
                add(msgid, where)
            for singular, plural in python_plurals(path):
                add(singular, where)
                if plurals is not None:
                    plurals[singular] = plural
    for msgid in js_msgids():
        add(msgid, "web/static/web/js/app.js")
    return sources


class Command(BaseCommand):
    help = "Collect translatable strings into locale/<lang>/LC_MESSAGES/django.po (no GNU gettext needed)."

    def add_arguments(self, parser):
        parser.add_argument("--lang", default="bn")
        parser.add_argument("--missing", action="store_true", help="List untranslated strings.")

    def handle(self, *args, lang, missing, **options):
        po_path = Path(settings.LOCALE_PATHS[0]) / lang / "LC_MESSAGES" / "django.po"
        po_path.parent.mkdir(parents=True, exist_ok=True)
        if po_path.exists():
            po = polib.pofile(str(po_path), wrapwidth=0)
        else:
            po = polib.POFile(wrapwidth=0)
            po.metadata = {
                "Project-Id-Version": "WaRa BD",
                "Language": lang,
                "MIME-Version": "1.0",
                "Content-Type": "text/plain; charset=UTF-8",
                "Content-Transfer-Encoding": "8bit",
                "Plural-Forms": "nplurals=2; plural=(n != 1);",
            }

        plurals = {}
        sources = collect(plurals)
        existing = {e.msgid: e for e in po}
        added = 0
        for msgid, where in sources.items():
            entry = existing.get(msgid)
            if entry is None:
                if msgid in plurals:
                    entry = polib.POEntry(msgid=msgid, msgid_plural=plurals[msgid], msgstr_plural={0: "", 1: ""})
                else:
                    entry = polib.POEntry(msgid=msgid, msgstr="")
                po.append(entry)
                added += 1
            entry.obsolete = False
            entry.occurrences = [(w, "") for w in where]
        obsolete = 0
        for msgid, entry in existing.items():
            if msgid in sources:
                continue
            if not entry.translated():
                po.remove(entry)  # never translated: nothing worth keeping
            elif not entry.obsolete:
                entry.obsolete = True  # keep the translation in case it comes back
                obsolete += 1

        po.sort(key=lambda e: (e.obsolete, e.occurrences[0][0] if e.occurrences else "", e.msgid))
        po.save(str(po_path))

        active = [e for e in po if not e.obsolete]
        untranslated = [e for e in active if not e.translated()]
        self.stdout.write(
            f"{po_path}: {len(active)} strings, {len(active) - len(untranslated)} translated, "
            f"{len(untranslated)} missing (+{added} new, {obsolete} now obsolete)"
        )
        if missing:
            for entry in untranslated:
                self.stdout.write(f"  - {entry.msgid}")
