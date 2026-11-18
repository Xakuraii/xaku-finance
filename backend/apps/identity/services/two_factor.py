"""Optional TOTP two-factor authentication.

The shared secret is Fernet-encrypted at rest with a versioned key. TOTP uses RFC 6238 with a
recorded time-step counter so a code cannot be replayed. Recovery codes are single-use and hashed
with Argon2id. See SECURITY.md 2.1 and DATABASE.md 2.1.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime

import pyotp
import qrcode
import qrcode.image.svg
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet
from cryptography.fernet import InvalidToken as FernetInvalidToken
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.common.errors import DomainError
from apps.identity.models import MFAChallenge, RecoveryCode, TwoFactorConfig, User
from apps.identity.services.email_tokens import hash_token, send_identity_email
from apps.identity.services.sessions import RequestMeta, TokenPair, issue_tokens

logger = logging.getLogger(__name__)

DIGESTS = {
    "SHA1": hashlib.sha1,
    "SHA256": hashlib.sha256,
    "SHA512": hashlib.sha512,
}


class TwoFactorError(DomainError):
    status_code = 400


class InvalidCode(TwoFactorError):
    status_code = 401
    code = "invalid_code"


class InvalidPassword(TwoFactorError):
    status_code = 401
    code = "invalid_password"


class TooManyAttempts(TwoFactorError):
    status_code = 429
    code = "too_many_attempts"


class AlreadyEnabled(TwoFactorError):
    status_code = 409
    code = "two_factor_already_enabled"


class NotEnabled(TwoFactorError):
    status_code = 409
    code = "two_factor_not_enabled"


class ChallengeInvalid(TwoFactorError):
    status_code = 401
    code = "mfa_challenge_invalid"


@dataclass(frozen=True)
class Enrollment:
    secret: str
    otpauth_uri: str
    qr_svg: str


@dataclass(frozen=True)
class ChallengeIssued:
    token: str
    expires_in: int


def _password_hasher() -> PasswordHasher:
    return PasswordHasher(
        time_cost=settings.RECOVERY_CODE_HASH_TIME_COST,
        memory_cost=settings.RECOVERY_CODE_HASH_MEMORY_COST,
        parallelism=settings.RECOVERY_CODE_HASH_PARALLELISM,
        hash_len=32,
        salt_len=16,
    )


def _fernet(version: int) -> Fernet:
    key = settings.TWO_FACTOR_ENCRYPTION_KEYS[version]
    return Fernet(key.encode("ascii"))


def _encrypt_secret(secret: str) -> tuple[bytes, int]:
    version = settings.TWO_FACTOR_CURRENT_KEY_VERSION
    return _fernet(version).encrypt(secret.encode("ascii")), version


def _decrypt_secret(config: TwoFactorConfig) -> str:
    """Try the recorded key first, then every configured key so rotation works."""
    ciphertext = bytes(config.secret_ciphertext)
    ordered = [config.key_version] + [
        version
        for version in settings.TWO_FACTOR_ENCRYPTION_KEYS
        if version != config.key_version
    ]
    for version in ordered:
        key = settings.TWO_FACTOR_ENCRYPTION_KEYS.get(version)
        if not key:
            continue
        try:
            return Fernet(key.encode("ascii")).decrypt(ciphertext).decode("ascii")
        except FernetInvalidToken:
            continue
    raise TwoFactorError(
        "The two-factor secret cannot be read. Contact support.",
        details={"reason": "key_unavailable"},
    )


def _otpauth_uri(user: User, secret: str) -> str:
    totp = pyotp.TOTP(
        secret,
        digits=settings.TWO_FACTOR_DIGITS,
        interval=settings.TWO_FACTOR_PERIOD_SECONDS,
        digest=DIGESTS[settings.TWO_FACTOR_ALGORITHM],
    )
    return totp.provisioning_uri(name=user.email, issuer_name=settings.TWO_FACTOR_ISSUER)


def _qr_svg(otpauth_uri: str) -> str:
    image = qrcode.make(otpauth_uri, image_factory=qrcode.image.svg.SvgPathImage)
    return image.to_string().decode("utf-8")


def is_enabled(user: User) -> bool:
    return TwoFactorConfig.objects.filter(user=user, is_enabled=True).exists()


def _enabled_config(user: User, *, for_update: bool = False) -> TwoFactorConfig:
    query = TwoFactorConfig.objects
    if for_update:
        query = query.select_for_update()
    config = query.filter(user=user, is_enabled=True).first()
    if config is None:
        raise NotEnabled("Two-factor authentication is not enabled.")
    return config


def _ensure_unlocked(config: TwoFactorConfig, now: datetime) -> None:
    if config.locked_until is not None and config.locked_until > now:
        raise TooManyAttempts("Too many incorrect codes. Try again later.")


def _record_failure(config: TwoFactorConfig, now: datetime) -> None:
    if (
        config.last_failed_at is None
        or now - config.last_failed_at > settings.TWO_FACTOR_LOCK_WINDOW
    ):
        config.failed_attempts = 0
    config.failed_attempts += 1
    config.last_failed_at = now
    if config.failed_attempts >= settings.TWO_FACTOR_MAX_FAILURES:
        config.locked_until = now + settings.TWO_FACTOR_LOCK_DURATION
        config.failed_attempts = 0
    config.save(update_fields=["failed_attempts", "last_failed_at", "locked_until"])


def _record_success(
    config: TwoFactorConfig, now: datetime, *, counter: int | None
) -> None:
    config.failed_attempts = 0
    config.last_failed_at = None
    config.locked_until = None
    if counter is not None:
        config.last_used_counter = counter
    config.save(
        update_fields=[
            "failed_attempts",
            "last_failed_at",
            "locked_until",
            "last_used_counter",
        ]
    )


def _matching_counter(
    config: TwoFactorConfig, secret: str, code: str, now: datetime
) -> int | None:
    totp = pyotp.TOTP(
        secret,
        digits=config.digits,
        interval=config.period_seconds,
        digest=DIGESTS[config.algorithm],
    )
    counter = int(now.timestamp()) // config.period_seconds
    for candidate in (counter - 1, counter, counter + 1):
        expected = totp.generate_otp(candidate)
        if hmac.compare_digest(expected, code):
            return candidate
    return None


def _normalize_recovery_code(raw: str) -> str:
    return raw.strip().replace("-", "").replace(" ", "").lower()


def _new_recovery_code() -> str:
    raw = (
        base64.b32encode(secrets.token_bytes(settings.RECOVERY_CODE_BYTES))
        .decode("ascii")
        .rstrip("=")
    )
    return "-".join(raw[index : index + 4] for index in range(0, len(raw), 4))


def _consume_recovery_code(user: User, code: str, now: datetime) -> bool:
    hasher = _password_hasher()
    normalized = _normalize_recovery_code(code)
    for candidate in RecoveryCode.objects.filter(user=user, used_at__isnull=True):
        try:
            if not hasher.verify(candidate.code_hash, normalized):
                continue
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            continue
        candidate.used_at = now
        candidate.save(update_fields=["used_at"])
        return True
    return False


def _consume_factor(
    user: User, config: TwoFactorConfig, code: str, now: datetime
) -> None:
    """Accept a current TOTP code or an unused recovery code, or record a failure."""
    _ensure_unlocked(config, now)
    candidate_code = code.strip()

    if candidate_code.isdigit() and len(candidate_code) == config.digits:
        secret = _decrypt_secret(config)
        counter = _matching_counter(config, secret, candidate_code, now)
        if counter is None:
            _record_failure(config, now)
            raise InvalidCode("That code is not valid.")
        if (
            config.last_used_counter is not None
            and counter <= config.last_used_counter
        ):
            _record_failure(config, now)
            raise InvalidCode("That code has already been used.")
        _record_success(config, now, counter=counter)
        return

    if not _consume_recovery_code(user, candidate_code, now):
        _record_failure(config, now)
        raise InvalidCode("That code is not valid.")
    _record_success(config, now, counter=None)


def _issue_recovery_codes(user: User) -> list[str]:
    """Replace every existing code and return the plaintext list exactly once."""
    RecoveryCode.objects.filter(user=user).delete()
    batch_id = uuid.uuid4()
    hasher = _password_hasher()
    codes: list[str] = []
    for _ in range(settings.RECOVERY_CODE_COUNT):
        raw = _new_recovery_code()
        RecoveryCode.objects.create(
            user=user,
            batch_id=batch_id,
            code_hash=hasher.hash(_normalize_recovery_code(raw)),
        )
        codes.append(raw)
    return codes


@transaction.atomic
def begin_enrollment(user: User) -> Enrollment:
    """Create or reset a pending TOTP secret. Caller must have reauthenticated first."""
    config = TwoFactorConfig.objects.select_for_update().filter(user=user).first()
    if config is not None and config.is_enabled:
        raise AlreadyEnabled("Two-factor authentication is already enabled.")

    secret = pyotp.random_base32(length=32)
    ciphertext, version = _encrypt_secret(secret)
    if config is None:
        config = TwoFactorConfig(user=user)
    config.is_enabled = False
    config.secret_ciphertext = ciphertext
    config.key_version = version
    config.algorithm = settings.TWO_FACTOR_ALGORITHM
    config.digits = settings.TWO_FACTOR_DIGITS
    config.period_seconds = settings.TWO_FACTOR_PERIOD_SECONDS
    config.last_used_counter = None
    config.failed_attempts = 0
    config.last_failed_at = None
    config.locked_until = None
    config.confirmed_at = None
    config.disabled_at = None
    config.save()

    RecoveryCode.objects.filter(user=user).delete()
    uri = _otpauth_uri(user, secret)
    return Enrollment(secret=secret, otpauth_uri=uri, qr_svg=_qr_svg(uri))


@transaction.atomic
def confirm_enrollment(user: User, code: str) -> list[str]:
    """Enable 2FA after a successful code and return fresh recovery codes."""
    config = TwoFactorConfig.objects.select_for_update().filter(user=user).first()
    if config is None:
        raise NotEnabled("Start enrollment before confirming a code.")
    if config.is_enabled:
        raise AlreadyEnabled("Two-factor authentication is already enabled.")

    now = timezone.now()
    _ensure_unlocked(config, now)
    secret = _decrypt_secret(config)
    counter = _matching_counter(config, secret, code.strip(), now)
    if counter is None:
        _record_failure(config, now)
        raise InvalidCode("That code is not valid.")

    config.is_enabled = True
    config.confirmed_at = now
    config.last_used_counter = counter
    config.failed_attempts = 0
    config.last_failed_at = None
    config.locked_until = None
    config.save(
        update_fields=[
            "is_enabled",
            "confirmed_at",
            "last_used_counter",
            "failed_attempts",
            "last_failed_at",
            "locked_until",
        ]
    )
    return _issue_recovery_codes(user)


def create_challenge(user: User) -> ChallengeIssued:
    """Issue a short-lived, single-use token that only proves the password step."""
    raw = secrets.token_urlsafe(32)
    now = timezone.now()
    MFAChallenge.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
    MFAChallenge.objects.create(
        user=user,
        token_hash=hash_token(raw),
        expires_at=now + settings.MFA_CHALLENGE_TTL,
    )
    return ChallengeIssued(
        token=raw,
        expires_in=int(settings.MFA_CHALLENGE_TTL.total_seconds()),
    )


def verify_challenge(
    raw_token: str, code: str, *, request_meta: RequestMeta
) -> TokenPair:
    """Complete a login challenge with a TOTP or recovery code and open a session.

    Deliberately not atomic: a wrong code must persist its failure counter even though the
    request ends with an error.
    """
    now = timezone.now()
    challenge = (
        MFAChallenge.objects.select_related("user")
        .filter(token_hash=hash_token(raw_token), used_at__isnull=True)
        .first()
    )
    if challenge is None or challenge.expires_at <= now:
        raise ChallengeInvalid("This sign-in attempt has expired. Start again.")

    user = challenge.user
    if not user.is_active:
        raise ChallengeInvalid("This sign-in attempt has expired. Start again.")

    config = (
        TwoFactorConfig.objects.filter(user=user, is_enabled=True).first()
    )
    if config is None:
        raise ChallengeInvalid("This sign-in attempt has expired. Start again.")

    _consume_factor(user, config, code, now)

    with transaction.atomic():
        burned = MFAChallenge.objects.filter(
            pk=challenge.pk, used_at__isnull=True
        ).update(used_at=timezone.now())
        if not burned:
            raise ChallengeInvalid("This sign-in attempt has expired. Start again.")

    return issue_tokens(user, request_meta=request_meta)


def _check_password(user: User, password: str) -> None:
    if not user.has_usable_password() or not user.check_password(password):
        raise InvalidPassword("Password is incorrect.")


@transaction.atomic
def disable(user: User, *, password: str, code: str) -> None:
    """Turn 2FA off. Requires both the account password and a current factor."""
    config = _enabled_config(user, for_update=True)
    _check_password(user, password)
    now = timezone.now()
    _consume_factor(user, config, code, now)

    config.is_enabled = False
    config.disabled_at = now
    config.confirmed_at = None
    # Replace the secret so an old database copy cannot be reactivated.
    ciphertext, version = _encrypt_secret(pyotp.random_base32(length=32))
    config.secret_ciphertext = ciphertext
    config.key_version = version
    config.last_used_counter = None
    config.save(
        update_fields=[
            "is_enabled",
            "disabled_at",
            "confirmed_at",
            "secret_ciphertext",
            "key_version",
            "last_used_counter",
        ]
    )
    RecoveryCode.objects.filter(user=user).delete()
    send_identity_email(
        subject="Two-factor authentication was disabled",
        template="identity/emails/two_factor_disabled.txt",
        context={
            "display_name": getattr(getattr(user, "profile", None), "display_name", ""),
            "changed_at": now,
        },
        to=user.email,
    )
    logger.info("Two-factor authentication disabled")


@transaction.atomic
def regenerate_recovery_codes(
    user: User, *, password: str, code: str
) -> list[str]:
    """Replace recovery codes after re-checking the password and a current factor."""
    config = _enabled_config(user, for_update=True)
    _check_password(user, password)
    _consume_factor(user, config, code, timezone.now())
    return _issue_recovery_codes(user)
