"""Copy every existing value into its new English (_en) column.

0014 added empty <field>_en / <field>_bn columns. Without this step the
site would read the empty English columns and lose all current text.
Bangla columns stay empty (pages fall back to English until filled in).
"""

from django.db import migrations
from django.db.models import F

TRANSLATED = {
    "Category": ("name", "description"),
    "Product": (
        "name", "subtitle", "short_description", "description_title",
        "description", "color", "warranty", "highlights", "specs",
        "features", "applications", "steps", "faq",
    ),
    "ProductImage": ("caption",),
    "PortfolioProject": ("title", "short_description", "description"),
    "SiteSettings": (
        "name", "address", "hours", "announcement", "delivery_inside_eta",
        "delivery_outside_eta", "meta_title", "meta_description",
    ),
    "SiteHighlight": ("title", "subtitle"),
    "SiteFeature": ("title", "text", "badge", "best_for"),
    "UseCase": ("title", "place", "text"),
    "TimelineStep": ("title", "text"),
}


def copy_to_english(apps, schema_editor):
    # The _en columns were created empty by 0014 (JSON ones as [] / {}),
    # so copying every row unconditionally is safe and complete.
    for model_name, fields in TRANSLATED.items():
        model = apps.get_model("web", model_name)
        model.objects.update(**{f"{field}_en": F(field) for field in fields})


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0014_english_bangla_fields"),
    ]

    operations = [
        migrations.RunPython(copy_to_english, migrations.RunPython.noop),
    ]
