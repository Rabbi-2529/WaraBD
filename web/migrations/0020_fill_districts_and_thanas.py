"""Fill the 64 districts and their thanas / upazilas.

Starting charges come from Site Settings: Dhaka district uses the
"inside Dhaka" fee and time, every other district the "outside Dhaka" one.
Change them later in the admin (Website Content → Delivery charges).
Runs only on an empty District table.
"""

from django.db import migrations


def fill(apps, schema_editor):
    from web.bd_locations import expanded

    District = apps.get_model("web", "District")
    Thana = apps.get_model("web", "Thana")
    SiteSettings = apps.get_model("web", "SiteSettings")
    if District.objects.exists():
        return

    site = SiteSettings.objects.filter(pk=1).first()
    inside_fee = getattr(site, "delivery_inside_fee", 60) or 60
    outside_fee = getattr(site, "delivery_outside_fee", 120) or 120
    inside_eta_en = getattr(site, "delivery_inside_eta_en", None) or "1–2 working days"
    outside_eta_en = getattr(site, "delivery_outside_eta_en", None) or "2–4 working days"
    inside_eta_bn = getattr(site, "delivery_inside_eta_bn", None) or "১–২ কার্যদিবস"
    outside_eta_bn = getattr(site, "delivery_outside_eta_bn", None) or "২–৪ কার্যদিবস"

    for d_en, d_bn, division, thanas in expanded():
        inside = d_en == "Dhaka"
        district = District.objects.create(
            name=d_en, name_en=d_en, name_bn=d_bn, division=division,
            delivery_fee=inside_fee if inside else outside_fee,
            delivery_eta=inside_eta_en if inside else outside_eta_en,
            delivery_eta_en=inside_eta_en if inside else outside_eta_en,
            delivery_eta_bn=inside_eta_bn if inside else outside_eta_bn,
        )
        Thana.objects.bulk_create([
            Thana(district=district, name=t_en, name_en=t_en, name_bn=t_bn) for t_en, t_bn in thanas
        ])


class Migration(migrations.Migration):

    dependencies = [
        ("web", "0019_districts_thanas_order_thana"),
    ]

    operations = [
        migrations.RunPython(fill, migrations.RunPython.noop),
    ]
