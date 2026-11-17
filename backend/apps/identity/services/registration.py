"""Registration: user, profile, layout, and workspace in one transaction."""

from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone as django_timezone

from apps.common.errors import DomainError
from apps.common.models import Currency
from apps.common.validators import validate_iana_timezone
from apps.identity.models import DashboardLayout, User, UserProfile, normalize_email
from apps.workspaces.services import ensure_workspace

MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128

DEFAULT_WIDGETS: list[dict[str, object]] = [
    {"key": "net_worth", "visible": True, "order": 0},
]


class RegistrationError(DomainError):
    status_code = 400


class EmailTaken(RegistrationError):
    code = "email_taken"


class WeakPassword(RegistrationError):
    code = "weak_password"


class InvalidTimezone(RegistrationError):
    code = "invalid_timezone"


class UnsupportedCurrency(RegistrationError):
    code = "unsupported_currency"


class InvalidDisplayName(RegistrationError):
    code = "invalid_display_name"


def _clean_email(email: str) -> str:
    normalized = normalize_email(email)
    try:
        validate_email(normalized)
    except DjangoValidationError as exc:
        raise RegistrationError(
            "Enter a valid email address.", field="email", details={"code": "invalid_email"}
        ) from exc
    return normalized


def _clean_display_name(display_name: str) -> str:
    cleaned = display_name.strip()
    if not cleaned:
        raise InvalidDisplayName("Display name is required.", field="display_name")
    if len(cleaned) > 80:
        raise InvalidDisplayName(
            "Display name must be at most 80 characters.", field="display_name"
        )
    return cleaned


def validate_password_strength(password: str, *, user: User | None = None) -> None:
    """Shared policy for registration, reset, and future password changes."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
            field="password",
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPassword(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters.",
            field="password",
        )
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise WeakPassword(" ".join(exc.messages), field="password") from exc


def _resolve_timezone(timezone: str) -> str:
    try:
        validate_iana_timezone(timezone)
    except DjangoValidationError as exc:
        raise InvalidTimezone("Unknown timezone.", field="timezone") from exc
    return timezone


def _resolve_currency(code: str) -> Currency:
    currency = Currency.objects.filter(code=code.strip().upper(), is_active=True).first()
    if currency is None:
        raise UnsupportedCurrency(
            "Reporting currency is not supported.", field="reporting_currency"
        )
    return currency


@transaction.atomic
def provision_account(
    *,
    email: str,
    password: str | None,
    display_name: str,
    timezone: str = "UTC",
    reporting_currency: str = "USD",
    is_email_verified: bool = False,
) -> User:
    """Create the user aggregate: user, profile, workspace, and dashboard layout.

    Shared by password registration and Google sign-in. Callers are responsible for deciding
    whether the email is allowed to become an account (for example Google's explicit-link rule).
    """
    normalized_email = _clean_email(email)
    clean_name = _clean_display_name(display_name)
    if password is not None:
        validate_password_strength(password)
    clean_timezone = _resolve_timezone(timezone)
    currency = _resolve_currency(reporting_currency)

    if User.objects.filter(email=normalized_email).exists():
        raise EmailTaken("An account already exists for this email.", field="email")

    now = django_timezone.now()
    try:
        user = User.objects.create_user(
            email=normalized_email,
            password=password,
            password_changed_at=now if password is not None else None,
            is_email_verified=is_email_verified,
            email_verified_at=now if is_email_verified else None,
        )
    except IntegrityError as exc:
        # A concurrent registration won the lower(email) unique index.
        raise EmailTaken("An account already exists for this email.", field="email") from exc

    UserProfile.objects.create(
        user=user,
        display_name=clean_name,
        timezone=clean_timezone,
        reporting_currency=currency,
        week_start=1,
    )
    ensure_workspace(user)
    DashboardLayout.objects.create(user=user, widgets=DEFAULT_WIDGETS)
    return user


@transaction.atomic
def register_user(
    *,
    email: str,
    password: str,
    display_name: str,
    timezone: str = "UTC",
    reporting_currency: str = "USD",
) -> User:
    """Create the account aggregate atomically.

    Any failure leaves no partial user, profile, or workspace behind.
    """
    return provision_account(
        email=email,
        password=password,
        display_name=display_name,
        timezone=timezone,
        reporting_currency=reporting_currency,
    )
