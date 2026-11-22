from django.db import migrations

PAGES = ["home", "product_list", "portfolio", "about", "contact"]


def create_rows(apps, schema_editor):
    PageSeo = apps.get_model("web", "PageSeo")
    for key in PAGES:
        PageSeo.objects.get_or_create(page=key)


class Migration(migrations.Migration):
    dependencies = [("web", "0022_seo_fields_and_page_seo")]
    operations = [migrations.RunPython(create_rows, migrations.RunPython.noop)]
