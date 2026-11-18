"""Identity models: the account, its profile, and dashboard layout.

The user model is defined before the first migration. Changing it later is expensive, so it carries
the fields the security design needs now. See docs/DATABASE.md 2.1 and ADR-0004.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import ClassVar

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from apps.common.validators import validate_iana_timezone


def normalize_email(email: str) -> str:
    """Emails are case-insensitive for login and uniqueness. Store them normalized."""
    return email.strip().lower()


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def create_user(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> User:
        if not email:
            raise ValueError("An email address is required.")
        user = self.model(email=normalize_email(email), **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        password: str | None = None,
        **extra_fields: object,
    ) -> User:
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(max_length=254, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    failed_login_count = models.PositiveIntegerField(default=0)
    last_failed_login_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        db_table = "identity_user"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="identity_user_email_ci_uq"),
        ]
        indexes = [
            models.Index(
                Lower("email"),
                name="identity_user_email_ix",
                condition=Q(is_active=True),
            ),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def last_login_at(self) -> datetime | None:
        """Docs name this ``last_login_at``; Django's own field is ``last_login``."""
        return self.last_login


class UserProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=80)
    avatar_url = models.URLField(max_length=500, blank=True, default="")
    timezone = models.CharField(
        max_length=64,
        default="UTC",
        validators=[validate_iana_timezone],
    )
    locale = models.CharField(max_length=16, default="en-US")
    reporting_currency = models.ForeignKey(
        "common.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        db_column="reporting_currency_code",
    )
    week_start = models.SmallIntegerField(default=1)
    theme = models.CharField(max_length=8, default="system")
    onboarding_state = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_profile"
        constraints = [
            models.CheckConstraint(
                condition=Q(week_start__gte=1) & Q(week_start__lte=7),
                name="user_profile_week_start_ck",
            ),
            models.CheckConstraint(
                condition=Q(theme__in=["light", "dark", "system"]),
                name="user_profile_theme_ck",
            ),
        ]

    def __str__(self) -> str:
        return self.display_name


class JsonbArrayCheck(models.Func):
    """CHECK-friendly expression asserting a jsonb column holds an array."""

    function = ""
    template = "jsonb_typeof(%(expressions)s) = 'array'"
    output_field = models.BooleanField()
    conditional = True


class DashboardLayout(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="dashboard_layout",
    )
    widgets = models.JSONField(default=list)
    version = models.PositiveSmallIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dashboard_layout"
        constraints = [
            models.CheckConstraint(
                condition=JsonbArrayCheck("widgets"),
                name="dashboard_layout_widgets_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"Layout for {self.user_id}"


class UserSession(models.Model):
    """A refresh-token lineage. Rotation updates ``refresh_jti``; reuse revokes the family."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    refresh_jti = models.UUIDField(unique=True)
    family_id = models.UUIDField(db_index=True)
    user_agent = models.CharField(max_length=400, blank=True, default="")
    #: HMAC-SHA256 of the client IP. The raw address is never stored.
    ip_hash = models.CharField(max_length=64, null=True, blank=True)
    approx_location = models.CharField(max_length=120, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField()
    expires_at = models.DateTimeField()
    #: Set by the reauthentication endpoint; sensitive actions require it to be recent.
    reauth_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_reason = models.CharField(max_length=40, blank=True, default="")

    class Meta:
        db_table = "user_session"
        indexes = [
            models.Index(
                fields=["user", "revoked_at", "-last_used_at"],
                name="user_session_active_ix",
            ),
        ]

    def __str__(self) -> str:
        return f"Session {self.id} for {self.user_id}"


class IdentityToken(models.Model):
    """A hashed, single-use, expiring token for email verification or password reset.

    Only the SHA-256 hash is stored. ``purpose`` keeps the two flows from accepting each other's
    tokens. See SECURITY.md 2 and DATABASE.md 2.1.
    """

    PURPOSE_EMAIL_VERIFICATION = "email_verification"
    PURPOSE_PASSWORD_RESET = "password_reset"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="identity_tokens",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    purpose = models.CharField(max_length=24)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    requested_ip_hash = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "identity_token"
        indexes = [
            models.Index(
                fields=["user", "purpose", "expires_at"],
                name="identity_token_user_purpose_ix",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(purpose__in=["email_verification", "password_reset"]),
                name="identity_token_purpose_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.purpose} token for {self.user_id}"


class SocialIdentity(models.Model):
    """An external identity linked to a local account, currently Google only."""

    PROVIDER_GOOGLE = "google"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="social_identities",
    )
    provider = models.CharField(max_length=20)
    subject = models.CharField(max_length=255)
    email_at_provider = models.EmailField(max_length=254)
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField()

    class Meta:
        db_table = "social_identity"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "subject"],
                name="social_identity_provider_subject_uq",
            ),
            models.UniqueConstraint(
                fields=["user", "provider"],
                name="social_identity_user_provider_uq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.subject}"


class TwoFactorConfig(models.Model):
    """TOTP enrollment state. The secret is stored only as Fernet ciphertext."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="two_factor",
    )
    is_enabled = models.BooleanField(default=False)
    secret_ciphertext = models.BinaryField()
    key_version = models.PositiveSmallIntegerField(default=1)
    algorithm = models.CharField(max_length=12, default="SHA1")
    digits = models.PositiveSmallIntegerField(default=6)
    period_seconds = models.PositiveSmallIntegerField(default=30)
    #: Highest accepted TOTP time-step; a code at or below it is a replay.
    last_used_counter = models.BigIntegerField(null=True, blank=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    last_failed_at = models.DateTimeField(null=True, blank=True)
    locked_until = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    disabled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "two_factor_config"
        constraints = [
            models.CheckConstraint(
                condition=Q(digits__gte=6) & Q(digits__lte=8),
                name="two_factor_digits_ck",
            ),
            models.CheckConstraint(
                condition=Q(period_seconds__gte=15) & Q(period_seconds__lte=120),
                name="two_factor_period_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"2FA for {self.user_id} ({'enabled' if self.is_enabled else 'pending'})"


class RecoveryCode(models.Model):
    """One Argon2id-hashed, single-use recovery code. A batch id allows regeneration."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="recovery_codes",
    )
    batch_id = models.UUIDField(db_index=True)
    code_hash = models.CharField(max_length=128)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "recovery_code"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "code_hash"],
                name="recovery_code_user_hash_uq",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "used_at"], name="recovery_code_user_used_ix"),
        ]

    def __str__(self) -> str:
        return f"Recovery code for {self.user_id}"


class MFAChallenge(models.Model):
    """A short-lived, single-use token that bridges password success and a 2FA code."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="mfa_challenges",
    )
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mfa_challenge"
        indexes = [
            models.Index(fields=["user", "expires_at"], name="mfa_challenge_user_expiry_ix"),
        ]

    def __str__(self) -> str:
        return f"MFA challenge for {self.user_id}"
