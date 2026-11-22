"""CKEditor 5 for long text in the admin (descriptions, page bodies, card text).

The editor itself comes from the official CDN (classic build, GPL); the
small `admin/js/wara-editor.js` script starts it on every
<textarea data-rich-editor> and sends pasted / dropped pictures to
/admin/editor-upload/ (staff only, CSRF protected).
"""

from django import forms
from django.urls import reverse_lazy

CKEDITOR_JS = "https://cdn.ckeditor.com/ckeditor5/41.4.2/classic/ckeditor.js"


class RichTextarea(forms.Textarea):
    def __init__(self, attrs=None, *, compact=False):
        base = {"data-rich-editor": "compact" if compact else "full", "rows": 8}
        base.update(attrs or {})
        super().__init__(attrs=base)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"]["data-upload-url"] = str(reverse_lazy("editor_upload"))
        return context

    class Media:
        js = (CKEDITOR_JS, "admin/js/wara-editor.js")
        css = {"all": ("admin/css/wara-editor.css",)}


# Django's own copy of jQuery + Select2 (the admin already ships them for autocomplete fields).
ADMIN_SELECT2_JS = (
    "admin/js/vendor/jquery/jquery.js",
    "admin/js/vendor/select2/select2.full.js",
    "admin/js/jquery.init.js",
)
ADMIN_SELECT2_CSS = ("admin/css/vendor/select2/select2.css",)


class KeywordTagsWidget(forms.SelectMultiple):
    """Searchable keyword box: pick keywords already used anywhere, or type a new one and press Enter."""

    def __init__(self, attrs=None):
        base = {"data-keyword-tags": "1", "class": "keyword-tags"}
        base.update(attrs or {})
        super().__init__(attrs=base)

    def get_context(self, name, value, attrs):
        from .models import SeoKeyword

        selected = [str(v) for v in (value or []) if str(v).strip()]
        known = list(SeoKeyword.objects.values_list("name", flat=True))
        lower = {k.lower() for k in known}
        self.choices = [(k, k) for k in known] + [(v, v) for v in selected if v.lower() not in lower]
        return super().get_context(name, selected, attrs)

    class Media:
        js = ADMIN_SELECT2_JS + ("admin/js/wara-tags.js",)
        css = {"screen": ADMIN_SELECT2_CSS}


class FaqEditor(forms.Textarea):
    """Question / answer rows in the admin. The rows are written back into this
    textarea as  Q: … / A: …  lines, so the form still works without JavaScript."""

    def __init__(self, attrs=None):
        base = {"data-faq-editor": "1", "rows": 8, "class": "form-control"}
        base.update(attrs or {})
        super().__init__(attrs=base)

    class Media:
        js = ("admin/js/wara-faq.js",)
