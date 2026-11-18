from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.budgets.services.create import create_budget
from apps.categories.models import Category, CategoryKind
from apps.common.models import Currency
from apps.identity.models import User
from apps.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
)
from apps.transactions.models import Transaction, TransactionType
from apps.workspaces.models import Workspace


@pytest.fixture
def auth_setup(db):
    user = User.objects.create_user(email="notif_api_user@example.com", password="password123456")
    usd = Currency.objects.get(code="USD")
    ws = Workspace.objects.create(
        owner=user,
        name="User WS",
        reporting_currency=usd,
        timezone="UTC",
    )
    user.workspace = ws

    other_user = User.objects.create_user(email="other_user@example.com", password="password123456")
    other_ws = Workspace.objects.create(
        owner=other_user,
        name="Other WS",
        reporting_currency=usd,
        timezone="UTC",
    )
    other_user.workspace = other_ws

    client = APIClient()
    client.force_authenticate(user=user)

    return {
        "user": user,
        "ws": ws,
        "other_user": other_user,
        "other_ws": other_ws,
        "client": client,
        "currency": usd,
    }


def test_notification_list_and_unread_count(auth_setup):
    user = auth_setup["user"]
    ws = auth_setup["ws"]
    client = auth_setup["client"]

    # Create 3 notifications for user, 1 for other user
    n1 = Notification.objects.create(
        user=user,
        workspace=ws,
        category=NotificationCategory.BUDGET,
        severity=NotificationSeverity.WARNING,
        title="Budget 80%",
        body="Spent 80%",
        dedupe_key="k1",
    )
    Notification.objects.create(
        user=user,
        workspace=ws,
        category=NotificationCategory.SAVINGS,
        severity=NotificationSeverity.INFO,
        title="Goal reached",
        body="Good job",
        dedupe_key="k2",
    )
    n3 = Notification.objects.create(
        user=user,
        workspace=ws,
        category=NotificationCategory.BILL,
        severity=NotificationSeverity.CRITICAL,
        title="Bill due",
        body="Electric bill",
        dedupe_key="k3",
    )
    Notification.objects.create(
        user=auth_setup["other_user"],
        workspace=auth_setup["other_ws"],
        category=NotificationCategory.SECURITY,
        severity=NotificationSeverity.CRITICAL,
        title="Other user alert",
        body="Secret",
        dedupe_key="k_other",
    )

    # Initial unread count should be 3
    resp = client.get("/api/v1/notifications/unread-count/")
    assert resp.status_code == 200
    assert resp.data["unread_count"] == 3

    # List all
    resp = client.get("/api/v1/notifications/")
    assert resp.status_code == 200
    assert len(resp.data) == 3
    assert resp.data[0]["id"] == str(n3.id)

    # Filter by category
    resp = client.get("/api/v1/notifications/?category=budget")
    assert resp.status_code == 200
    assert len(resp.data) == 1
    assert resp.data[0]["id"] == str(n1.id)

    # Mark n1 as read
    resp = client.post(f"/api/v1/notifications/{n1.id}/read/")
    assert resp.status_code == 200
    assert resp.data["success"] is True

    # Filter unread
    resp = client.get("/api/v1/notifications/?unread=true")
    assert resp.status_code == 200
    assert len(resp.data) == 2

    # Check unread count is now 2
    resp = client.get("/api/v1/notifications/unread-count/")
    assert resp.status_code == 200
    assert resp.data["unread_count"] == 2

    # Mark all read
    resp = client.post("/api/v1/notifications/read-all/")
    assert resp.status_code == 200
    assert resp.data["updated_count"] == 2

    # Unread count is now 0
    resp = client.get("/api/v1/notifications/unread-count/")
    assert resp.status_code == 200
    assert resp.data["unread_count"] == 0


def test_notification_read_other_user_404(auth_setup):
    client = auth_setup["client"]
    other_notif = Notification.objects.create(
        user=auth_setup["other_user"],
        workspace=auth_setup["other_ws"],
        category=NotificationCategory.SECURITY,
        severity=NotificationSeverity.CRITICAL,
        title="Secret",
        body="Secret",
        dedupe_key="other_key_secret",
    )

    # Attempting to read another user's notification returns 404
    resp = client.post(f"/api/v1/notifications/{other_notif.id}/read/")
    assert resp.status_code == 404


def test_notification_preferences_get_and_put(auth_setup):
    client = auth_setup["client"]

    # GET auto-creates all canonical categories
    resp = client.get("/api/v1/notification-preferences/")
    assert resp.status_code == 200
    categories = [p["category"] for p in resp.data]
    assert "security" in categories
    assert "budget" in categories
    assert "bill" in categories

    # Update budget preference
    payload = [
        {"category": "budget", "in_app": False, "email": True},
    ]
    resp = client.put("/api/v1/notification-preferences/", data=payload, format="json")
    assert resp.status_code == 200
    budget_pref = next(p for p in resp.data if p["category"] == "budget")
    assert budget_pref["in_app"] is False
    assert budget_pref["email"] is True

    # Attempt to disable locked security notification -> 409 CONFLICT
    lock_tamper_payload = [
        {"category": "security", "in_app": False},
    ]
    resp = client.put("/api/v1/notification-preferences/", data=lock_tamper_payload, format="json")
    assert resp.status_code == 409
    assert resp.data["code"] == "security_notification_locked"


def test_evaluate_notifications_endpoint(auth_setup):
    user = auth_setup["user"]
    ws = auth_setup["ws"]
    client = auth_setup["client"]
    curr = auth_setup["currency"]

    acc = create_account(
        workspace=ws,
        name="Checking",
        account_type=AccountType.CHECKING,
        currency=curr.code,
        actor=user,
        opened_on=date(2026, 1, 1),
    )

    cat = Category.objects.create(workspace=ws, name="Groceries", kind=CategoryKind.EXPENSE)
    create_budget(
        workspace=ws,
        name="Groceries Budget",
        category_id=cat.id,
        amount="100.00",
        currency=curr.code,
        period_type="monthly",
    )

    # Spend $85.00 (85%)
    Transaction.objects.create(
        workspace=ws,
        account=acc,
        currency=curr,
        category=cat,
        amount_minor=8500,
        transaction_type=TransactionType.EXPENSE,
        occurred_on=date.today(),
        description="Weekly grocery shopping",
        created_by=user,
    )

    # Trigger evaluation endpoint
    resp = client.post("/api/v1/notifications/evaluate/")
    assert resp.status_code == 200
    assert resp.data["evaluated"] is True
    assert resp.data["created_count"] >= 1

    # Check notification exists in DB
    notifs = Notification.objects.filter(user=user, category=NotificationCategory.BUDGET)
    assert notifs.count() == 1
    assert "Budget Warning" in notifs.first().title

    # Idempotent re-run should not create duplicates
    resp2 = client.post("/api/v1/notifications/evaluate/")
    assert resp2.status_code == 200
    assert resp2.data["created_count"] == 0
