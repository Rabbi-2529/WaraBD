"""Empty the shop's catalogue so it can be entered again from scratch.

    python manage.py clear_catalog          # shows what WOULD be deleted, deletes nothing
    python manage.py clear_catalog --yes    # deletes it

On the live server (cPanel), run it with the production settings and the .env file:

    DJANGO_READ_DOT_ENV_FILE=True python manage.py clear_catalog --settings=config.settings.production

Deletes: all orders (and their lines), all products (and their gallery pictures),
product categories, the Portfolio page's use cases, portfolio projects, and the
uploaded picture files of everything deleted.
Keeps: customers and their addresses, site settings, page text, policy pages,
delivery charges, SEO keywords, SMS log.

Orders go too because a product that is in an order cannot be deleted.
"""

from django.core.management.base import BaseCommand
from django.db import connection, models, transaction

from web.models import Category, Order, OrderItem, PortfolioProject, Product, ProductImage, UseCase

# Order matters: order lines before products (an order line protects its product).
TABLES = [
    ("order lines", OrderItem),
    ("orders", Order),
    ("product gallery pictures", ProductImage),
    ("products", Product),
    ("product categories", Category),
    ("portfolio use cases", UseCase),
    ("portfolio projects", PortfolioProject),
]


def _file_fields(model):
    return [f for f in model._meta.get_fields() if isinstance(f, models.FileField)]


def _files_of(model):
    """Names of the uploaded files the rows of this table point to."""
    names = set()
    for field in _file_fields(model):
        for name in model.objects.exclude(**{field.name: ""}).exclude(**{f"{field.name}__isnull": True}) \
                .values_list(field.name, flat=True):
            if name:
                names.add((field, name))
    return names


class Command(BaseCommand):
    help = "Delete all orders, products, categories, portfolio use cases and portfolio projects (dry run unless --yes)."

    def add_arguments(self, parser):
        parser.add_argument("--yes", action="store_true", help="Really delete. Without it, only shows what would go.")
        parser.add_argument("--keep-files", action="store_true", help="Leave the uploaded picture files on disk.")

    def handle(self, *args, **options):
        db = connection.settings_dict
        self.stdout.write(f"Database: {db.get('NAME')} on {db.get('HOST') or 'localhost'}")
        counts = [(label, model, model.objects.count()) for label, model in TABLES]
        files = set()
        for _label, model, _n in counts:
            files |= _files_of(model)
        for label, _model, n in counts:
            self.stdout.write(f"  {label:<26} {n}")
        self.stdout.write(f"  {'uploaded picture files':<26} {0 if options['keep_files'] else len(files)}")

        if not options["yes"]:
            self.stdout.write(self.style.WARNING("Nothing deleted. Run again with --yes to delete the above."))
            return

        with transaction.atomic():
            for _label, model, _n in counts:
                model.objects.all().delete()

        removed = 0
        if not options["keep_files"]:
            for field, name in files:
                try:
                    if field.storage.exists(name):
                        field.storage.delete(name)
                        removed += 1
                except OSError as exc:
                    self.stderr.write(f"Could not delete {name}: {exc}")
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {sum(n for _l, _m, n in counts)} rows and {removed} picture files. "
            "Customers, site settings, pages and delivery charges were kept."))
