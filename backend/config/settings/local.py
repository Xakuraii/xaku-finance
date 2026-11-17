"""Local development settings."""

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Dev-only convenience; never enabled in production.
INTERNAL_IPS = ["127.0.0.1"]
