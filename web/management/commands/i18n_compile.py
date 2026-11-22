"""Compile locale/*/LC_MESSAGES/django.po into django.mo without GNU gettext.

    python manage.py i18n_compile

Same result as Django's `compilemessages` (which needs GNU gettext's
msgfmt). Fuzzy and untranslated entries are skipped, so those strings
simply stay in English.
"""

from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Compile django.po files to django.mo (no GNU gettext needed)."

    def handle(self, *args, **options):
        compiled = 0
        codes = [code for code, _name in settings.LANGUAGES]
        for locale_dir in settings.LOCALE_PATHS:
            for code in codes:
                po_path = Path(locale_dir) / code / "LC_MESSAGES" / "django.po"
                if not po_path.exists():
                    continue
                po = polib.pofile(str(po_path))
                po.save_as_mofile(str(po_path.with_suffix(".mo")))
                compiled += 1
                self.stdout.write(f"{po_path.with_suffix('.mo')}: {len(po.translated_entries())} strings")
        if not compiled:
            self.stdout.write("No .po files found.")
