"""Django settings shared by every environment."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REPO_DIR = BASE_DIR.parent

load_dotenv(REPO_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-development-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", False)
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "django_filters",
    "rest_framework",
    "drf_spectacular",
    "apps.common",
    "apps.identity",
    "apps.workspaces",
    "apps.accounts",
    "apps.ledger",
    "apps.categories",
    "apps.tags",
    "apps.transactions",
    "apps.budgets",
    "apps.imports",
    "apps.savings",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.common.middleware.RequestIdMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": dj_database_url.config(
        default=os.getenv(
            "DATABASE_URL",
            "postgres://xaku:xaku_dev_password@127.0.0.1:55432/xaku",
        ),
        conn_max_age=60,
        conn_health_checks=True,
    )
}
# Fail fast when the database is unreachable instead of blocking a request for minutes.
DATABASES["default"].setdefault("OPTIONS", {})["connect_timeout"] = 5

# The custom user model must be set before the first migration; it is now the only user model.
AUTH_USER_MODEL = "identity.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Every request runs in a transaction unless a view opts out. Financial writes additionally
# open their own atomic block in the service layer.
ATOMIC_REQUESTS = True

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_THROTTLE_CLASSES": [],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "300/min",
        "login": "10/min",
        "register": "5/hour",
        "password_reset": "20/hour",
        "password_reset_email": "5/hour",
        "email_verification": "5/hour",
        "two_factor": "10/min",
    },
    "EXCEPTION_HANDLER": "apps.common.errors.exception_handler",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": os.getenv("JWT_SIGNING_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_CLAIM": "sub",
    "TOKEN_TYPE_CLAIM": "typ",
}

# HMAC key for session IP hashes. Rotating it makes old hashes unlinkable, which is acceptable.
IP_HASH_KEY = os.getenv("IP_HASH_KEY", SECRET_KEY)

# Token lifetimes from SECURITY.md. Verification is 24 hours; reset is 1 hour.
EMAIL_VERIFICATION_TTL = timedelta(hours=24)
PASSWORD_RESET_TTL = timedelta(hours=1)

# Links in emails point at the SPA, never at the API host.
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "XakuFinance <no-reply@xakufinance.local>")
EMAIL_HOST = os.getenv("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)

# Google sign-in is optional. An empty client id disables the endpoint with a clear error.
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")


def _parse_two_factor_keys(raw: str) -> dict[int, str]:
    """Parse ``version:key`` pairs so an old key can still decrypt during rotation."""
    keys: dict[int, str] = {}
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        version, _, key = item.partition(":")
        if not version or not key:
            raise ValueError("TWO_FACTOR_ENCRYPTION_KEYS must look like 1:key,2:key")
        keys[int(version)] = key.strip()
    return keys


def _derived_two_factor_key() -> str:
    """Development fallback so a fresh checkout can enroll without extra setup.

    Production refuses to start without an explicit key (see production.py).
    """
    import base64
    import hashlib

    digest = hashlib.sha256(f"two-factor:{SECRET_KEY}".encode()).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii")


_two_factor_raw = os.getenv("TWO_FACTOR_ENCRYPTION_KEYS", "").strip()
if not _two_factor_raw:
    single_key = os.getenv("TWO_FACTOR_ENCRYPTION_KEY", "").strip()
    _two_factor_raw = f"1:{single_key}" if single_key else f"1:{_derived_two_factor_key()}"

TWO_FACTOR_ENCRYPTION_KEYS = _parse_two_factor_keys(_two_factor_raw)
TWO_FACTOR_CURRENT_KEY_VERSION = int(os.getenv("TWO_FACTOR_KEY_VERSION", "1"))
if TWO_FACTOR_CURRENT_KEY_VERSION not in TWO_FACTOR_ENCRYPTION_KEYS:
    raise ValueError("TWO_FACTOR_KEY_VERSION must name a configured encryption key.")

TWO_FACTOR_ISSUER = os.getenv("TWO_FACTOR_ISSUER", "XakuFinance")
TWO_FACTOR_ALGORITHM = "SHA1"
TWO_FACTOR_DIGITS = 6
TWO_FACTOR_PERIOD_SECONDS = 30
TWO_FACTOR_MAX_FAILURES = 5
TWO_FACTOR_LOCK_WINDOW = timedelta(minutes=10)
TWO_FACTOR_LOCK_DURATION = timedelta(minutes=15)
RECOVERY_CODE_COUNT = 10
RECOVERY_CODE_BYTES = 10

# A challenge bridges a correct password and a 2FA code; it is not a session.
MFA_CHALLENGE_TTL = timedelta(minutes=5)

# Sensitive actions (enrolling 2FA, regenerating recovery codes) need a recent password check.
REAUTH_WINDOW = timedelta(minutes=10)

# Recovery codes are Argon2id-hashed. Tests lower these so the suite stays fast.
RECOVERY_CODE_HASH_TIME_COST = int(os.getenv("RECOVERY_CODE_HASH_TIME_COST", "3"))
RECOVERY_CODE_HASH_MEMORY_COST = int(os.getenv("RECOVERY_CODE_HASH_MEMORY_COST", "65536"))
RECOVERY_CODE_HASH_PARALLELISM = int(os.getenv("RECOVERY_CODE_HASH_PARALLELISM", "4"))

SPECTACULAR_SETTINGS = {
    "TITLE": "XakuFinance API",
    "DESCRIPTION": "Personal finance management API. Amounts are decimal strings.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": "/api/v1",
    "ENUM_NAME_OVERRIDES": {},
}

# CORS: never wildcard. Origins come from the environment.
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/.*$"

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "http://localhost:5173")

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # the SPA reads the double-submit token
CSRF_COOKIE_SAMESITE = "Lax"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "json"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
