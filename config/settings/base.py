
# ruff: noqa: ERA001, E501
"""Base settings to build other settings files upon."""

import os
from pathlib import Path


# ==============================================================================
# BASE DIRECTORIES
# ==============================================================================

BASE_DIR = Path(__file__).resolve(strict=True).parent.parent.parent

APPS_DIR = BASE_DIR / "rizz"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"
MEDIA_DIR = BASE_DIR / "media"


# ==============================================================================
# ENVIRONMENT VARIABLES
# ==============================================================================

def env(name, default=None):
    """Return an environment variable or its default."""
    return os.environ.get(name, default)


def env_bool(name, default=False):
    """Convert an environment variable to a boolean."""
    value = env(name)

    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name, default=None):
    """Return a comma-separated environment variable as a list."""
    value = env(name)

    if value is None:
        return list(default or [])

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def read_env(path):
    """Load environment variables from a .env file."""
    if not path.is_file():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)

        os.environ.setdefault(
            name.strip(),
            value.strip().strip("\"'"),
        )


READ_DOT_ENV_FILE = env_bool(
    "DJANGO_READ_DOT_ENV_FILE",
    default=False,
)

if READ_DOT_ENV_FILE:
    read_env(BASE_DIR / ".env")


# ==============================================================================
# GENERAL
# ==============================================================================

DEBUG = env_bool("DJANGO_DEBUG", default=False)

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="django-insecure-local-development-key-change-before-deployment",
)

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "0.0.0.0"],
)

TIME_ZONE = "Asia/Dhaka"

LANGUAGE_CODE = "en"

# English is served at "/", Bangla at "/bn/" (see config/urls.py).
LANGUAGES = [
    ("en", "English"),
    ("bn", "বাংলা"),
]

USE_I18N = True

USE_TZ = True

LOCALE_PATHS = [
    str(BASE_DIR / "locale"),
]

# django-modeltranslation: every translated model field gets an _en and a
# _bn column; an empty Bangla value falls back to English.
MODELTRANSLATION_DEFAULT_LANGUAGE = "en"
MODELTRANSLATION_LANGUAGES = ("en", "bn")
MODELTRANSLATION_FALLBACK_LANGUAGES = ("en",)

SITE_ID = 1


# ==============================================================================
# DATABASE
# ==============================================================================

# MySQL / MariaDB. Defaults match a local XAMPP install (database "warabd",
# user root, no password); set the DJANGO_DB_* variables on the server.
# utf8mb4 is required so Bangla text and emoji are stored correctly.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DJANGO_DB_NAME", "warabd"),
        "USER": env("DJANGO_DB_USER", "root"),
        "PASSWORD": env("DJANGO_DB_PASSWORD", ""),
        "HOST": env("DJANGO_DB_HOST", "127.0.0.1"),
        "PORT": env("DJANGO_DB_PORT", "3306"),
        "ATOMIC_REQUESTS": True,
        "OPTIONS": {
            "charset": "utf8mb4",
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_unicode_ci",
        },
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==============================================================================
# URLS
# ==============================================================================

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"


# ==============================================================================
# APPLICATIONS
# ==============================================================================

DJANGO_APPS = [
    "modeltranslation",  # must come before django.contrib.admin
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.admin",
    "django.contrib.sites",
    "django.contrib.sitemaps",
    "django.forms",
]

THIRD_PARTY_APPS = [
    "crispy_forms",
    "crispy_bootstrap5",
    "allauth",
    "allauth.account",
    "allauth.mfa",
    "allauth.socialaccount",
]

LOCAL_APPS = [
    "users",
    "web",
    "customers",
]

INSTALLED_APPS = (
    DJANGO_APPS
    + THIRD_PARTY_APPS
    + LOCAL_APPS
)


# ==============================================================================
# MIGRATIONS
# ==============================================================================

MIGRATION_MODULES = {
}


# ==============================================================================
# AUTHENTICATION
# ==============================================================================

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

AUTH_USER_MODEL = "users.User"

LOGIN_REDIRECT_URL = "users:redirect"

LOGIN_URL = "account_login"

LOGOUT_REDIRECT_URL = "/"


# ==============================================================================
# PASSWORDS
# ==============================================================================

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ==============================================================================
# MIDDLEWARE
# ==============================================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "customers.middleware.CustomerMiddleware",
]


# ==============================================================================
# STATIC FILES
# ==============================================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
    APPS_DIR / "static",
]

STATICFILES_DIRS = [
    directory
    for directory in STATICFILES_DIRS
    if directory.exists()
]

STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

if not DEBUG:
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": (
                "whitenoise.storage.CompressedManifestStaticFilesStorage"
            ),
        },
    }


# ==============================================================================
# MEDIA FILES
# ==============================================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = MEDIA_DIR


# ==============================================================================
# TEMPLATES
# ==============================================================================

TEMPLATE_DIRS = [
    TEMPLATES_DIR,
    APPS_DIR / "templates",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            str(directory)
            for directory in TEMPLATE_DIRS
            if directory.exists()
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": DEBUG,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "web.context_processors.cart_summary",
                "web.context_processors.site_settings",
                "web.context_processors.products_json",
                "web.context_processors.i18n_links",
                "customers.context_processors.customer",
            ],
        },
    },
]


# ==============================================================================
# DJANGO FORMS
# ==============================================================================

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

CRISPY_TEMPLATE_PACK = "bootstrap5"

CRISPY_ALLOWED_TEMPLATE_PACKS = [
    "bootstrap5",
]


# ==============================================================================
# FIXTURES
# ==============================================================================

FIXTURE_DIRS = (
    str(APPS_DIR / "fixtures"),
)


# ==============================================================================
# SECURITY
# ==============================================================================

SESSION_COOKIE_HTTPONLY = True

CSRF_COOKIE_HTTPONLY = True

X_FRAME_OPTIONS = "DENY"

SECURE_CONTENT_TYPE_NOSNIFF = True

SECURE_BROWSER_XSS_FILTER = True


# ==============================================================================
# EMAIL
# ==============================================================================

EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = env("DJANGO_EMAIL_HOST", default="localhost")

EMAIL_PORT = int(env("DJANGO_EMAIL_PORT", default="25") or "25")

EMAIL_HOST_USER = env("DJANGO_EMAIL_HOST_USER", default="")

EMAIL_HOST_PASSWORD = env("DJANGO_EMAIL_HOST_PASSWORD", default="")

EMAIL_USE_TLS = env_bool("DJANGO_EMAIL_USE_TLS", default=False)

EMAIL_USE_SSL = env_bool("DJANGO_EMAIL_USE_SSL", default=False)

EMAIL_TIMEOUT = 5

DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="WaRa BD <noreply@warabd.com>",
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL


# ==============================================================================
# ADMIN
# ==============================================================================

ADMIN_URL = "admin/"

ADMINS = [
    (
        "WaRa BD",
        env("DJANGO_ADMIN_EMAIL", default="admin@warabd.com"),
    ),
]

MANAGERS = ADMINS

DJANGO_ADMIN_FORCE_ALLAUTH = env_bool(
    "DJANGO_ADMIN_FORCE_ALLAUTH",
    default=False,
)


# ==============================================================================
# LOGGING
# ==============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": (
                "%(levelname)s %(asctime)s %(module)s "
                "%(process)d %(thread)d %(message)s"
            ),
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"],
    },
}


# ==============================================================================
# DJANGO ALLAUTH
# ==============================================================================

ACCOUNT_ALLOW_REGISTRATION = env_bool(
    "DJANGO_ACCOUNT_ALLOW_REGISTRATION",
    default=True,
)

# allauth 65 names (staff accounts log in with email + password).
ACCOUNT_LOGIN_METHODS = {"email"}

ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]

ACCOUNT_USER_MODEL_USERNAME_FIELD = None

ACCOUNT_EMAIL_VERIFICATION = "mandatory"

ACCOUNT_ADAPTER = "rizz.users.adapters.AccountAdapter"

ACCOUNT_FORMS = {
    "signup": "rizz.users.forms.UserSignupForm",
}

SOCIALACCOUNT_ADAPTER = "rizz.users.adapters.SocialAccountAdapter"

SOCIALACCOUNT_FORMS = {
    "signup": "rizz.users.forms.UserSocialSignupForm",
}


# ==============================================================================
# WARABD E-COMMERCE SETTINGS
# ==============================================================================

# Email notifications for new orders
ADMIN_ORDER_EMAILS = env_list(
    "DJANGO_ADMIN_ORDER_EMAILS",
    default=["admin@warabd.com"],
)

# Website URL used in order emails and notifications
SITE_URL = env(
    "DJANGO_SITE_URL",
    default="http://127.0.0.1:8000",
)

# Currency
DEFAULT_CURRENCY = "BDT"

# Currency display
CURRENCY_SYMBOL = "৳"

# Default country
DEFAULT_COUNTRY = "Bangladesh"

# Pagination
PRODUCTS_PER_PAGE = 12

ORDERS_PER_PAGE = 25


# ==============================================================================
# PROJECT-SPECIFIC SETTINGS
# ==============================================================================

# Add additional WaRa BD settings here.
