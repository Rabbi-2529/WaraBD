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
