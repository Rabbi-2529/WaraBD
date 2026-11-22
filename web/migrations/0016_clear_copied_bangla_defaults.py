"""Clear Bangla (_bn) values that are only copies of the English default.

When 0014 added the _bn columns, modeltranslation gave them each field's
English default (e.g. Site Settings "1–2 working days", Product warranty
"1 Year"). A non-empty _bn stops the fallback, so Bangla pages showed that
English text. Nobody had entered Bangla yet, so any _bn equal to its _en
value or to the field's default is an artifact and is emptied here; the
page then falls back to English until real Bangla is entered.
"""

from django.db import migrations
from django.db.models import F, Q
from django.db.models.fields import NOT_PROVIDED

TEXT_FIELDS = {
    "Category": ("name", "description"),
    "Product": ("name", "subtitle", "short_description", "description_title", "description", "color", "warranty"),
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


def clear_copies(apps, schema_editor):
    for model_name, fields in TEXT_FIELDS.items():
        model = apps.get_model("web", model_name)
        for field in fields:
            bn = f"{field}_bn"
            match = Q(**{bn: F(f"{field}_en")})
            default = model._meta.get_field(bn).default
            if default is not NOT_PROVIDED and not callable(default) and default not in ("", None):
                match |= Q(**{bn: default})
            empty = None if model._meta.get_field(bn).null else ""
            model.objects.filter(match).update(**{bn: empty})


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0015_copy_existing_text_to_english"),
    ]

    operations = [
        migrations.RunPython(clear_copies, migrations.RunPython.noop),
    ]
