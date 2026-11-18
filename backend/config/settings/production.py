"""Production settings. Refuse to start with unsafe defaults."""

import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403

DEBUG = False

if SECRET_KEY == "insecure-development-key-change-me":  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production.")
if not os.getenv("JWT_SIGNING_KEY"):  # noqa: F405
    raise ImproperlyConfigured("JWT_SIGNING_KEY must be set in production.")
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["*"]:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS must list real hosts in production.")
if FRONTEND_BASE_URL.startswith(("http://localhost", "http://127.0.0.1")):  # noqa: F405
    raise ImproperlyConfigured("FRONTEND_BASE_URL must be the public SPA origin in production.")
if not (
    os.getenv("TWO_FACTOR_ENCRYPTION_KEYS") or os.getenv("TWO_FACTOR_ENCRYPTION_KEY")
):
    raise ImproperlyConfigured("TWO_FACTOR_ENCRYPTION_KEY must be set in production.")

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
