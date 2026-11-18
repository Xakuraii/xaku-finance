"""TOTP 2FA: enrollment, challenge verification, replay protection, and recovery codes."""

import hashlib
from datetime import timedelta

import pyotp
import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.identity.api.cookies import REFRESH_COOKIE
from apps.identity.models import MFAChallenge, RecoveryCode, TwoFactorConfig
from apps.identity.services import two_factor
from apps.identity.services.sessions import (
    RequestMeta,
    issue_tokens,
)
from apps.identity.services.two_factor import (
    AlreadyEnabled,
    ChallengeInvalid,
    InvalidCode,
    InvalidPassword,
    NotEnabled,
    TooManyAttempts,
    begin_enrollment,
    confirm_enrollment,
    create_challenge,
    disable,
    regenerate_recovery_codes,
    verify_challenge,
)

PASSWORD = "correct horse battery staple"


def _secret(user) -> str:
    return two_factor._decrypt_secret(TwoFactorConfig.objects.get(user=user))


def current_code(user, *, offset: int = 0) -> str:
    config = TwoFactorConfig.objects.get(user=user)
    totp = pyotp.TOTP(
        _secret(user),
        digits=config.digits,
        interval=config.period_seconds,
        digest=hashlib.sha1,
    )
    return totp.at(timezone.now() + timedelta(seconds=offset))


def _challenge(user) -> str:
    return create_challenge(user).token


@pytest.fixture
def enrolled(user):
    """A user with 2FA enabled and ten unused recovery codes."""
    begin_enrollment(user)
    codes = confirm_enrollment(user, current_code(user))
    return user, codes


def test_enrollment_encrypts_the_secret_at_rest(user) -> None:
    enrollment = begin_enrollment(user)

    config = TwoFactorConfig.objects.get(user=user)
    stored = bytes(config.secret_ciphertext)
    assert enrollment.secret.encode("ascii") not in stored
    assert config.secret_ciphertext != enrollment.secret.encode("ascii")
    assert config.is_enabled is False
    assert two_factor._decrypt_secret(config) == enrollment.secret


def test_enrollment_returns_a_scannable_uri_and_svg(user) -> None:
    enrollment = begin_enrollment(user)

    assert enrollment.otpauth_uri.startswith("otpauth://totp/")
    assert enrollment.secret in enrollment.otpauth_uri
    assert enrollment.qr_svg.startswith("<?xml") or "svg" in enrollment.qr_svg


@pytest.mark.django_db
def test_confirm_enables_and_returns_ten_recovery_codes(user) -> None:
    begin_enrollment(user)
    codes = confirm_enrollment(user, current_code(user))

    config = TwoFactorConfig.objects.get(user=user)
    assert config.is_enabled is True
    assert config.confirmed_at is not None
    assert len(codes) == 10
    assert len(set(codes)) == 10
    assert RecoveryCode.objects.filter(user=user, used_at__isnull=True).count() == 10


@pytest.mark.django_db
def test_recovery_codes_are_argon2id_hashes(enrolled) -> None:
    user, codes = enrolled

    stored = RecoveryCode.objects.filter(user=user).first()
    assert stored is not None
    assert stored.code_hash.startswith("$argon2id$")
    for code in codes:
        assert code not in stored.code_hash


@pytest.mark.django_db
def test_a_wrong_confirmation_code_does_not_enable(user) -> None:
    begin_enrollment(user)

    with pytest.raises(InvalidCode):
        confirm_enrollment(user, "000000")

    assert TwoFactorConfig.objects.get(user=user).is_enabled is False


@pytest.mark.django_db
def test_confirm_requires_an_enrollment(user) -> None:
    with pytest.raises(NotEnabled):
        confirm_enrollment(user, "123456")


@pytest.mark.django_db
def test_begin_enrollment_refuses_an_enabled_account(enrolled) -> None:
    user, _ = enrolled

    with pytest.raises(AlreadyEnabled):
        begin_enrollment(user)


@pytest.mark.django_db
def test_challenge_verification_issues_a_session(enrolled) -> None:
    user, _ = enrolled

    tokens = verify_challenge(
        _challenge(user), current_code(user, offset=30), request_meta=RequestMeta()
    )

    assert tokens.access
    assert tokens.refresh


@pytest.mark.django_db
def test_totp_replay_is_rejected(enrolled) -> None:
    user, _ = enrolled
    code = current_code(user, offset=30)
    verify_challenge(_challenge(user), code, request_meta=RequestMeta())

    with pytest.raises(InvalidCode):
        verify_challenge(_challenge(user), code, request_meta=RequestMeta())


@pytest.mark.django_db
def test_recovery_code_is_single_use(enrolled) -> None:
    user, codes = enrolled

    assert verify_challenge(_challenge(user), codes[0], request_meta=RequestMeta()).access
    assert (
        RecoveryCode.objects.get(user=user, used_at__isnull=False).used_at is not None
    )

    with pytest.raises(InvalidCode):
        verify_challenge(_challenge(user), codes[0], request_meta=RequestMeta())


@pytest.mark.django_db
def test_recovery_codes_are_case_and_dash_insensitive(enrolled) -> None:
    user, codes = enrolled
    mangled = codes[1].lower().replace("-", " ")

    tokens = verify_challenge(_challenge(user), mangled, request_meta=RequestMeta())

    assert tokens.access


@pytest.mark.django_db
def test_five_failures_lock_verification(enrolled) -> None:
    user, _ = enrolled
    now = timezone.now()

    with freeze_time(now):
        for _ in range(5):
            with pytest.raises(InvalidCode):
                verify_challenge(_challenge(user), "000000", request_meta=RequestMeta())

        with pytest.raises(TooManyAttempts):
            verify_challenge(_challenge(user), "000000", request_meta=RequestMeta())

    config = TwoFactorConfig.objects.get(user=user)
    assert config.locked_until is not None
    assert config.locked_until > now


@pytest.mark.django_db
def test_lock_expires_after_fifteen_minutes(enrolled) -> None:
    user, codes = enrolled
    now = timezone.now()
    with freeze_time(now):
        for _ in range(5):
            with pytest.raises(InvalidCode):
                verify_challenge(_challenge(user), "000000", request_meta=RequestMeta())

    with freeze_time(now + timedelta(minutes=16)):
        tokens = verify_challenge(_challenge(user), codes[2], request_meta=RequestMeta())

    assert tokens.access


@pytest.mark.django_db
def test_challenge_is_single_use(enrolled) -> None:
    user, codes = enrolled
    raw = _challenge(user)
    verify_challenge(raw, codes[0], request_meta=RequestMeta())

    with pytest.raises(ChallengeInvalid):
        verify_challenge(raw, codes[1], request_meta=RequestMeta())


@pytest.mark.django_db
def test_challenge_expires_after_five_minutes(enrolled) -> None:
    user, codes = enrolled
    now = timezone.now()

    with freeze_time(now):
        raw = _challenge(user)

    with freeze_time(now + timedelta(minutes=6)):
        with pytest.raises(ChallengeInvalid):
            verify_challenge(raw, codes[0], request_meta=RequestMeta())


@pytest.mark.django_db
def test_unknown_challenge_is_rejected(user) -> None:
    with pytest.raises(ChallengeInvalid):
        verify_challenge("not-a-challenge", "123456", request_meta=RequestMeta())


@pytest.mark.django_db
def test_disable_requires_password_and_code(enrolled, mailoutbox) -> None:
    user, codes = enrolled
    begin_enrollment_codes = len(mailoutbox)

    with pytest.raises(InvalidPassword):
        disable(user, password="wrong password", code=codes[0])

    with pytest.raises(InvalidCode):
        disable(user, password=PASSWORD, code="000000")

    disable(user, password=PASSWORD, code=codes[0])

    config = TwoFactorConfig.objects.get(user=user)
    assert config.is_enabled is False
    assert config.disabled_at is not None
    assert not RecoveryCode.objects.filter(user=user).exists()
    assert len(mailoutbox) == begin_enrollment_codes + 1
    assert "two-factor" in mailoutbox[-1].subject.lower()


@pytest.mark.django_db
def test_disable_is_idempotently_reported_as_not_enabled(user) -> None:
    with pytest.raises(NotEnabled):
        disable(user, password=PASSWORD, code="123456")


@pytest.mark.django_db
def test_regenerating_recovery_codes_invalidates_the_old_batch(enrolled) -> None:
    user, old_codes = enrolled

    new_codes = regenerate_recovery_codes(
        user, password=PASSWORD, code=current_code(user, offset=30)
    )

    assert set(new_codes).isdisjoint(old_codes)
    assert RecoveryCode.objects.filter(user=user).count() == 10

    with pytest.raises(InvalidCode):
        verify_challenge(_challenge(user), old_codes[0], request_meta=RequestMeta())

    assert verify_challenge(
        _challenge(user), new_codes[0], request_meta=RequestMeta()
    ).access


@pytest.mark.django_db
def test_regeneration_checks_the_password(enrolled) -> None:
    user, _ = enrolled

    with pytest.raises(InvalidPassword):
        regenerate_recovery_codes(user, password="nope", code="123456")


@pytest.mark.django_db
def test_login_with_two_factor_returns_a_challenge(
    api_client, enrolled
) -> None:
    user, _ = enrolled

    response = api_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )

    assert response.status_code == 202
    body = response.json()
    assert body["mfa_required"] is True
    assert body["methods"] == ["totp", "recovery_code"]
    assert body["mfa_token"]
    assert REFRESH_COOKIE not in response.cookies
    assert MFAChallenge.objects.filter(user=user, used_at__isnull=True).count() == 1


@pytest.mark.django_db
def test_two_factor_verify_endpoint_issues_tokens(api_client, enrolled) -> None:
    user, _ = enrolled
    login = api_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )
    code = current_code(user, offset=30)

    response = api_client.post(
        "/api/v1/auth/2fa/verify/",
        {"mfa_token": login.json()["mfa_token"], "code": code},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["access"]
    assert REFRESH_COOKIE in response.cookies


@pytest.mark.django_db
def test_two_factor_verify_rejects_a_replayed_challenge(api_client, enrolled) -> None:
    user, _ = enrolled
    login = api_client.post(
        "/api/v1/auth/login/",
        {"email": user.email, "password": PASSWORD},
        format="json",
    )
    mfa_token = login.json()["mfa_token"]

    first = api_client.post(
        "/api/v1/auth/2fa/verify/",
        {"mfa_token": mfa_token, "code": current_code(user, offset=30)},
        format="json",
    )
    second = api_client.post(
        "/api/v1/auth/2fa/verify/",
        {"mfa_token": mfa_token, "code": current_code(user, offset=60)},
        format="json",
    )

    assert first.status_code == 200
    assert second.status_code == 401
    assert second.json()["error"]["code"] == "mfa_challenge_invalid"


@pytest.mark.django_db
def test_setup_requires_reauth(api_client, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    blocked = api_client.post("/api/v1/auth/2fa/setup/")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "reauth_required"

    reauth = api_client.post(
        "/api/v1/auth/reauth/", {"password": PASSWORD}, format="json"
    )
    assert reauth.status_code == 200
    assert reauth.json()["reauth_expires_in"] == 600

    allowed = api_client.post("/api/v1/auth/2fa/setup/")
    assert allowed.status_code == 200
    assert allowed.json()["secret"]
    assert "svg" in allowed.json()["qr_svg"]


@pytest.mark.django_db
def test_reauth_rejects_a_wrong_password(api_client, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    response = api_client.post(
        "/api/v1/auth/reauth/", {"password": "wrong"}, format="json"
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_password"


@pytest.mark.django_db
def test_reauth_expires(api_client, user, settings) -> None:
    settings.REAUTH_WINDOW = timedelta(seconds=1)
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")
    now = timezone.now()

    with freeze_time(now):
        assert (
            api_client.post(
                "/api/v1/auth/reauth/", {"password": PASSWORD}, format="json"
            ).status_code
            == 200
        )

    with freeze_time(now + timedelta(seconds=2)):
        blocked = api_client.post("/api/v1/auth/2fa/setup/")
    assert blocked.status_code == 403


@pytest.mark.django_db
def test_full_enrollment_through_the_api(api_client, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")
    api_client.post("/api/v1/auth/reauth/", {"password": PASSWORD}, format="json")

    setup = api_client.post("/api/v1/auth/2fa/setup/")
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()

    confirm = api_client.post(
        "/api/v1/auth/2fa/confirm/", {"code": code}, format="json"
    )

    assert confirm.status_code == 200
    assert confirm.json()["enabled"] is True
    assert len(confirm.json()["recovery_codes"]) == 10
    assert TwoFactorConfig.objects.get(user=user).is_enabled is True


@pytest.mark.django_db
def test_api_confirm_requires_reauth(api_client, user) -> None:
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")
    begin_enrollment(user)

    response = api_client.post(
        "/api/v1/auth/2fa/confirm/",
        {"code": current_code(user)},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_disable_endpoint_requires_a_current_code(api_client, enrolled) -> None:
    user, codes = enrolled
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    wrong = api_client.post(
        "/api/v1/auth/2fa/disable/",
        {"password": PASSWORD, "code": "000000"},
        format="json",
    )
    assert wrong.status_code == 401

    response = api_client.post(
        "/api/v1/auth/2fa/disable/",
        {"password": PASSWORD, "code": codes[0]},
        format="json",
    )
    assert response.status_code == 204


@pytest.mark.django_db
def test_recovery_codes_endpoint_returns_a_new_batch(api_client, enrolled) -> None:
    user, old_codes = enrolled
    tokens = issue_tokens(user, request_meta=RequestMeta())
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens.access}")

    response = api_client.post(
        "/api/v1/auth/2fa/recovery-codes/",
        {"password": PASSWORD, "code": current_code(user, offset=30)},
        format="json",
    )

    assert response.status_code == 200
    new_codes = response.json()["recovery_codes"]
    assert len(new_codes) == 10
    assert set(new_codes).isdisjoint(old_codes)


@pytest.mark.django_db
def test_reauth_marks_only_the_current_session(api_client, user) -> None:
    first = issue_tokens(user, request_meta=RequestMeta())
    second = issue_tokens(user, request_meta=RequestMeta())

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {first.access}")
    assert (
        api_client.post(
            "/api/v1/auth/reauth/", {"password": PASSWORD}, format="json"
        ).status_code
        == 200
    )

    assert api_client.post("/api/v1/auth/2fa/setup/").status_code == 200

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {second.access}")
    assert api_client.post("/api/v1/auth/2fa/setup/").status_code == 403
