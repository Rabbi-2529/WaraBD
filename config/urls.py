"""URL configuration for WaRa BD."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from web.sitemaps import SITEMAPS


urlpatterns = [
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("", include("web.urls")),
]


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
