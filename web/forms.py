
from django import forms
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


class ProductOrganizeForm(forms.ModelForm):
    tags = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter tags separated by commas",
            }
        ),
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "slug",
            "sku",
            "stock",
            "stock_status",
            "description",
            "image",
            "price",
            "discount_type",
            "discount_price",
            "brand",
            "category",
            "sub_category",
            "is_active",
            "tags",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Product name",
                }
            ),
            "slug": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Product URL slug",
                }
            ),
            "sku": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Product SKU",
                }
            ),
            "stock": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
            "stock_status": forms.Select(
                attrs={"class": "form-control"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Enter product description",
                }
            ),
            "image": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Enter product price",
                }
            ),
            "discount_type": forms.Select(
                attrs={"class": "form-control"}
            ),
            "discount_price": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Enter discount value",
                }
            ),
            "brand": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter brand name",
                }
            ),
            "category": forms.Select(
                attrs={"class": "form-control"}
            ),
            "sub_category": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Smart Locks",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def clean_slug(self):
        """
        Automatically generate a unique product slug.

        Examples:
            wireless-speaker
            wireless-speaker-2
            wireless-speaker-3
        """
        supplied_slug = self.cleaned_data.get("slug", "")
        product_name = self.cleaned_data.get("name", "")

        base_slug = slugify(supplied_slug or product_name) or "product"

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

    def clean_tags(self):
        tags = self.cleaned_data.get("tags", "")

        if not tags:
            return []

        return [
            tag.strip()
            for tag in tags.split(",")
            if tag.strip()
        ]
