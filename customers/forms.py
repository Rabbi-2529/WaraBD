from django import forms
from django.utils.translation import gettext_lazy as _

from web.bd import BD_DISTRICTS, normalize_bd_phone

from .models import CustomerAddress

_INPUT = {"class": "form-control"}


class PhoneField(forms.CharField):
    """Bangladeshi mobile number; accepts +880 / 880 / 0 and Bangla digits, returns 01XXXXXXXXX."""

    def __init__(self, **kwargs):
        kwargs.setdefault("label", _("Mobile number"))
        kwargs.setdefault("max_length", 20)
        kwargs.setdefault("widget", forms.TextInput(attrs={
            "type": "tel", "inputmode": "numeric", "autocomplete": "tel", "placeholder": "01XXXXXXXXX",
            "pattern": "01[3-9][0-9]{8}", "title": "01XXXXXXXXX",
        }))
        super().__init__(**kwargs)

    def clean(self, value):
        value = super().clean(value)
        if not value:
            return value
        try:
            return normalize_bd_phone(value)
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc


class LoginForm(forms.Form):
    phone = PhoneField()


class RegisterForm(forms.Form):
    name = forms.CharField(label=_("Full name"), max_length=150, min_length=3,
                           widget=forms.TextInput(attrs={"autocomplete": "name", "placeholder": _("Your full name")}))
    phone = PhoneField()
    email = forms.EmailField(label=_("Email (optional)"), required=False,
                             widget=forms.EmailInput(attrs={"autocomplete": "email", "placeholder": "you@example.com"}))


class OtpForm(forms.Form):
    code = forms.CharField(label=_("6-digit code"), max_length=12, widget=forms.TextInput(attrs={
        "inputmode": "numeric", "autocomplete": "one-time-code", "pattern": "[0-9০-৯ ]*",
        "maxlength": "6", "class": "otp-input", "placeholder": "••••••", "autofocus": True,
    }))


class ProfileForm(forms.Form):
    name = forms.CharField(label=_("Full name"), max_length=150, min_length=3)
    email = forms.EmailField(label=_("Email (optional)"), required=False)


class ChangePhoneForm(forms.Form):
    phone = PhoneField(label=_("New mobile number"))


class AddressForm(forms.ModelForm):
    class Meta:
        model = CustomerAddress
        fields = ["label", "name", "phone", "district", "thana", "address", "is_default"]
        widgets = {
            "label": forms.TextInput(attrs={"placeholder": _("e.g. Home, Office")}),
            "phone": forms.TextInput(attrs={"type": "tel", "placeholder": "01XXXXXXXXX"}),
            "address": forms.TextInput(attrs={"placeholder": _("House, road, area")}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils.translation import gettext

        # District → thana dropdowns (Select2, filled by app.js bindLocationSelects).
        # Values stay English (stored), labels follow the page language.
        current_district = self["district"].value() or ""
        current_thana = self["thana"].value() or ""
        self.fields["district"].choices = [("", _("Select your district"))] + [
            (d, gettext(d)) for d in BD_DISTRICTS
        ]
        self.fields["district"].widget.attrs.update({"data-district-select": "", "data-selected": current_district})
        self.fields["thana"].required = True
        self.fields["thana"].widget = forms.Select(
            choices=[(current_thana, current_thana)] if current_thana else [("", _("Select district first"))],
            attrs={"data-thana-select": "", "data-selected": current_thana},
        )

    def clean_phone(self):
        try:
            return normalize_bd_phone(self.cleaned_data.get("phone"))
        except ValueError as exc:
            raise forms.ValidationError(str(exc)) from exc
