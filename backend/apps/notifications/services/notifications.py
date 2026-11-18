"""Notification delivery and preference services."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.notifications.models import (
    DeliveryStatus,
    Notification,
    NotificationCategory,
    NotificationChannel,
    NotificationDelivery,
    NotificationPreference,
    NotificationSeverity,
)

if TYPE_CHECKING:
    from apps.identity.models import User
    from apps.workspaces.models import Workspace


class SecurityNotificationLocked(Exception):
    """Raised when an attempt is made to disable locked security notifications."""


DEFAULT_CATEGORY_CONFIG = {
    NotificationCategory.SECURITY: {"in_app": True, "email": True, "locked": True},
    NotificationCategory.BUDGET: {"in_app": True, "email": False, "locked": False},
    NotificationCategory.BILL: {"in_app": True, "email": False, "locked": False},
    NotificationCategory.SAVINGS: {"in_app": True, "email": False, "locked": False},
    NotificationCategory.REPORT: {"in_app": True, "email": False, "locked": False},
    NotificationCategory.SYSTEM: {"in_app": True, "email": False, "locked": False},
}


def ensure_user_preferences(user: User) -> list[NotificationPreference]:
    """Ensure preferences exist for all canonical categories, returning them in order."""
    existing = {p.category: p for p in NotificationPreference.objects.filter(user=user)}
    created_prefs: list[NotificationPreference] = []

    for cat in NotificationCategory.values:
        if cat in existing:
            created_prefs.append(existing[cat])
        else:
            cfg = DEFAULT_CATEGORY_CONFIG.get(
                cat, {"in_app": True, "email": False, "locked": False}
            )
            pref = NotificationPreference.objects.create(
                user=user,
                category=cat,
                in_app=cfg["in_app"],
                email=cfg["email"],
                locked=cfg["locked"],
            )
            created_prefs.append(pref)

    return created_prefs


def update_user_preferences(
    user: User,
    preferences_data: list[dict[str, Any]],
) -> list[NotificationPreference]:
    """Update user notification preferences, rejecting edits to locked security settings."""
    ensure_user_preferences(user)

    for item in preferences_data:
        cat = item.get("category")
        if not cat:
            continue

        if cat == NotificationCategory.SECURITY:
            if item.get("in_app") is False or item.get("locked") is False:
                raise SecurityNotificationLocked("Security notifications cannot be disabled.")

        pref = NotificationPreference.objects.filter(user=user, category=cat).first()
        if pref:
            if "in_app" in item:
                pref.in_app = bool(item["in_app"])
            if "email" in item:
                pref.email = bool(item["email"])
            if "quiet_hours_start" in item:
                pref.quiet_hours_start = item["quiet_hours_start"]
            if "quiet_hours_end" in item:
                pref.quiet_hours_end = item["quiet_hours_end"]
            if "digest" in item:
                pref.digest = item["digest"]
            pref.save()

    return list(NotificationPreference.objects.filter(user=user).order_by("category"))


@transaction.atomic
def create_notification(
    *,
    user: User,
    workspace: Workspace,
    category: str,
    title: str,
    body: str,
    dedupe_key: str,
    severity: str = NotificationSeverity.INFO,
    data: dict[str, Any] | None = None,
) -> tuple[Notification | None, bool]:
    """Create a deduplicated notification and queue appropriate channel deliveries."""
    pref = NotificationPreference.objects.filter(user=user, category=category).first()
    if pref and not pref.in_app and category != NotificationCategory.SECURITY:
        # In-app delivery suppressed by preference
        return None, False

    try:
        notif, created = Notification.objects.get_or_create(
            user=user,
            dedupe_key=dedupe_key,
            defaults={
                "workspace": workspace,
                "category": category,
                "severity": severity,
                "title": title,
                "body": body,
                "data": data or {},
            },
        )
    except IntegrityError:
        return None, False

    if created:
        # Queue in-app delivery
        NotificationDelivery.objects.create(
            notification=notif,
            channel=NotificationChannel.IN_APP,
            status=DeliveryStatus.SENT,
            sent_at=timezone.now(),
        )

        # Queue email delivery if enabled and user email is verified
        if pref and pref.email and getattr(user, "is_email_verified", False):
            NotificationDelivery.objects.create(
                notification=notif,
                channel=NotificationChannel.EMAIL,
                status=DeliveryStatus.QUEUED,
            )

    return notif, created


def mark_notification_read(user: User, notification_id: UUID | str) -> bool:
    """Mark an individual notification as read."""
    updated = Notification.objects.filter(
        id=notification_id,
        user=user,
        read_at__isnull=True,
    ).update(read_at=timezone.now())
    return bool(updated)


def mark_all_notifications_read(user: User) -> int:
    """Mark all unread notifications for a user as read."""
    return Notification.objects.filter(
        user=user,
        read_at__isnull=True,
    ).update(read_at=timezone.now())


def get_unread_count(user: User) -> int:
    """Return the total number of unread notifications for a user."""
    return Notification.objects.filter(user=user, read_at__isnull=True).count()
