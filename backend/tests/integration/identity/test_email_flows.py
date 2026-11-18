"""Email verification and password reset flows.

Tokens are 32 random bytes, SHA-256 hashed at rest, single use, and expiring. Password reset
revokes every session because a reset is what you do when you believe the account is compromised.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.identity.models import IdentityToken, UserSession
from apps.identity.services.email_tokens import (
    AlreadyVerified,
    TokenAlreadyUsed,
    TokenExpired,
    TokenInvalid,
    send_verification,
    verify_email,
)
from apps.identity.services.passwords import request_password_reset, reset_password
from apps.identity.services.sessions import RequestMeta, issue_tokens

PASSWORD = "correct horse battery staple"
NEW_PASSWORD = "a much better passphrase"


def extract_token(body: str) -> str:
    marker = "token="
    start = body.index(marker) + len(marker)
    end = start
    while end < len(body) and (body[end].isalnum() or body[end] in "-_"):
        end += 1
    assert end > start, "email body did not contain a token"
    return body[start:end]


@pytest.mark.django_db
def test_verification_token_is_single_use(mailoutbox, user) -> None:
    send_verification(user)
    raw = extract_token(mailoutbox[0].body)

    assert verify_email(raw) is True
    with pytest.raises(TokenAlreadyUsed):
        verify_email(raw)


@pytest.mark.django_db
def test_verification_marks_the_user_verified(mailoutbox, user) -> None:
    raw = send_verification(user)

    assert verify_email(raw) is True
    user.refresh_from_db()
    assert user.is_email_verified is True
    assert user.email_verified_at is not None


@pytest.mark.django_db
def test_only_the_hash_is_stored(mailoutbox, user) -> None:
    raw = send_verification(user)

    token = IdentityToken.objects.get(user=user)
    assert len(token.token_hash) == 64
    assert raw not in token.token_hash
    assert token.purpose == "email_verification"


@pytest.mark.django_db
def test_expired_verification_token_is_rejected(mailoutbox, user) -> None:
    raw = send_verification(user)

    with freeze_time(timezone.now() + timedelta(hours=25)):
        with pytest.raises(TokenExpired):
            verify_email(raw)


@pytest.mark.django_db
def test_unknown_verification_token_is_rejected(user) -> None:
    with pytest.raises(TokenInvalid):
        verify_email("not-a-real-token")


@pytest.mark.django_db
def test_new_verification_token_supersedes_the_old_one(mailoutbox, user) -> None:
    first = send_verification(user)
    second = send_verification(user)

    with pytest.raises(TokenAlreadyUsed):
        verify_email(first)
    assert verify_email(second) is True


@pytest.mark.django_db
def test_resend_rejects_an_already_verified_account(mailoutbox, user) -> None:
    raw = send_verification(user)
    verify_email(raw)

    with pytest.raises(AlreadyVerified):
        send_verification(user)


@pytest.mark.django_db
def test_registration_sends_a_verification_email(api_client, mailoutbox) -> None:
    response = api_client.post(
        "/api/v1/auth/register/",
        {
            "email": "newcomer@example.com",
            "password": PASSWORD,
            "display_name": "Newcomer",
        },
        format="json",
    )
    assert response.status_code == 201
    assert len(mailoutbox) == 1
    assert "verify" in mailoutbox[0].subject.lower()
    assert extract_token(mailoutbox[0].body)


@pytest.mark.django_db
def test_verify_email_endpoint(mailoutbox, user) -> None:
    raw = send_verification(user)
    from rest_framework.test import APIClient

    response = APIClient().post("/api/v1/auth/verify-email/", {"token": raw}, format="json")
    assert response.status_code == 200
    assert response.json() == {"verified": True}

    replay = APIClient().post("/api/v1/auth/verify-email/", {"token": raw}, format="json")
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "token_already_used"


@pytest.mark.django_db
def test_resend_verification_requires_authentication(api_client) -> None:
    response = api_client.post("/api/v1/auth/verify-email/resend/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_resend_verification_endpoint(api_client, mailoutbox, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    response = api_client.post("/api/v1/auth/verify-email/resend/")
    assert response.status_code == 202
    assert response.json() == {"sent": True}
    assert len(mailoutbox) == 1


@pytest.mark.django_db
def test_password_reset_sends_only_for_existing_accounts(mailoutbox, user) -> None:
    assert request_password_reset("nobody@example.com") is False
    assert len(mailoutbox) == 0

    assert request_password_reset(user.email) is True
    assert len(mailoutbox) == 1
    assert "reset" in mailoutbox[0].subject.lower()


@pytest.mark.django_db
def test_password_reset_changes_password_and_revokes_sessions(mailoutbox, user) -> None:
    issue_tokens(user, request_meta=RequestMeta())
    send_verification(user)
    mailoutbox.clear()

    request_password_reset(user.email)
    raw = extract_token(mailoutbox[0].body)

    assert reset_password(raw, NEW_PASSWORD) is True
    user.refresh_from_db()
    assert user.check_password(NEW_PASSWORD)
    assert user.password_changed_at is not None
    assert not UserSession.objects.filter(user=user, revoked_at__isnull=True).exists()
    assert UserSession.objects.filter(user=user, revoked_reason="password_reset").exists()


@pytest.mark.django_db
def test_password_reset_token_is_single_use(mailoutbox, user) -> None:
    request_password_reset(user.email)
    raw = extract_token(mailoutbox[0].body)

    reset_password(raw, NEW_PASSWORD)
    with pytest.raises(TokenAlreadyUsed):
        reset_password(raw, "another very long passphrase")


@pytest.mark.django_db
def test_expired_password_reset_token_is_rejected(mailoutbox, user) -> None:
    request_password_reset(user.email)
    raw = extract_token(mailoutbox[0].body)

    with freeze_time(timezone.now() + timedelta(hours=2)):
        with pytest.raises(TokenExpired):
            reset_password(raw, NEW_PASSWORD)


@pytest.mark.django_db
def test_weak_password_does_not_consume_the_reset_token(mailoutbox, user) -> None:
    from apps.identity.services.registration import WeakPassword

    request_password_reset(user.email)
    raw = extract_token(mailoutbox[0].body)

    with pytest.raises(WeakPassword):
        reset_password(raw, "short")

    assert reset_password(raw, NEW_PASSWORD) is True


@pytest.mark.django_db
def test_password_reset_endpoints_do_not_reveal_accounts(api_client, mailoutbox, user) -> None:
    known = api_client.post("/api/v1/auth/password/forgot/", {"email": user.email}, format="json")
    unknown = api_client.post(
        "/api/v1/auth/password/forgot/", {"email": "nobody@example.com"}, format="json"
    )
    assert known.status_code == 202
    assert unknown.status_code == 202
    assert known.json() == unknown.json()

    raw = extract_token(mailoutbox[0].body)
    response = api_client.post(
        "/api/v1/auth/password/reset/",
        {"token": raw, "new_password": NEW_PASSWORD},
        format="json",
    )
    assert response.status_code == 200
    assert response.json() == {"reset": True}


@pytest.mark.django_db
def test_password_forgot_is_throttled_per_email(api_client) -> None:
    for _ in range(5):
        assert (
            api_client.post(
                "/api/v1/auth/password/forgot/",
                {"email": "target@example.com"},
                format="json",
            ).status_code
            == 202
        )
    blocked = api_client.post(
        "/api/v1/auth/password/forgot/", {"email": "target@example.com"}, format="json"
    )
    assert blocked.status_code == 429


@pytest.mark.django_db
def test_reset_token_cannot_verify_an_email(mailoutbox, user) -> None:
    request_password_reset(user.email)
    raw = extract_token(mailoutbox[0].body)

    with pytest.raises(TokenInvalid):
        verify_email(raw)


@pytest.mark.django_db
def test_tokens_are_never_logged(mailoutbox, caplog, user) -> None:
    caplog.set_level("DEBUG")
    raw = send_verification(user)
    assert raw not in caplog.text
    assert raw not in mailoutbox[0].subject


@pytest.mark.django_db
def test_unknown_user_token_is_not_reported_as_expired(user) -> None:
    with pytest.raises(TokenInvalid):
        reset_password("bogus", NEW_PASSWORD)
