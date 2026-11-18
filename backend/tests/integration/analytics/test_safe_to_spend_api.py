"""API integration tests for Safe-to-Spend, Daily Allowance, and Recurring Obligations."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.analytics.models import ObligationCadence, ObligationKind, RecurringObligation
from apps.budgets.models import BudgetPeriodType
from apps.budgets.services.create import create_budget
from apps.categories.models import Category, CategoryKind
from apps.identity.services.registration import register_user
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def sts_api_setup(db):
    user = register_user(
        email="sts_api@example.com",
        password="StrongPassword123!",
        display_name="STS API User",
    )
    ws = user.workspace

    checking = create_account(
        workspace=ws,
        actor=user,
        name="Spendable Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        is_spendable=True,
    )
    savings = create_account(
        workspace=ws,
        actor=user,
        name="Vault Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
        is_spendable=False,
    )

    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="3000.00",
        as_of=date.today(),
        actor=user,
    )
    create_opening_balance(
        workspace=ws,
        account=savings,
        amount="10000.00",
        as_of=date.today(),
        actor=user,
    )

    cat = Category.objects.create(workspace=ws, name="Food", kind=CategoryKind.EXPENSE)
    b = create_budget(
        workspace=ws,
        name="Food Budget",
        category_id=cat.id,
        amount="600.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        is_flexible=True,
    )

    client = APIClient()
    client.force_authenticate(user=user)

    return {
        "user": user,
        "workspace": ws,
        "checking": checking,
        "savings": savings,
        "client": client,
        "budget": b,
    }


def test_safe_to_spend_api_endpoint(sts_api_setup):
    client = sts_api_setup["client"]

    res = client.get("/api/v1/safe-to-spend/")
    assert res.status_code == 200
    data = res.json()

    assert data["currency"] == "USD"
    assert data["display"] == "3000.00"
    assert data["raw"] == "3000.00"
    assert "components" in data
    assert "accounts" in data
    assert "excluded_accounts" in data
    assert len(data["accounts"]) == 1
    assert len(data["excluded_accounts"]) == 1


def test_safe_to_spend_horizon_days_param(sts_api_setup):
    client = sts_api_setup["client"]

    res = client.get("/api/v1/safe-to-spend/?horizon_days=14")
    assert res.status_code == 200
    data = res.json()
    assert "next 14 days" in data["horizon"]["label"]


def test_daily_allowance_api_endpoint(sts_api_setup):
    client = sts_api_setup["client"]

    res = client.get("/api/v1/daily-allowance/")
    assert res.status_code == 200
    data = res.json()

    assert data["currency"] == "USD"
    assert data["state"] == "ok"
    assert data["remaining_days"] >= 1
    assert "budgets" in data
    assert len(data["budgets"]) == 1


def test_recurring_obligation_crud(sts_api_setup):
    client = sts_api_setup["client"]
    checking = sts_api_setup["checking"]

    # 1. Create
    payload = {
        "name": "Gym Membership",
        "kind": "subscription",
        "amount": "45.00",
        "currency_code": "USD",
        "account": str(checking.id),
        "cadence": "monthly",
        "next_due_date": (date.today() + timedelta(days=10)).isoformat(),
        "is_reserved": True,
    }
    create_res = client.post("/api/v1/recurring-obligations/", payload)
    assert create_res.status_code == 201
    ob_id = create_res.json()["id"]

    # 2. List
    list_res = client.get("/api/v1/recurring-obligations/")
    assert list_res.status_code == 200
    items = list_res.json()["results"] if "results" in list_res.json() else list_res.json()
    assert len(items) == 1
    assert items[0]["name"] == "Gym Membership"
    assert items[0]["amount"] == "45.00"

    # 3. Update
    patch_res = client.patch(f"/api/v1/recurring-obligations/{ob_id}/", {"amount": "50.00"})
    assert patch_res.status_code == 200
    assert patch_res.json()["amount"] == "50.00"

    # 4. Delete
    del_res = client.delete(f"/api/v1/recurring-obligations/{ob_id}/")
    assert del_res.status_code == 204
