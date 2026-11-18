from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.budgets.services.create import create_budget
from apps.categories.models import Category, CategoryKind
from apps.common.models import Currency
from apps.identity.models import User
from apps.transactions.models import Transaction, TransactionType
from apps.workspaces.models import Workspace


@pytest.fixture
def settings_user(db):
    user = User.objects.create_user(email="settings_user@example.com", password="password123456")
    usd = Currency.objects.get(code="USD")
    khr = Currency.objects.get(code="KHR")
    ws = Workspace.objects.create(
        owner=user,
        name="Personal Finances",
        reporting_currency=usd,
        timezone="UTC",
        week_start=1,
    )
    user.workspace = ws

    client = APIClient()
    client.force_authenticate(user=user)

    return {"user": user, "ws": ws, "client": client, "usd": usd, "khr": khr}


def test_me_get_and_patch(settings_user):
    client = settings_user["client"]

    # Initial GET auto-creates profile
    resp = client.get("/api/v1/me/")
    assert resp.status_code == 200
    assert resp.data["email"] == "settings_user@example.com"
    assert resp.data["display_name"] == "settings_user"
    assert resp.data["theme"] == "system"

    # PATCH profile
    patch_payload = {
        "display_name": "Finance Pro",
        "theme": "dark",
        "timezone": "America/New_York",
        "week_start": 7,
    }
    resp = client.patch("/api/v1/me/", data=patch_payload, format="json")
    assert resp.status_code == 200
    assert resp.data["display_name"] == "Finance Pro"
    assert resp.data["theme"] == "dark"
    assert resp.data["timezone"] == "America/New_York"
    assert resp.data["week_start"] == 7

    # Reject invalid timezone
    bad_resp = client.patch("/api/v1/me/", data={"timezone": "Invalid/Zone"}, format="json")
    assert bad_resp.status_code == 400


def test_workspace_settings_get_and_patch(settings_user):
    client = settings_user["client"]

    resp = client.get("/api/v1/workspace/")
    assert resp.status_code == 200
    assert resp.data["name"] == "Personal Finances"
    assert resp.data["reporting_currency"] == "USD"

    # Patch workspace settings
    patch_payload = {
        "name": "Global Treasury",
        "reporting_currency": "KHR",
        "timezone": "Europe/London",
        "week_start": 1,
    }
    resp = client.patch("/api/v1/workspace/", data=patch_payload, format="json")
    assert resp.status_code == 200
    assert resp.data["name"] == "Global Treasury"
    assert resp.data["reporting_currency"] == "KHR"
    assert resp.data["timezone"] == "Europe/London"

    # Reject blank name
    bad_resp = client.patch("/api/v1/workspace/", data={"name": "   "}, format="json")
    assert bad_resp.status_code == 400


def test_workspace_summary_counts(settings_user):
    user = settings_user["user"]
    ws = settings_user["ws"]
    client = settings_user["client"]
    curr = settings_user["usd"]

    # Initial summary
    resp = client.get("/api/v1/workspace/summary/")
    assert resp.status_code == 200
    assert resp.data["accounts_count"] == 0
    assert resp.data["transactions_count"] == 0
    assert resp.data["budgets_count"] == 0

    # Add account, category, budget, transaction
    acc = create_account(
        workspace=ws,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency=curr.code,
        actor=user,
        opened_on=date(2026, 1, 1),
    )

    cat = Category.objects.create(workspace=ws, name="Utilities", kind=CategoryKind.EXPENSE)
    create_budget(
        workspace=ws,
        name="Utility Budget",
        category_id=cat.id,
        amount="150.00",
        currency=curr.code,
    )

    Transaction.objects.create(
        workspace=ws,
        account=acc,
        currency=curr,
        category=cat,
        amount_minor=5000,
        transaction_type=TransactionType.EXPENSE,
        occurred_on=date(2026, 11, 10),
        description="Electricity bill",
        created_by=user,
    )

    # Verify counts reflect active records
    resp = client.get("/api/v1/workspace/summary/")
    assert resp.status_code == 200
    assert resp.data["accounts_count"] == 1
    assert resp.data["budgets_count"] == 1
    assert resp.data["transactions_count"] == 1
