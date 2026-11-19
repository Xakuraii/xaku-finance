"""Service for account deletion requests, grace period management, and execution.

See docs/architecture/SECURITY.md Section 9.2 and docs/api/API_SPECIFICATION.md Section 16.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.identity.models import User, UserSession
from apps.identity.services import two_factor
from apps.identity.services.two_factor import InvalidPassword
from apps.notifications.models import NotificationCategory, NotificationSeverity
from apps.notifications.services.notifications import create_notification
from apps.privacy.models import AccountDeletionRequest, DeletionRequestStatus

logger = logging.getLogger(__name__)

DELETION_CONSEQUENCES = [
    "All accounts, transactions, budgets, goals, debts, and reports will be permanently deleted.",
    "Encrypted backups containing this data expire by the backup expiry date shown.",
    "This action cannot be undone after the grace period expires.",
]


def request_account_deletion(
    *,
    user: User,
    password: str,
    confirm_text: str,
    code: str | None = None,
    current_session_id: Any | None = None,
) -> AccountDeletionRequest:
    """Register an account deletion request with a 7-day grace period."""
    if confirm_text != "DELETE":
        raise ValidationError("Confirmation text must be 'DELETE'.")

    if not user.has_usable_password() or not user.check_password(password):
        raise InvalidPassword("Password is incorrect.")

    if two_factor.is_enabled(user):
        if not code:
            raise ValidationError("A two-factor authentication code is required.")
        config = two_factor._enabled_config(user, for_update=True)
        two_factor._consume_factor(user, config, code.strip(), timezone.now())

    active = AccountDeletionRequest.objects.filter(
        user=user,
        status=DeletionRequestStatus.REQUESTED,
    ).first()
    if active:
        return active

    now = timezone.now()
    execute_after = now + timedelta(days=7)
    backup_expiry_date = (execute_after + timedelta(days=30)).date()

    workspace = getattr(user, "workspace", None)

    with transaction.atomic():
        req = AccountDeletionRequest.objects.create(
            user=user,
            workspace=workspace,
            status=DeletionRequestStatus.REQUESTED,
            execute_after=execute_after,
            backup_expiry_date=backup_expiry_date,
        )

        # Revoke other sessions immediately
        sessions = UserSession.objects.filter(user=user, revoked_at__isnull=True)
        if current_session_id:
            sessions = sessions.exclude(id=current_session_id)
        sessions.update(
            revoked_at=now,
            revoked_reason="account_deletion_requested",
        )

        if workspace:
            create_notification(
                user=user,
                workspace=workspace,
                category=NotificationCategory.SECURITY,
                severity=NotificationSeverity.CRITICAL,
                title="Account Deletion Scheduled",
                body=(
                    f"Your account deletion request is active. All live financial data will be permanently "
                    f"deleted on {execute_after.strftime('%Y-%m-%d %H:%M UTC')}. Encrypted backups containing "
                    f"your records expire by {backup_expiry_date.isoformat()}. You may cancel during this 7-day grace period."
                ),
                dedupe_key=f"deletion_requested_{req.id}",
                data={"deletion_request_id": str(req.id), "execute_after": execute_after.isoformat()},
            )

    logger.info("Account deletion requested for user %s, execution after %s", user.id, execute_after)
    return req


def cancel_account_deletion(*, user: User) -> AccountDeletionRequest:
    """Cancel a pending deletion request during the grace period."""
    req = AccountDeletionRequest.objects.filter(
        user=user,
        status=DeletionRequestStatus.REQUESTED,
    ).first()
    if not req:
        raise NotFound("No active deletion request found to cancel.")

    now = timezone.now()
    req.status = DeletionRequestStatus.CANCELLED
    req.cancelled_at = now
    req.save(update_fields=["status", "cancelled_at", "updated_at"])

    workspace = getattr(user, "workspace", None)
    if workspace:
        create_notification(
            user=user,
            workspace=workspace,
            category=NotificationCategory.SECURITY,
            severity=NotificationSeverity.INFO,
            title="Account Deletion Cancelled",
            body="Your account deletion request was cancelled. Your workspace and financial data remain active.",
            dedupe_key=f"deletion_cancelled_{req.id}_{int(now.timestamp())}",
        )

    logger.info("Account deletion cancelled for user %s", user.id)
    return req


def get_current_deletion_request(*, user: User) -> AccountDeletionRequest | None:
    """Get the currently active deletion request, if any."""
    return AccountDeletionRequest.objects.filter(
        user=user,
        status=DeletionRequestStatus.REQUESTED,
    ).first()


@transaction.atomic
def execute_deletion(deletion_request: AccountDeletionRequest) -> None:
    """Permanently execute an account deletion after grace period expiration."""
    user = deletion_request.user
    workspace = deletion_request.workspace

    now = timezone.now()
    deletion_request.status = DeletionRequestStatus.EXECUTED
    deletion_request.executed_at = now
    deletion_request.workspace = None
    deletion_request.save(update_fields=["status", "executed_at", "workspace", "updated_at"])

    if workspace:
        # Cascade workspace deletion deletes accounts, ledger, transactions, etc.
        workspace.delete()

    user.is_active = False
    user.email = f"deleted_{user.id}@deleted.local"
    user.set_unusable_password()
    user.save(update_fields=["is_active", "email", "password"])

    logger.info("Account deletion executed permanently for user %s", user.id)
