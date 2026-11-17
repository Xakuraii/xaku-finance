"""Password reset.

Requesting a reset never reveals whether an account exists. Completing one revokes every session:
a reset usually follows suspicion of compromise.
"""

from __future__ import annotations

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.identity.models import IdentityToken, User, normalize_email
from apps.identity.services.email_tokens import (
    consume_token,
    frontend_link,
    issue_token,
    send_identity_email,
)
from apps.identity.services.registration import validate_password_strength
from apps.identity.services.sessions import revoke_all_sessions


@transaction.atomic
def request_password_reset(email: str, *, requested_ip_hash: str | None = None) -> bool:
    """Issue a 1-hour reset token if the account exists. Returns whether mail was queued."""
    normalized = normalize_email(email)
    user = User.objects.filter(email=normalized, is_active=True).first()
    if user is None:
        return False

    raw_token = issue_token(
        user=user,
        purpose=IdentityToken.PURPOSE_PASSWORD_RESET,
        ttl=settings.PASSWORD_RESET_TTL,
        requested_ip_hash=requested_ip_hash,
    )
    send_identity_email(
        subject="Reset your XakuFinance password",
        template="identity/emails/password_reset.txt",
        context={
            "display_name": getattr(getattr(user, "profile", None), "display_name", ""),
            "link": frontend_link("/reset-password", raw_token),
            "expires_hours": int(settings.PASSWORD_RESET_TTL.total_seconds() // 3600),
        },
        to=user.email,
    )
    return True


@transaction.atomic
def reset_password(raw_token: str, new_password: str) -> bool:
    """Consume the token, set the new password, and revoke every session.

    Password policy is checked after the token is read but before it is committed as used, so a
    weak password does not burn the link.
    """
    token = consume_token(raw_token, purpose=IdentityToken.PURPOSE_PASSWORD_RESET)
    user = token.user
    validate_password_strength(new_password, user=user)

    now = timezone.now()
    user.set_password(new_password)
    user.password_changed_at = now
    user.failed_login_count = 0
    user.last_failed_login_at = None
    user.locked_until = None
    user.save(
        update_fields=[
            "password",
            "password_changed_at",
            "failed_login_count",
            "last_failed_login_at",
            "locked_until",
        ]
    )
    revoke_all_sessions(user=user, reason="password_reset")
    return True
