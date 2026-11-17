"""Throttles that key on something other than the client address."""

from __future__ import annotations

import hashlib

from rest_framework.throttling import SimpleRateThrottle


class PasswordResetEmailThrottle(SimpleRateThrottle):
    """Five reset requests per hour per email address, regardless of source IP.

    The key is hashed so the cache never stores a plain email address.
    """

    scope = "password_reset_email"

    def get_cache_key(self, request, view):  # type: ignore[no-untyped-def]
        email = ""
        data = getattr(request, "data", None)
        if isinstance(data, dict):
            email = str(data.get("email") or "").strip().lower()
        ident = email or self.get_ident(request)
        digest = hashlib.sha256(ident.encode("utf-8")).hexdigest()
        return self.cache_format % {"scope": self.scope, "ident": digest}
