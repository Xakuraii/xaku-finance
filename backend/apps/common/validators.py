"""Shared validators for user-supplied metadata."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError


def validate_iana_timezone(value: str) -> None:
    """Reject anything the stdlib cannot resolve as an IANA zone name."""
    try:
        ZoneInfo(value)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as exc:
        raise ValidationError(
            "%(value)s is not a known IANA timezone.",
            code="invalid_timezone",
            params={"value": value},
        ) from exc
