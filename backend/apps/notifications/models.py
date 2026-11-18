"""Notification models for in-app and email delivery.

See docs/DATABASE.md Section 2.10 and docs/SRS.md FR-NOT-01..08.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.db import models
from django.db.models import CheckConstraint, Index, Q, UniqueConstraint


class NotificationCategory(models.TextChoices):
    SECURITY = "security", "Security"
    BUDGET = "budget", "Budget"
    BILL = "bill", "Bill & Recurring"
    SAVINGS = "savings", "Savings"
    REPORT = "report", "Report"
    SYSTEM = "system", "System"


class NotificationSeverity(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    CRITICAL = "critical", "Critical"


class NotificationChannel(models.TextChoices):
    IN_APP = "in_app", "In-App"
    EMAIL = "email", "Email"


class DeliveryStatus(models.TextChoices):
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    FAILED = "failed", "Failed"
    SUPPRESSED = "suppressed", "Suppressed"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    category = models.CharField(max_length=20, choices=NotificationCategory.choices)
    severity = models.CharField(
        max_length=8,
        choices=NotificationSeverity.choices,
        default=NotificationSeverity.INFO,
    )
    title = models.CharField(max_length=160)
    body = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=120)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notification"
        constraints = [
            UniqueConstraint(
                fields=["user", "dedupe_key"],
                name="notification_user_dedupe_uq",
            ),
        ]
        indexes = [
            Index(
                fields=["user", "read_at", "-created_at"],
                name="ix_notif_user_read_created",
            ),
        ]

    def __str__(self) -> str:
        return f"[{self.category.upper()}] {self.title}"


class NotificationPreference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    category = models.CharField(max_length=20, choices=NotificationCategory.choices)
    in_app = models.BooleanField(default=True)
    email = models.BooleanField(default=False)
    threshold_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    digest = models.CharField(max_length=12, default="immediate")
    locked = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_preference"
        constraints = [
            UniqueConstraint(
                fields=["user", "category"],
                name="notif_pref_user_category_uq",
            ),
            CheckConstraint(
                condition=~Q(category=NotificationCategory.SECURITY)
                | (Q(in_app=True) & Q(locked=True)),
                name="notif_pref_security_locked_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"Preferences for {self.user_id} ({self.category})"


class NotificationDelivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    channel = models.CharField(max_length=8, choices=NotificationChannel.choices)
    status = models.CharField(
        max_length=12,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.QUEUED,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=400, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notification_delivery"
        constraints = [
            UniqueConstraint(
                fields=["notification", "channel"],
                name="notif_deliv_notif_channel_uq",
            ),
        ]
        indexes = [
            Index(
                fields=["status", "created_at"],
                name="ix_notif_deliv_status_created",
            ),
        ]

    def __str__(self) -> str:
        return f"Delivery of {self.notification_id} via {self.channel}: {self.status}"
