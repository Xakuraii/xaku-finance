"""Server-tracked JWT sessions.

Access tokens are short-lived and stateless. Refresh tokens are rotated on every use and tracked in
``UserSession``; presenting an older refresh token revokes the whole lineage (reuse detection). See
ADR-0004 and SECURITY.md 2.2.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.errors import DomainError
from apps.identity.models import User, UserSession, normalize_email

LOCK_THRESHOLD = 5
LOCK_WINDOW = timedelta(minutes=15)
LOCK_DURATIONS = (
    timedelta(minutes=1),
    timedelta(minutes=5),
    timedelta(minutes=15),
    timedelta(hours=1),
)
CLAIM_VERSION = 1


class SessionError(DomainError):
    status_code = 401


class InvalidCredentials(SessionError):
    code = "invalid_credentials"


class InvalidToken(SessionError):
    code = "invalid_token"


class RefreshReuseDetected(InvalidToken):
    """An old refresh token was replayed; the family has been revoked."""


class SessionNotFound(DomainError):
    status_code = 404
    code = "not_found"


class ReauthRequired(DomainError):
    status_code = 403
    code = "reauth_required"


@dataclass(frozen=True)
class RequestMeta:
    user_agent: str = ""
    ip_hash: str | None = None
    approx_location: str | None = None

    @classmethod
    def from_request(cls, request: HttpRequest) -> RequestMeta:
        user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:400]
        raw_ip = request.META.get("REMOTE_ADDR")
        ip_hash = None
        if raw_ip:
            ip_hash = hmac.new(
                settings.IP_HASH_KEY.encode("utf-8"),
                raw_ip.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        return cls(user_agent=user_agent, ip_hash=ip_hash)


@dataclass(frozen=True)
class TokenPair:
    access: str
    refresh: str
    session_id: uuid.UUID
    access_expires_in: int
    refresh_expires_in: int
    user: User | None = None


def _expires_at(token: RefreshToken) -> datetime:
    return datetime.fromtimestamp(int(token["exp"]), tz=UTC)


def _new_refresh(user: User, session_id: uuid.UUID) -> RefreshToken:
    token = RefreshToken.for_user(user)
    token["sid"] = str(session_id)
    token["ver"] = CLAIM_VERSION
    return token


def _pair(token: RefreshToken, session_id: uuid.UUID, user: User | None = None) -> TokenPair:
    return TokenPair(
        access=str(token.access_token),
        refresh=str(token),
        session_id=session_id,
        access_expires_in=int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
        refresh_expires_in=int(api_settings.REFRESH_TOKEN_LIFETIME.total_seconds()),
        user=user,
    )


@transaction.atomic
def issue_tokens(user: User, *, request_meta: RequestMeta) -> TokenPair:
    """Open a new session and return its first access/refresh pair."""
    session_id = uuid.uuid4()
    token = _new_refresh(user, session_id)
    now = timezone.now()
    UserSession.objects.create(
        id=session_id,
        user=user,
        refresh_jti=uuid.UUID(str(token["jti"])),
        family_id=uuid.uuid4(),
        user_agent=request_meta.user_agent,
        ip_hash=request_meta.ip_hash,
        approx_location=request_meta.approx_location,
        last_used_at=now,
        expires_at=_expires_at(token),
    )
    return _pair(token, session_id, user=user)


class _RefreshReuse(Exception):
    def __init__(self, family_id: uuid.UUID) -> None:
        self.family_id = family_id


def rotate_refresh(raw_refresh: str, *, request_meta: RequestMeta | None = None) -> TokenPair:
    """Rotate a refresh token exactly once.

    A token whose ``jti`` is no longer the session's current one is treated as a replay: every
    session in the family is revoked, then the request fails with 401.

    Deliberately not wrapped in an outer ``atomic``: the family revocation must survive the
    exception that reports the replay.
    """
    try:
        token = RefreshToken(raw_refresh)  # type: ignore[arg-type]
    except TokenError as exc:
        raise InvalidToken("Session is no longer valid.") from exc

    user_id = token.get(api_settings.USER_ID_CLAIM)
    sid_raw = token.get("sid")
    jti = token.get("jti")
    if not user_id or not sid_raw or not jti:
        raise InvalidToken("Session is no longer valid.")
    try:
        session_id = uuid.UUID(str(sid_raw))
        presented_jti = uuid.UUID(str(jti))
    except ValueError as exc:
        raise InvalidToken("Session is no longer valid.") from exc

    user = User.objects.filter(pk=user_id, is_active=True).first()
    if user is None:
        raise InvalidToken("Session is no longer valid.")

    now = timezone.now()
    try:
        with transaction.atomic():
            session = (
                UserSession.objects.select_for_update().filter(id=session_id, user=user).first()
            )
            if session is None or session.revoked_at is not None or session.expires_at <= now:
                raise InvalidToken("Session is no longer valid.")
            if session.refresh_jti != presented_jti:
                raise _RefreshReuse(session.family_id)

            new_token = _new_refresh(user, session.id)
            session.refresh_jti = uuid.UUID(str(new_token["jti"]))
            session.last_used_at = now
            session.expires_at = _expires_at(new_token)
            if request_meta is not None:
                session.user_agent = request_meta.user_agent or session.user_agent
                session.ip_hash = request_meta.ip_hash or session.ip_hash
            session.save(
                update_fields=[
                    "refresh_jti",
                    "last_used_at",
                    "expires_at",
                    "user_agent",
                    "ip_hash",
                ]
            )
    except _RefreshReuse as exc:
        # Runs after the inner atomic block rolled back, so the revocation is durable.
        UserSession.objects.filter(family_id=exc.family_id, revoked_at__isnull=True).update(
            revoked_at=now, revoked_reason="refresh_reuse"
        )
        raise RefreshReuseDetected("Session is no longer valid.") from None

    return _pair(new_token, session_id, user=user)


@transaction.atomic
def revoke_session(*, user: User, session_id: uuid.UUID, reason: str = "user_logout") -> None:
    session = UserSession.objects.select_for_update().filter(id=session_id, user=user).first()
    if session is None:
        raise SessionNotFound("Session not found.")
    if session.revoked_at is None:
        session.revoked_at = timezone.now()
        session.revoked_reason = reason
        session.save(update_fields=["revoked_at", "revoked_reason"])


@transaction.atomic
def revoke_all_sessions(*, user: User, reason: str = "logout_all") -> int:
    """Revoke every active session. Returns how many were still active."""
    return UserSession.objects.filter(user=user, revoked_at__isnull=True).update(
        revoked_at=timezone.now(), revoked_reason=reason
    )


@transaction.atomic
def mark_reauth(*, user: User, session_id: uuid.UUID) -> datetime:
    """Record that the user re-entered their password for this session."""
    now = timezone.now()
    session = (
        UserSession.objects.select_for_update()
        .filter(id=session_id, user=user, revoked_at__isnull=True)
        .first()
    )
    if session is None or session.expires_at <= now:
        raise InvalidToken("Session is no longer valid.")
    session.reauth_at = now
    session.save(update_fields=["reauth_at"])
    return now


def has_recent_reauth(*, user: User, session_id: uuid.UUID | None) -> bool:
    """Sensitive actions require a password check inside the reauthentication window."""
    if session_id is None:
        return False
    now = timezone.now()
    return UserSession.objects.filter(
        id=session_id,
        user=user,
        revoked_at__isnull=True,
        expires_at__gt=now,
        reauth_at__gte=now - settings.REAUTH_WINDOW,
    ).exists()


def _lock_duration(failure_count: int) -> timedelta | None:
    if failure_count < LOCK_THRESHOLD:
        return None
    tier = min((failure_count - LOCK_THRESHOLD) // LOCK_THRESHOLD, len(LOCK_DURATIONS) - 1)
    return LOCK_DURATIONS[tier]


def _record_failure(user: User, now: datetime) -> None:
    window_start = user.last_failed_login_at
    count = user.failed_login_count
    if window_start is None or now - window_start > LOCK_WINDOW:
        count = 0
    count += 1
    user.failed_login_count = count
    user.last_failed_login_at = now
    duration = _lock_duration(count)
    if duration is not None:
        user.locked_until = now + duration
    user.save(update_fields=["failed_login_count", "last_failed_login_at", "locked_until"])


def _record_success(user: User, now: datetime) -> None:
    user.failed_login_count = 0
    user.last_failed_login_at = None
    user.locked_until = None
    user.last_login = now
    user.save(
        update_fields=[
            "failed_login_count",
            "last_failed_login_at",
            "locked_until",
            "last_login",
        ]
    )


def authenticate_user(*, email: str, password: str) -> User:
    """Authenticate with a generic failure that never reveals whether the account exists."""
    now = timezone.now()
    normalized = normalize_email(email)
    candidate = User.objects.filter(email=normalized).first()

    if candidate is not None and candidate.locked_until and candidate.locked_until > now:
        raise InvalidCredentials("Invalid email or password.")

    user = authenticate(request=None, email=normalized, password=password)
    if user is None:
        if candidate is not None:
            _record_failure(candidate, now)
        raise InvalidCredentials("Invalid email or password.")

    if candidate is not None:
        _record_success(candidate, now)
    return user
