"""Create the editable storefront content rows (safe to run any time).

    python manage.py sync_content            # add whatever is missing
    python manage.py sync_content --reset-text   # put page text back to the built-in wording

* Page text: every {% cms "key" %}…{% endcms %} tag in the storefront
  templates becomes a ContentBlock row, pre-filled with the built-in text
  in English and Bangla (taken from the template + locale/bn translations).
* Page lists and policy pages: defaults from web/content_defaults.py, only
  for groups / slugs that have nothing yet.
Existing rows are never changed (except with --reset-text).
"""

import html
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.template import Context, engines
from django.utils import translation

from web.content_defaults import ITEMS, PAGES
from web.models import ContentBlock, ContentItem, Page
from web.templatetags.cms_tags import CmsNode

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
PAGE_FOR_PREFIX = {"checkout": "cart"}


def _render(template, node, lang):
    context = Context(autoescape=True)
    with translation.override(lang), context.bind_template(template):
        text = node.nodelist.render(context).strip()
    return text if node.allow_html else html.unescape(text)


def template_blocks():
    """{key: (page, allow_html, english, bangla)} from all storefront templates."""
    engine = engines["django"]
    found = {}
    for path in sorted((TEMPLATE_DIR / "web").rglob("*.html")):
        name = path.relative_to(TEMPLATE_DIR).as_posix()
        template = engine.get_template(name).template
        for node in template.nodelist.get_nodes_by_type(CmsNode):
            prefix = node.key.split(".", 1)[0]
            page = PAGE_FOR_PREFIX.get(prefix, prefix)
            found[node.key] = (
                page, node.allow_html, _render(template, node, "en"), _render(template, node, "bn"),
            )
    return found


def _label(key):
    return key.split(".", 1)[-1].replace(".", " · ").replace("_", " ").capitalize()


class Command(BaseCommand):
    help = "Create missing page text, page list and policy page rows (never overwrites edits)."

    def add_arguments(self, parser):
        parser.add_argument("--reset-text", action="store_true",
                            help="Overwrite page text with the built-in English and Bangla wording.")

    def handle(self, *args, reset_text=False, **options):
        with translation.override("en"), transaction.atomic():
            self._blocks(reset_text)
            self._items()
            self._pages()

    def _blocks(self, reset):
        added = updated = 0
        valid_pages = dict(ContentBlock.PAGE_CHOICES)
        for key, (page, allow_html, english, bangla) in template_blocks().items():
            values = {
                "page": page if page in valid_pages else "home",
                "allow_html": allow_html,
                "value_en": english,
                "value_bn": bangla if bangla != english else "",
            }
            block = ContentBlock.objects.filter(key=key).first()
            if block is None:
                ContentBlock.objects.create(key=key, label=_label(key), **values)
                added += 1
            elif reset:
                for field, value in values.items():
                    setattr(block, field, value)
                block.save()
                updated += 1
        self.stdout.write(f"  page text: {added} added" + (f", {updated} reset" if reset else ""))

    def _items(self):
        added = 0
        for group, rows in ITEMS.items():
            if ContentItem.objects.filter(group=group).exists():
                continue
            for order, (icon, value_en, value_bn, title_en, title_bn, text_en, text_bn) in enumerate(rows, 1):
                ContentItem.objects.create(
                    group=group, icon=icon, order=order,
                    value_en=value_en, value_bn=value_bn if value_bn != value_en else "",
                    title_en=title_en, title_bn=title_bn if title_bn != title_en else "",
                    text_en=text_en, text_bn=text_bn if text_bn != text_en else "",
                )
                added += 1
        self.stdout.write(f"  page list items: {added} added")

    def _pages(self):
        added = 0
        for data in PAGES:
            if Page.objects.filter(slug=data["slug"]).exists():
                continue
            Page.objects.create(**data)
            added += 1
        self.stdout.write(f"  policy pages: {added} added")
