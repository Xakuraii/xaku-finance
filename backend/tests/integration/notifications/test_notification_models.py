import pytest
from django.db import IntegrityError

from apps.common.models import Currency
from apps.identity.models import User
from apps.notifications.models import (
    DeliveryStatus,
    Notification,
    NotificationCategory,
    NotificationChannel,
    NotificationDelivery,
    NotificationPreference,
    NotificationSeverity,
)
from apps.workspaces.models import Workspace


@pytest.fixture
def notif_user(db):
    user = User.objects.create_user(email="notifuser@example.com", password="password123456")
    ws = Workspace.objects.create(
        owner=user,
        name="Personal",
        reporting_currency=Currency.objects.get(code="USD"),
        timezone="UTC",
    )
    user.workspace = ws
    return user, ws


def test_notification_creation_and_dedupe_constraint(notif_user):
    user, ws = notif_user

    notif = Notification.objects.create(
        user=user,
        workspace=ws,
        category=NotificationCategory.BUDGET,
        severity=NotificationSeverity.WARNING,
        title="Budget 80% Threshold Reached",
        body="You have spent 82% of your Groceries budget.",
        dedupe_key="budget:groc:2026-11:80",
    )
    assert str(notif) == "[BUDGET] Budget 80% Threshold Reached"

    # Duplicate dedupe_key for same user must be rejected by unique constraint
    with pytest.raises(IntegrityError):
        Notification.objects.create(
            user=user,
            workspace=ws,
            category=NotificationCategory.BUDGET,
            severity=NotificationSeverity.WARNING,
            title="Duplicate Budget Warning",
            body="Another warning.",
            dedupe_key="budget:groc:2026-11:80",
        )


def test_notification_preference_security_locked(notif_user):
    user, _ws = notif_user

    # Valid security preference: locked=True, in_app=True
    pref = NotificationPreference.objects.create(
        user=user,
        category=NotificationCategory.SECURITY,
        in_app=True,
        locked=True,
    )
    assert pref.locked is True

    # Attempting to disable in_app for security must violate check constraint
    pref.in_app = False
    with pytest.raises(IntegrityError):
        pref.save()


def test_notification_delivery_creation(notif_user):
    user, ws = notif_user

    notif = Notification.objects.create(
        user=user,
        workspace=ws,
        category=NotificationCategory.BILL,
        title="Upcoming Rent Due",
        body="Rent is due in 3 days.",
        dedupe_key="bill:rent:2026-11-20",
    )

    deliv = NotificationDelivery.objects.create(
        notification=notif,
        channel=NotificationChannel.IN_APP,
        status=DeliveryStatus.SENT,
    )
    assert deliv.status == DeliveryStatus.SENT

    # Duplicate delivery for same channel on same notification must be rejected
    with pytest.raises(IntegrityError):
        NotificationDelivery.objects.create(
            notification=notif,
            channel=NotificationChannel.IN_APP,
            status=DeliveryStatus.QUEUED,
        )
