"""Load the real WaRa FT-SCL029 product and the storefront content.

    python manage.py seed_wara

Safe to run more than once: the product is only created if its slug is
missing, and each content section is only filled while it is still empty,
so anything already edited in the admin is never overwritten.

Product photos are not included — upload them in the admin
(Products -> FT-SCL029 -> Image / Gallery images).
"""

from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import translation

from web.models import (
    Category,
    Product,
    SiteFeature,
    SiteHighlight,
    SiteSettings,
    TimelineStep,
    UseCase,
)

from . import _seed_wara_bn as bn


PRODUCT = {
    "slug": "ft-scl029",
    "name": "WaRa FT-SCL029 Cabinet Drawer Lock",
    "subtitle": "With Visitor Password Changing Access",
    "short_description": (
        "A compact round keypad and a motorized lock body that turn any cabinet, "
        "drawer, wardrobe or locker into keyless, code-protected storage."
    ),
    "description_title": "Keyless, code-protected storage for anything with a door",
    "description": (
        "The WaRa FT-SCL029 replaces the old key-and-cylinder cabinet lock with a slim "
        "round keypad. The keypad sits on the outside of the door; a motorized lock body "
        "mounts neatly inside, so there's nothing to pick and no key to lose.\n\n"
        "Two password levels keep control in the right hands: a management code for the "
        "owner and a user code for everyday access. Switch to public mode and each visitor "
        "sets their own code — ideal for gyms, spas, hotels, schools and shared offices.\n\n"
        "For backup, the lock supports one main USB key and three management USB keys. Low "
        "power consumption gives long battery life, a low-battery reminder warns you in good "
        "time, and an external USB emergency power port means you're never locked out."
    ),
    "brand": "WaRa",
    "model_number": "FT-SCL029",
    "sku": "WR-SCL029-BK",
    "color": "Black",
    "warranty": "1 Year",
    # ৳2,050 regular price, ৳75 off = ৳1,975 selling price.
    "price": Decimal("2050"),
    "discount_type": "fixed",
    "discount_price": Decimal("75"),
    # Placeholder stock so the product can be ordered — set the real count in the admin.
    "stock": 20,
    "stock_status": Product.STOCK_IN,
    "is_active": True,
    "is_featured": True,
    "tags": ["FCC", "CE", "RoHS", "Motorized lock"],
    "highlights": [
        "Password & USB key unlock",
        "Management + user codes",
        "Public (visitor) & private modes",
        "1 main + 3 management USB keys",
        "Low-battery reminder",
        "USB emergency power",
    ],
    "specs": [
        ["Model", "FT-SCL029"],
        ["Brand", "WaRa"],
        ["Type", "Furniture / cabinet & drawer lock"],
        ["Unlock methods", "Password, USB key"],
        ["Password sets", "Management code + user code"],
        ["USB key management", "1 main key + 3 management keys"],
        ["Usage modes", "Public (visitor) mode & private mode"],
        ["Locking system", "Motorized mechanism"],
        ["Front body (keypad)", "Ø 50.5 mm × 12.5 mm"],
        ["Back body (lock)", "60 × 86 × 23.5 mm (W × H × D)"],
        ["Suitable door thickness", "More than 3 mm"],
        ["Housing material", "ABS"],
        ["Power", "Low power consumption, low-battery reminder, external USB emergency power"],
        ["Color", "Black"],
        ["Design style", "Minimalist"],
        ["Certification", "FCC, CE, RoHS"],
        ["Compatible with", "Cabinets, drawers, wardrobes, lockers"],
        ["Warranty", "1 Year"],
    ],
    "features": [
        {"icon": "keypad", "title": "Two password sets", "text": "A management code for the owner and a user code for daily access."},
        {"icon": "users", "title": "Visitor password changing", "text": "In public mode each visitor sets their own one-time code."},
        {"icon": "usb", "title": "USB key management", "text": "One main key plus three management keys for backup control."},
        {"icon": "lock", "title": "Motorized mechanism", "text": "Smooth, quiet electric locking with no exposed key cylinder."},
        {"icon": "battery", "title": "Low power, long life", "text": "Low power consumption with a reminder before the battery runs low."},
        {"icon": "zap", "title": "USB emergency power", "text": "Plug in external USB power to open the lock even with flat batteries."},
    ],
    "applications": {
        "compatible": ["Cabinets", "Drawers", "Wardrobes", "Lockers"],
        "places": [
            "Kitchen", "Bathroom", "Living room", "Bedroom", "Dining", "Hotel",
            "Office building", "Hospital", "School", "Mall", "Sports venues",
            "Leisure facilities", "Supermarket", "Warehouse", "Workshop",
            "Storage & closet", "Wine cellar", "Gym",
        ],
    },
    "steps": [
        {"title": "Mount it", "text": "Fix the keypad on the front and screw the lock body inside a door thicker than 3 mm."},
        {"title": "Set your codes", "text": "Create the management code first, then add a user code for daily use."},
        {"title": "Pick a mode", "text": "Public mode for visitors, private mode for a fixed personal code."},
        {"title": "Tap & open", "text": "Enter the code and the motor unlocks. USB keys and USB power are your backup."},
    ],
    "faq": [
        {"q": "What is the difference between public and private mode?",
         "a": "In public mode each visitor sets their own code when they lock, and it is released once they unlock — perfect for gyms, hotels and shared lockers. In private mode the lock keeps one fixed user code, ideal for your own cabinet or office drawer."},
        {"q": "What happens if the battery runs out?",
         "a": "The lock warns you with a low-battery reminder well before it runs flat. If it does run out, connect external USB power (for example a power bank) to the emergency port and open it with your code."},
        {"q": "I forgot the user code. Can I still open it?",
         "a": "Yes. The management code or one of the USB management keys can open the lock, after which you can set a new user code."},
        {"q": "Will it fit my cabinet or drawer?",
         "a": "The keypad is Ø 50.5 mm on the front and the lock body is 60 × 86 × 23.5 mm inside. It suits doors and drawer fronts thicker than 3 mm. Send us a photo on WhatsApp if you are unsure."},
        {"q": "Do I need an electrician to install it?",
         "a": "No. There is no mains wiring — you only need a drill and a screwdriver. Our team can guide you over phone or WhatsApp."},
        {"q": "How can I pay?",
         "a": "Cash on delivery anywhere in Bangladesh, or pay in advance with bKash or Nagad at checkout."},
    ],
}

HIGHLIGHTS = [
    ("Two password sets", "Management code + user code", "keypad"),
    ("USB key control", "1 main key + 3 management keys", "usb"),
    ("Public & private", "Visitors can set their own code", "users"),
    ("Never locked out", "Low-battery alert + USB power", "battery"),
]

FEATURES = {
    "home_mode": [
        {"title": "Public mode", "icon": "users", "badge": "Visitor password",
         "text": "Each visitor sets their own code when locking\nThe code is released after they unlock\nNo codes passed between strangers\nManagement code & USB key can always override",
         "best_for": "gyms, spas, hotels, schools, malls"},
        {"title": "Private mode", "icon": "user", "badge": "Fixed code",
         "text": "One fixed user code for everyday access\nSeparate management code for the owner\n1 main + 3 management USB keys as backup\nIdeal for personal and staff storage",
         "best_for": "homes, offices, clinics, shops"},
    ],
    "home_why": [
        {"title": "Genuine product", "icon": "shield", "text": "Original WaRa locks, certified FCC, CE and RoHS."},
        {"title": "Cash on delivery", "icon": "cash", "text": "Pay when it reaches you — or use bKash / Nagad."},
        {"title": "Setup help", "icon": "headset", "text": "Call or WhatsApp us and we'll guide your installation."},
        {"title": "1-year warranty", "icon": "award", "text": "Covered against manufacturing defects for a full year."},
    ],
    "about_mission": [
        {"title": "Our mission", "icon": "target", "text": "Replace easily lost keys with simple, reliable keypad security for every cabinet, drawer and locker."},
        {"title": "Our vision", "icon": "eye", "text": "A Bangladesh where homes and businesses protect what matters without fuss, wiring or high cost."},
        {"title": "Our promise", "icon": "heart", "text": "Genuine products, clear prices and support that answers — before and after you buy."},
    ],
    "about_why": [
        {"title": "Genuine", "icon": "shield", "text": "Certified FCC, CE and RoHS — sourced directly, never copies."},
        {"title": "Nationwide", "icon": "truck", "text": "Cash on delivery to all 64 districts of Bangladesh."},
        {"title": "Setup help", "icon": "tool", "text": "Step-by-step installation guidance on phone or WhatsApp."},
        {"title": "Warranty", "icon": "refresh", "text": "One full year of cover against manufacturing defects."},
    ],
}

TIMELINE = [
    ("You place an order", "cart", "Online, by phone or on WhatsApp — whichever is easiest for you."),
    ("We call to confirm", "phone", "Our team confirms your address, quantity and preferred payment method."),
    ("Fast delivery", "truck", "1–2 working days inside Dhaka, 2–4 working days elsewhere in Bangladesh."),
    ("Installation support", "tool", "Stuck on a step? Send us a photo or video and we'll walk you through it."),
    ("Covered for a year", "shield", "If anything goes wrong because of a defect, we repair or replace it."),
]

USE_CASES = [
    ("home", "archive", "", "Bedroom Wardrobes", "Homes & apartments", "private", "Keep jewellery, cash and documents behind a code only your family knows."),
    ("home", "drawer", "red", "Kitchen & Medicine Drawers", "Family homes", "private", "Child-safe storage for knives, cleaning products and medicines — no key lying around."),
    ("home", "wine", "green", "Wine & Display Cabinets", "Homes, lounges, cellars", "private", "A clean round keypad that protects collections without spoiling the look of the furniture."),
    ("office", "briefcase", "", "Office Filing Cabinets", "Corporate offices", "private", "Admins hold the management code, staff use a user code — confidential files stay confidential."),
    ("office", "users", "red", "Shared Staff Lockers", "Co-working & hot-desk floors", "public", "Each employee sets a fresh code for the day; the locker is free again after they leave."),
    ("hospitality", "bed", "green", "Hotel Room Wardrobes", "Hotels & guest houses", "public", "Guests choose their own code at check-in while management keeps master access by USB key."),
    ("hospitality", "hospital", "", "Medicine Cabinets", "Hospitals, clinics & pharmacies", "private", "Restrict drug cabinets and patient-record drawers to authorised staff only."),
    ("public", "activity", "red", "Gym, Spa & Pool Lockers", "Fitness & leisure centres", "public", "Members pick any code, store their things, and the locker resets for the next person."),
    ("public", "book", "green", "School & Campus Lockers", "Schools, colleges, libraries", "public", "No more lost keys or cut padlocks — students simply set and remember their own code."),
    ("public", "grid", "", "Shopper Bag-Drop Lockers", "Malls & supermarkets", "public", "Self-service bag lockers that need no attendant and no key handover."),
    ("commercial", "cash", "red", "Retail Cash & Stock Drawers", "Shops & showrooms", "private", "Lock away cash, cards and high-value stock under the counter with a quick-entry code."),
    ("commercial", "box", "green", "Warehouse Tool Cabinets", "Warehouses & workshops", "private", "Give shift supervisors their own access while USB management keys provide backup."),
]


class Command(BaseCommand):
    help = "Load the FT-SCL029 product and Home/About/Portfolio content (only where empty)."

    def handle(self, *args, **options):
        # Always write the English text into the English (_en) columns, even if
        # a Bangla request left "bn" active in this thread.
        with translation.override("en"), transaction.atomic():
            self._seed()
        # Page text, page lists and policy pages (Phase 3).
        call_command("sync_content", stdout=self.stdout)

    def _seed(self):
        self._product()
        self._fill(SiteHighlight, "Home highlights", [
            SiteHighlight(title=t, subtitle=s, icon=i, order=n)
            for n, (t, s, i) in enumerate(HIGHLIGHTS, 1)
        ])
        for section, rows in FEATURES.items():
            self._fill(
                SiteFeature,
                f"Feature cards ({section})",
                [SiteFeature(section=section, order=n, **row) for n, row in enumerate(rows, 1)],
                existing=SiteFeature.objects.filter(section=section),
            )
        self._fill(TimelineStep, "About timeline", [
            TimelineStep(title=t, icon=i, text=x, order=n)
            for n, (t, i, x) in enumerate(TIMELINE, 1)
        ])
        self._fill(UseCase, "Use cases", [
            UseCase(category=c, icon=i, tone=tone, title=t, place=p, mode=m, text=x, order=n)
            for n, (c, i, tone, t, p, m, x) in enumerate(USE_CASES, 1)
        ])
        self._bangla()

    def _bangla(self):
        """Fill empty Bangla (_bn) fields for rows that still have the seeded English."""
        changed = 0

        def untranslated(obj, field):
            # Empty, or just a copy of the English / the field default
            # (modeltranslation fills new _bn columns with the English default).
            current = getattr(obj, f"{field}_bn")
            default = obj._meta.get_field(f"{field}_bn").default
            return not current or current == getattr(obj, f"{field}_en") or current == default

        def fill(obj, values):
            nonlocal changed
            dirty = []
            for field, value in values.items():
                if untranslated(obj, field):
                    setattr(obj, f"{field}_bn", value)
                    dirty.append(f"{field}_bn")
            if dirty:
                obj.save(update_fields=dirty)
                changed += 1

        product = Product.objects.filter(slug=PRODUCT["slug"], name_en=PRODUCT["name"]).first()
        if product:
            fill(product, bn.PRODUCT_BN)
        for category in Category.objects.filter(name_en__in=bn.CATEGORY_BN):
            fill(category, {"name": bn.CATEGORY_BN[category.name_en]})
        for row in SiteHighlight.objects.filter(title_en__in=bn.HIGHLIGHTS_BN):
            title, subtitle = bn.HIGHLIGHTS_BN[row.title_en]
            fill(row, {"title": title, "subtitle": subtitle})
        for row in SiteFeature.objects.all():
            values = bn.FEATURES_BN.get((row.section, row.title_en))
            if values:
                fill(row, values)
        for row in TimelineStep.objects.filter(title_en__in=bn.TIMELINE_BN):
            title, text = bn.TIMELINE_BN[row.title_en]
            fill(row, {"title": title, "text": text})
        for row in UseCase.objects.filter(title_en__in=bn.USE_CASES_BN):
            title, place, text = bn.USE_CASES_BN[row.title_en]
            fill(row, {"title": title, "place": place, "text": text})

        site = SiteSettings.load()
        values = {}
        for field, mapping in bn.SETTINGS_BN.items():
            english = getattr(site, f"{field}_en") or ""
            if english in mapping:
                values[field] = mapping[english]
        for field, (prefix, bangla) in bn.SETTINGS_BN_PREFIX.items():
            if (getattr(site, f"{field}_en") or "").startswith(prefix):
                values[field] = bangla
        fill(site, values)

        if changed:
            self.stdout.write(self.style.SUCCESS(f"  added Bangla text to {changed} rows"))
        else:
            self.stdout.write("  skip  Bangla text (already filled or English was edited)")

    def _product(self):
        if Product.objects.filter(slug=PRODUCT["slug"]).exists():
            self.stdout.write(f"  skip  Product {PRODUCT['slug']} (already exists)")
            return
        category, _ = Category.objects.get_or_create(
            slug="smart-cabinet-lock",
            defaults={"name": "Smart Cabinet Lock"},
        )
        Product.objects.create(category=category, **PRODUCT)
        self.stdout.write(self.style.SUCCESS(f"  added Product {PRODUCT['slug']} (upload its photos in the admin)"))

    def _fill(self, model, label, objects, existing=None):
        existing = model.objects.all() if existing is None else existing
        if existing.exists():
            self.stdout.write(f"  skip  {label} (already has {existing.count()})")
            return
        model.objects.bulk_create(objects)
        self.stdout.write(self.style.SUCCESS(f"  added {label}: {len(objects)}"))
