"""URL configuration for WaRa BD."""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, re_path
from django.views.decorators.cache import cache_control
from django.views.static import serve

from web.sitemaps import SITEMAPS
from web.editor_upload import editor_upload
from web.translate import translate_view
from web.views import robots_txt


urlpatterns = [
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("robots.txt", robots_txt, name="robots_txt"),
    path("admin/editor-upload/", editor_upload, name="editor_upload"),  # CKEditor pictures (staff only)
    path("admin/translate/", translate_view, name="admin_translate"),  # English -> বাংলা (staff only)
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
]

# Storefront in two languages: English at "/" (no prefix, so existing links
# keep working) and Bangla at "/bn/...".
urlpatterns += i18n_patterns(
    path("account/", include("customers.urls")),  # customer phone login + My Account
    path("", include("web.urls")),
    prefix_default_language=False,
)


# 🟢 Debug Toolbar: local development only (DISABLED)
# ------------------------------------------------------------------------------
# if settings.DEBUG:
#     import debug_toolbar
#
#     urlpatterns += [
#         path("__debug__/", include(debug_toolbar.urls)),
#     ]


# Uploaded files (logo, product pictures, editor images, share images).
# ------------------------------------------------------------------------------
def media_urlpatterns():
    """On cPanel / Passenger nothing else serves the media folder, so Django does it
    (DJANGO_SERVE_MEDIA=False turns this off when the web server serves /media/ itself)."""
    if settings.DEBUG:
        return static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    prefix = str(settings.MEDIA_URL or "")
    if not getattr(settings, "SERVE_MEDIA", False) or not prefix.startswith("/") or prefix == "/":
        return []
    view = cache_control(public=True, max_age=60 * 60 * 24 * 7)(serve)  # uploads get new names, so a week is safe
    return [re_path(r"^%s(?P<path>.+)$" % prefix.lstrip("/"), view, {"document_root": settings.MEDIA_ROOT})]


urlpatterns = media_urlpatterns() + urlpatterns
