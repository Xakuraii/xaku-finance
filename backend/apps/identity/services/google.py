"""Google sign-in.

The server verifies the ID token (signature, issuer, audience, expiry) and requires
``email_verified``. An existing password account is never linked implicitly: the user must sign in
with the password and link Google deliberately. See SECURITY.md 2 and ARCHITECTURE.md 6.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token

from apps.common.errors import DomainError
from apps.identity.models import SocialIdentity, User, normalize_email
from apps.identity.services.registration import provision_account

logger = logging.getLogger(__name__)


class GoogleAuthError(DomainError):
    status_code = 400


class GoogleInvalidToken(GoogleAuthError):
    code = "google_invalid_token"


class GoogleEmailUnverified(GoogleAuthError):
    code = "google_email_unverified"


class GoogleLinkRequired(GoogleAuthError):
    status_code = 409
    code = "google_link_required"


class GoogleNotConfigured(GoogleAuthError):
    status_code = 503
    code = "google_not_configured"


def _verify_id_token(raw_id_token: str) -> dict[str, Any]:
    """Verify against Google's public keys and our client id. Raises our error on failure."""
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        raise GoogleNotConfigured("Google sign-in is not configured.")

    try:
        claims = google_id_token.verify_oauth2_token(
            raw_id_token,
            google_requests.Request(),
            client_id,
        )
    except ValueError as exc:
        raise GoogleInvalidToken("The Google token is not valid.") from exc
    return claims


@transaction.atomic
def login_with_google(raw_id_token: str) -> User:
    """Return the linked user, create one, or demand explicit linking."""
    claims = _verify_id_token(raw_id_token)

    if claims.get("email_verified") is not True:
        raise GoogleEmailUnverified("Google has not verified this email address.")

    email = normalize_email(str(claims.get("email") or ""))
    subject = str(claims.get("sub") or "")
    if not email or not subject:
        raise GoogleInvalidToken("The Google token is missing required claims.")

    now = timezone.now()
    identity = (
        SocialIdentity.objects.select_for_update()
        .select_related("user")
        .filter(provider=SocialIdentity.PROVIDER_GOOGLE, subject=subject)
        .first()
    )
    if identity is not None:
        user = identity.user
        if not user.is_active:
            raise GoogleInvalidToken("This account is not active.")
        identity.email_at_provider = email
        identity.last_login_at = now
        identity.save(update_fields=["email_at_provider", "last_login_at"])
        user.last_login = now
        user.save(update_fields=["last_login"])
        return user

    existing = User.objects.select_for_update().filter(email=email).first()
    if existing is not None:
        raise GoogleLinkRequired(
            "Sign in with your password first, then link Google from your profile."
        )

    display_name = str(claims.get("name") or email.split("@")[0]).strip()[:80] or email
    user = provision_account(
        email=email,
        password=None,
        display_name=display_name,
        is_email_verified=True,
    )
    SocialIdentity.objects.create(
        user=user,
        provider=SocialIdentity.PROVIDER_GOOGLE,
        subject=subject,
        email_at_provider=email,
        last_login_at=now,
    )
    logger.info("Created account from Google identity")
    return user
