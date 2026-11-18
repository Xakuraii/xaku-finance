"""Local development settings."""

import os

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Console by default. Set EMAIL_BACKEND to SMTP and EMAIL_HOST/PORT to use Mailpit.
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")

# Dev-only convenience; never enabled in production.
INTERNAL_IPS = ["127.0.0.1"]
