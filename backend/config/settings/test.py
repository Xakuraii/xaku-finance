"""Test settings: same engine as production, deterministic, no external services."""

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

PASSWORD_HASHERS = [
    # Fast hashing in tests only. Production uses Argon2id.
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# Fixed key so ciphertext tests are deterministic; cheap Argon2 so recovery-code tests stay fast.
TWO_FACTOR_ENCRYPTION_KEYS = {
    1: "vwA3dsSuqYew9Ox-6vva7D1mmWktd1kECym-lSxKT6E=",
}
TWO_FACTOR_CURRENT_KEY_VERSION = 1
RECOVERY_CODE_HASH_TIME_COST = 1
RECOVERY_CODE_HASH_MEMORY_COST = 16
RECOVERY_CODE_HASH_PARALLELISM = 1

CELERY_TASK_ALWAYS_EAGER = True
