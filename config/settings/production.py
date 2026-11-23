
# ruff: noqa: E501
"""Production settings for WaRa BD."""

from .base import *  # noqa: F401,F403 — every base setting (apps, URLs, middleware …); changed below
from .base import (
    BASE_DIR,
    DATABASES,
    env,
    env_bool,
    env_list,
)


# ==============================================================================
# GENERAL
# ==============================================================================

DEBUG = False

SECRET_KEY = env("DJANGO_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError(
        "DJANGO_SECRET_KEY must be configured in production."
    )

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=["warabd.com", "www.warabd.com"],
)


# ==============================================================================
# DATABASE
# ==============================================================================

CONN_MAX_AGE = env("CONN_MAX_AGE", default="60") or "60"

DATABASES["default"]["CONN_MAX_AGE"] = int(CONN_MAX_AGE)


# ==============================================================================
# REDIS CACHE
# ==============================================================================

# Redis only when REDIS_URL is set (e.g. redis://127.0.0.1:6379/1). Shared cPanel
# hosting usually has no Redis: then each app process keeps its own small
# in-memory cache (sessions and SMS limits live in the database, not here).
REDIS_URL = env("REDIS_URL", default="")

if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": REDIS_URL,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "IGNORE_EXCEPTIONS": True,
            },
        },
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "warabd",
        },
    }


# ==============================================================================
# SECURITY
# ==============================================================================

SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SECURE_SSL_REDIRECT = env_bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    default=True,
)

SESSION_COOKIE_SECURE = True

SESSION_COOKIE_HTTPONLY = True

SESSION_COOKIE_NAME = "__Secure-sessionid"

CSRF_COOKIE_SECURE = True

CSRF_COOKIE_HTTPONLY = True

CSRF_COOKIE_NAME = "__Secure-csrftoken"

SECURE_HSTS_SECONDS = int(
    env("DJANGO_SECURE_HSTS_SECONDS", default="60") or "60"
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=True,
)

SECURE_HSTS_PRELOAD = env_bool(
    "DJANGO_SECURE_HSTS_PRELOAD",
    default=True,
)

SECURE_CONTENT_TYPE_NOSNIFF = env_bool(
    "DJANGO_SECURE_CONTENT_TYPE_NOSNIFF",
    default=True,
)

X_FRAME_OPTIONS = "DENY"


# ==============================================================================
# STATIC FILES AND MEDIA
# ==============================================================================

# WhiteNoiseMiddleware should already be configured in base.py.
# Do not insert it a second time.

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # WhiteNoise hashed + compressed files; tolerates theme CSS that
        # points at pictures the theme never shipped (config/storage.py).
        "BACKEND": "config.storage.ForgivingManifestStaticFilesStorage",
    },
}

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = BASE_DIR / "media"

MEDIA_URL = "/media/"

# cPanel / Passenger: Apache does not serve the app's media folder, so without this
# every uploaded file (logo, product pictures …) is a 404 on the live site.
SERVE_MEDIA = env_bool("DJANGO_SERVE_MEDIA", default=True)


# ==============================================================================
# EMAIL / SMTP
# ==============================================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = env(
    "DJANGO_EMAIL_HOST",
    default="smtp.gmail.com",
)

EMAIL_PORT = int(
    env("DJANGO_EMAIL_PORT", default="587") or "587"
)

EMAIL_HOST_USER = env(
    "DJANGO_EMAIL_HOST_USER",
    default="",
)

EMAIL_HOST_PASSWORD = env(
    "DJANGO_EMAIL_HOST_PASSWORD",
    default="",
)

EMAIL_USE_TLS = env_bool(
    "DJANGO_EMAIL_USE_TLS",
    default=True,
)

EMAIL_USE_SSL = env_bool(
    "DJANGO_EMAIL_USE_SSL",
    default=False,
)

EMAIL_TIMEOUT = 10

DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="WaRa BD <noreply@warabd.com>",
)

SERVER_EMAIL = env(
    "DJANGO_SERVER_EMAIL",
    default=DEFAULT_FROM_EMAIL,
)

EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX",
    default="[WaRa BD] ",
)


# ==============================================================================
# ADMIN
# ==============================================================================

ADMIN_URL = env(
    "DJANGO_ADMIN_URL",
    default="admin/",
)

ADMINS = [
    (
        "WaRa BD",
        env(
            "DJANGO_ADMIN_EMAIL",
            default="admin@warabd.com",
        ),
    ),
]

MANAGERS = ADMINS


# ==============================================================================
# ANYMAIL
# ==============================================================================

# SMTP is configured above.
# Add Anymail only if you switch to a supported provider.

ANYMAIL = {}


# ==============================================================================
# LOGGING
# ==============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "formatters": {
        "verbose": {
            "format": (
                "%(levelname)s %(asctime)s %(module)s "
                "%(process)d %(thread)d %(message)s"
            ),
        },
    },
    "handlers": {
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
        },
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
    "loggers": {
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": True,
        },
        "django.security.DisallowedHost": {
            "level": "ERROR",
            "handlers": ["console", "mail_admins"],
            "propagate": True,
        },
    },
}


# ==============================================================================
# PRODUCTION APPLICATION SETTINGS
# ==============================================================================

SITE_URL = env(
    "DJANGO_SITE_URL",
    default="https://warabd.com",
)

DEFAULT_CURRENCY = "BDT"

CURRENCY_SYMBOL = "৳"

DEFAULT_COUNTRY = "Bangladesh"

PRODUCTS_PER_PAGE = 12

ORDERS_PER_PAGE = 25
