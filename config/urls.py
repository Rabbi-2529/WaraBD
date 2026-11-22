"""URL configuration for WaRa BD."""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from web.sitemaps import SITEMAPS
from web.editor_upload import editor_upload
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


# Serve uploaded media files during development.
# ------------------------------------------------------------------------------
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
