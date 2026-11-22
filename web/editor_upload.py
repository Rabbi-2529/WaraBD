"""Picture upload for CKEditor (admin only): POST /admin/editor-upload/ with a file named "upload"."""

import os
import uuid

from django.contrib.admin.views.decorators import staff_member_required
from django.core.files.storage import default_storage
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST

MAX_BYTES = 5 * 1024 * 1024
ALLOWED = {"JPEG": ".jpg", "PNG": ".png", "GIF": ".gif", "WEBP": ".webp"}


def _error(message, status=400):
    return JsonResponse({"error": message}, status=status)


@require_POST
@staff_member_required
def editor_upload(request):
    upload = request.FILES.get("upload")
    if not upload:
        return _error("No file received.")
    if upload.size > MAX_BYTES:
        return _error("Picture is larger than 5 MB.")
    try:
        from PIL import Image

        image = Image.open(upload)
        image.verify()                      # real picture, not a renamed file
        kind = image.format
    except Exception:  # noqa: BLE001 — anything Pillow cannot read is refused
        return _error("Only JPG, PNG, GIF or WebP pictures can be added.")
    if kind not in ALLOWED:
        return _error("Only JPG, PNG, GIF or WebP pictures can be added.")
    upload.seek(0)
    now = timezone.localtime()
    name = os.path.join("editor", f"{now:%Y}", f"{now:%m}", uuid.uuid4().hex + ALLOWED[kind]).replace("\\", "/")
    saved = default_storage.save(name, upload)
    return JsonResponse({"url": default_storage.url(saved)})
