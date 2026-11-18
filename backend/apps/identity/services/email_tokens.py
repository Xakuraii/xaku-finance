"""Single-use, expiring, hashed tokens for email verification and password reset.

The database never sees the raw token: it stores a SHA-256 hash of 32 random bytes. Comparing
hashes also means a leaked database cannot be used to verify accounts or reset passwords.
"""

from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone

from apps.common.errors import DomainError
from apps.identity.models import IdentityToken, User

logger = logging.getLogger(__name__)

TOKEN_BYTES = 32


class IdentityTokenError(DomainError):
    status_code = 400
    code = "invalid_token"


class TokenInvalid(IdentityTokenError):
    pass


class TokenExpired(IdentityTokenError):
    code = "token_expired"


class TokenAlreadyUsed(IdentityTokenError):
    status_code = 409
    code = "token_already_used"


class AlreadyVerified(DomainError):
    status_code = 400
    code = "already_verified"


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def issue_token(
    *,
    user: User,
    purpose: str,
    ttl: timedelta,
    requested_ip_hash: str | None = None,
) -> str:
    """Create a token, invalidate unused predecessors, and return the raw value once."""
    raw_token = secrets.token_urlsafe(TOKEN_BYTES)
    now = timezone.now()
    IdentityToken.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(
        used_at=now
    )
    IdentityToken.objects.create(
        user=user,
        token_hash=hash_token(raw_token),
        purpose=purpose,
        expires_at=now + ttl,
        requested_ip_hash=requested_ip_hash,
    )
    return raw_token


def consume_token(raw_token: str, *, purpose: str) -> IdentityToken:
    """Validate and mark a token used. Must run inside a transaction.

    The caller decides what the token authorizes; this function only enforces the token's own
    invariants so a replay is always reported as such, never silently accepted.
    """
    if not isinstance(raw_token, str) or not raw_token:
        raise TokenInvalid("This link is not valid.")

    token = (
        IdentityToken.objects.select_for_update()
        .select_related("user")
        .filter(token_hash=hash_token(raw_token), purpose=purpose)
        .first()
    )
    if token is None:
        raise TokenInvalid("This link is not valid.")
    if token.used_at is not None:
        raise TokenAlreadyUsed("This link has already been used.")
    if token.expires_at <= timezone.now():
        raise TokenExpired("This link has expired.")

    token.used_at = timezone.now()
    token.save(update_fields=["used_at"])
    return token


def send_identity_email(
    *, subject: str, template: str, context: dict[str, object], to: str
) -> None:
    """Send without leaking the token into logs and without failing the caller's request.

    A mail outage must not roll back a completed registration or reveal whether an account
    exists during password reset.
    """
    body = render_to_string(template, context)
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
    except Exception:  # pragma: no cover - delivery failures depend on the provider
        logger.exception("Failed to send %s email", subject)


def frontend_link(path: str, raw_token: str) -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    return f"{base}{path}?token={raw_token}"


@transaction.atomic
def send_verification(user: User, *, requested_ip_hash: str | None = None) -> str:
    """Issue a 24-hour verification token and email its link. Returns the raw token."""
    if User.objects.filter(pk=user.pk, is_email_verified=True).exists():
        raise AlreadyVerified("This email is already verified.")

    raw_token = issue_token(
        user=user,
        purpose=IdentityToken.PURPOSE_EMAIL_VERIFICATION,
        ttl=settings.EMAIL_VERIFICATION_TTL,
        requested_ip_hash=requested_ip_hash,
    )
    send_identity_email(
        subject="Verify your XakuFinance email",
        template="identity/emails/verify_email.txt",
        context={
            "display_name": getattr(getattr(user, "profile", None), "display_name", ""),
            "link": frontend_link("/verify-email", raw_token),
            "expires_hours": int(settings.EMAIL_VERIFICATION_TTL.total_seconds() // 3600),
        },
        to=user.email,
    )
    return raw_token


@transaction.atomic
def verify_email(raw_token: str) -> bool:
    """Mark the account verified. A second use of the same token fails loudly."""
    token = consume_token(raw_token, purpose=IdentityToken.PURPOSE_EMAIL_VERIFICATION)
    user = token.user
    user.is_email_verified = True
    user.email_verified_at = timezone.now()
    user.save(update_fields=["is_email_verified", "email_verified_at"])
    return True
