
import re

from django import forms

from .widgets import RichTextarea
from django.utils.text import slugify

from .models import ContactMessage, Order, Product


def _bs(placeholder=""):
    return {
        "class": "form-control",
        "placeholder": placeholder,
    }


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = [
            "name",
            "email",
            "phone",
            "subject",
            "message",
        ]
        widgets = {
            "name": forms.TextInput(attrs=_bs("Your name")),
            "email": forms.EmailInput(attrs=_bs("you@example.com")),
            "phone": forms.TextInput(attrs=_bs("Optional")),
            "subject": forms.TextInput(attrs=_bs("How can we help?")),
            "message": forms.Textarea(
                attrs={
                    **_bs("Write your message…"),
                    "rows": 5,
                }
            ),
        }


class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            "full_name",
            "email",
            "phone",
            "address_line1",
            "address_line2",
            "city",
            "postal_code",
            "country",
            "notes",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs=_bs("Full name")),
            "email": forms.EmailInput(attrs=_bs("you@example.com")),
            "phone": forms.TextInput(attrs=_bs("Phone")),
            "address_line1": forms.TextInput(attrs=_bs("Street address")),
            "address_line2": forms.TextInput(
                attrs=_bs("Apt, suite (optional)")
            ),
            "city": forms.TextInput(attrs=_bs("City")),
            "postal_code": forms.TextInput(attrs=_bs("Postal code")),
            "country": forms.TextInput(attrs=_bs("Country")),
            "notes": forms.Textarea(
                attrs={
                    **_bs("Order notes (optional)"),
                    "rows": 3,
                }
            ),
        }


# First URL segments used by other pages: a product slug must never be one of these.
RESERVED_SLUGS = {
    "products", "portfolio", "about", "contact", "cart", "checkout", "order", "track-order",
    "page", "api", "account", "accounts", "admin", "admin-invoice", "bn", "en", "static",
    "media", "sitemap-xml", "robots-txt",
}


def make_slug(text, keep_case=False):
    """Like slugify, but optionally keeps capitals (e.g. 'Huion 420 H420' -> 'Huion-420-H420')."""
    if not keep_case:
        return slugify(text)
    import unicodedata

    ascii_text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9_]+", "-", ascii_text).strip("-_")


class TextListField(forms.CharField):
    """Edit a JSON list as plain text in the admin (one item per line).

    Sub-classes convert between the stored structure and the text shown in
    the textarea, so staff never have to type JSON.
    """

    help_text_default = ""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.Textarea(attrs={"class": "form-control", "rows": 5}))
        kwargs.setdefault("help_text", self.help_text_default)
        super().__init__(*args, **kwargs)

    # stored value -> text
    def prepare_value(self, value):
        if isinstance(value, str):
            return value  # re-displaying what was typed (e.g. after an error)
        return self.to_text(value or self.empty_value_stored())

    def empty_value_stored(self):
        return []

    def to_text(self, value):
        return "\n".join(str(v) for v in value)

    # text -> stored value
    def to_python(self, value):
        text = super().to_python(value) or ""
        lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
        return self.from_lines(lines, text)

    def from_lines(self, lines, text):
        return [line for line in lines if line]

    def has_changed(self, initial, data):
        try:
            return self.to_python(data) != (initial or self.empty_value_stored())
        except forms.ValidationError:
            return True


class HighlightsField(TextListField):
    help_text_default = "One highlight per line."


class SpecsField(TextListField):
    help_text_default = "One per line, as  Label: Value   e.g.  Model: FT-SCL029"

    def to_text(self, value):
        rows = []
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                rows.append(f"{item[0]}: {item[1]}")
            elif isinstance(item, dict):
                rows.append(f"{item.get('label', '')}: {item.get('value', '')}")
        return "\n".join(rows)

    def from_lines(self, lines, text):
        rows, bad = [], []
        for line in lines:
            if not line:
                continue
            label, sep, val = line.partition(":")
            if not sep or not label.strip() or not val.strip():
                bad.append(line)
                continue
            rows.append([label.strip(), val.strip()])
        if bad:
            raise forms.ValidationError(
                "Each line needs a label and a value separated by a colon. Check: %s" % "; ".join(bad[:3])
            )
        return rows


class FeaturesField(TextListField):
    help_text_default = "One per line:  icon | Title | Text   (icon is optional, e.g. keypad, usb, lock, battery, zap, shield)"

    def to_text(self, value):
        rows = []
        for item in value:
            if isinstance(item, dict):
                rows.append(" | ".join([item.get("icon", "check"), item.get("title", ""), item.get("text", "")]))
        return "\n".join(rows)

    def from_lines(self, lines, text):
        rows = []
        for line in lines:
            if not line:
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                icon, title, body = parts[0] or "check", parts[1], " | ".join(parts[2:])
            elif len(parts) == 2:
                icon, title, body = "check", parts[0], parts[1]
            else:
                icon, title, body = "check", parts[0], ""
            rows.append({"icon": icon, "title": title, "text": body})
        return rows


class StepsField(TextListField):
    help_text_default = "One step per line:  Title | Text"

    def to_text(self, value):
        rows = []
        for item in value:
            if isinstance(item, dict):
                rows.append(f"{item.get('title', '')} | {item.get('text', '')}".strip(" |"))
            elif isinstance(item, str):
                rows.append(item)
        return "\n".join(rows)

    def from_lines(self, lines, text):
        rows = []
        for line in lines:
            if not line:
                continue
            title, sep, body = line.partition("|")
            if sep:
                rows.append({"title": title.strip(), "text": body.strip()})
            else:
                rows.append({"title": "", "text": title.strip()})
        return rows


class FaqField(TextListField):
    help_text_default = "Write  Q: question  on one line and  A: answer  on the next. Leave a blank line between questions."

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", forms.Textarea(attrs={"class": "form-control", "rows": 8}))
        super().__init__(*args, **kwargs)

    def to_text(self, value):
        blocks = []
        for item in value:
            if isinstance(item, dict):
                blocks.append(f"Q: {item.get('q', '')}\nA: {item.get('a', '')}")
        return "\n\n".join(blocks)

    def from_lines(self, lines, text):
        rows, current, bad = [], None, []
        for line in lines + [""]:
            upper = line[:2].upper()
            if upper == "Q:":
                if current:
                    rows.append(current)
                current = {"q": line[2:].strip(), "a": ""}
            elif upper == "A:" and current is not None:
                current["a"] = (current["a"] + "\n" + line[2:].strip()).strip()
            elif not line:
                if current:
                    rows.append(current)
                current = None
            elif current is not None:
                current["a"] = (current["a"] + "\n" + line).strip()
            else:
                bad.append(line)
        if bad:
            raise forms.ValidationError("Start each question with  Q:  Check: %s" % "; ".join(bad[:3]))
        missing = [r["q"] for r in rows if not r["a"]]
        if missing:
            raise forms.ValidationError("These questions have no  A:  answer: %s" % "; ".join(missing[:3]))
        return rows


class ApplicationsField(TextListField):
    help_text_default = "Two lines:  Works with: Cabinets, Drawers   and   Used in: Kitchen, Office, Hotel"

    def empty_value_stored(self):
        return {}

    def to_text(self, value):
        if not isinstance(value, dict):
            return ""
        rows = []
        if value.get("compatible"):
            rows.append("Works with: " + ", ".join(value["compatible"]))
        if value.get("places"):
            rows.append("Used in: " + ", ".join(value["places"]))
        return "\n".join(rows)

    def from_lines(self, lines, text):
        result = {}
        for line in lines:
            if not line:
                continue
            key, sep, rest = line.partition(":")
            items = [i.strip() for i in rest.split(",") if i.strip()]
            name = key.strip().lower()
            if not sep or name not in ("works with", "used in"):
                raise forms.ValidationError("Start the lines with  Works with:  or  Used in:")
            result["compatible" if name == "works with" else "places"] = items
        return result


class TagsField(forms.CharField):
    """Comma-separated tags <-> list (e.g. FCC, CE, RoHS)."""

    def prepare_value(self, value):
        if isinstance(value, (list, tuple)):
            return ", ".join(str(v) for v in value)
        return value or ""

    def to_python(self, value):
        text = super().to_python(value) or ""
        return [t.strip() for t in text.split(",") if t.strip()]


# English + Bangla pairs shown in the "Product page content" card of the
# custom admin template (templates/admin/web/product/add_form.html).
PRODUCT_TEXT_FIELDS = [
    ("subtitle", "Subtitle", forms.TextInput),
    ("short_description", "Short description", forms.Textarea),
    ("description_title", "Description heading", forms.TextInput),
    ("warranty", "Warranty", forms.TextInput),
    ("color", "Color", forms.TextInput),
]
PRODUCT_LIST_FIELDS = [
    ("highlights", "Highlights", HighlightsField),
    ("specs", "Specifications", SpecsField),
    ("features", "Features", FeaturesField),
    ("steps", "How to use (steps)", StepsField),
    ("faq", "FAQ", FaqField),
    ("applications", "Works with / used in", ApplicationsField),
]
LANGS = (("en", "English"), ("bn", "বাংলা"))


def product_form_fields():
    names = ["name_en", "name_bn", "slug", "sku", "model_number", "stock", "stock_status",
             "description_en", "description_bn", "image", "price", "discount_type",
             "discount_price", "brand", "category", "sub_category", "is_active", "is_featured", "tags"]
    for field, _label, _widget in PRODUCT_TEXT_FIELDS:
        names += [f"{field}_en", f"{field}_bn"]
    for field, _label, _cls in PRODUCT_LIST_FIELDS:
        names += [f"{field}_en", f"{field}_bn"]
    names += ["seo_title_en", "seo_title_bn", "seo_description_en", "seo_description_bn", "share_image"]
    return names


class ProductOrganizeForm(forms.ModelForm):
    tags = TagsField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter tags separated by commas"}),
    )

    class Meta:
        model = Product
        fields = product_form_fields()
        widgets = {
            "name_en": forms.TextInput(attrs={"class": "form-control", "placeholder": "Product name (English)"}),
            "name_bn": forms.TextInput(attrs={"class": "form-control", "placeholder": "পণ্যের নাম (বাংলা)", "lang": "bn"}),
            "slug": forms.TextInput(attrs={"class": "form-control", "placeholder": "Product URL slug"}),
            "sku": forms.TextInput(attrs={"class": "form-control", "placeholder": "Product SKU"}),
            "model_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. FT-SCL029"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "min": "0"}),
            "stock_status": forms.Select(attrs={"class": "form-control"}),
            "description_en": RichTextarea(attrs={"class": "form-control", "placeholder": "Write the product description in English…"}),
            "description_bn": RichTextarea(attrs={"class": "form-control", "placeholder": "পণ্যের বিবরণ (বাংলা) লিখুন…", "lang": "bn"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "placeholder": "Enter product price"}),
            "discount_type": forms.Select(attrs={"class": "form-control"}),
            "discount_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0", "placeholder": "Enter discount value"}),
            "brand": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter brand name"}),
            "category": forms.Select(attrs={"class": "form-control"}),
            "sub_category": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. Smart Locks"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "is_featured": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "name_en" in self.fields:
            self.fields["name_en"].required = True
            self.fields["name_en"].label = "Product name (English)"
        if "name_bn" in self.fields:
            self.fields["name_bn"].label = "Product name (বাংলা)"
        for field, label, widget_cls in PRODUCT_TEXT_FIELDS:
            for code, lang_label in LANGS:
                name = f"{field}_{code}"
                if name not in self.fields:
                    continue
                attrs = {"class": "form-control"}
                if widget_cls is forms.Textarea:
                    attrs["rows"] = 3
                if code == "bn":
                    attrs["lang"] = "bn"
                self.fields[name].widget = widget_cls(attrs=attrs)
                self.fields[name].label = f"{label} ({lang_label})"
        for field, label, field_cls in PRODUCT_LIST_FIELDS:
            for code, lang_label in LANGS:
                name = f"{field}_{code}"
                if name not in self.fields:
                    continue
                new_field = field_cls(label=f"{label} ({lang_label})")
                if code == "bn":
                    new_field.widget.attrs["lang"] = "bn"
                    new_field.help_text = "Leave empty to show the English list on the Bangla page."
                self.fields[name] = new_field
        # SEO & sharing (Phase 6)
        for code, lang_label in LANGS:
            for field, label, limit, rows in (("seo_title", "SEO title", 70, None), ("seo_description", "SEO description", 170, 2)):
                name = f"{field}_{code}"
                if name not in self.fields:
                    continue
                attrs = {"class": "form-control", "maxlength": limit, "data-count": limit}
                if code == "bn":
                    attrs["lang"] = "bn"
                self.fields[name].widget = forms.Textarea(attrs={**attrs, "rows": rows}) if rows else forms.TextInput(attrs=attrs)
                self.fields[name].label = f"{label} ({lang_label})"
        if "share_image" in self.fields:
            self.fields["share_image"].widget.attrs.update({"class": "form-control", "accept": "image/*"})

    def clean_slug(self):
        """
        Unique product address, StarTech style: /huion-420-H420.

        Typed slug: kept as typed (capitals allowed, spaces/slashes become "-").
        Empty slug: English name + model number, e.g. "wara-smart-lock-ft-scl029".
        Duplicates get -2, -3 …; words used by other pages (about, cart …) get "-product".
        """
        supplied_slug = (self.cleaned_data.get("slug") or "").strip()
        if supplied_slug:
            base_slug = make_slug(supplied_slug, keep_case=True)
        else:
            product_name = self.cleaned_data.get("name_en", "")
            model = (self.data.get("model_number") or "").strip()
            if model and slugify(model) not in slugify(product_name):
                product_name = f"{product_name} {model}"
            base_slug = slugify(product_name)
        base_slug = base_slug or "product"
        if base_slug.lower() in RESERVED_SLUGS:
            base_slug = f"{base_slug}-product"

        slug_field = Product._meta.get_field("slug")
        max_length = slug_field.max_length or 255

        products = Product.objects.all()

        # Exclude the current product when editing.
        if self.instance and self.instance.pk:
            products = products.exclude(pk=self.instance.pk)

        candidate = base_slug[:max_length].strip("-")

        if not candidate:
            candidate = "product"[:max_length]

        counter = 2

        while products.filter(slug=candidate).exists():
            suffix = f"-{counter}"
            available_length = max_length - len(suffix)

            candidate = (
                f"{base_slug[:available_length].rstrip('-')}{suffix}"
            )

            counter += 1

        return candidate
