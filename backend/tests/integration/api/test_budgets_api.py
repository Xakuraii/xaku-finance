"""Integration tests for the Budgets REST API endpoints."""

from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.budgets.models import BudgetPeriodType
from apps.budgets.services.create import create_budget
from apps.categories.models import CategoryKind
from apps.categories.services import create_category
from apps.transactions.services.create import create_transaction
from tests.factories.users import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def budget_api_setup():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Main Account",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="5000.00",
        opening_balance_date=date(2026, 11, 1),
    )

    groceries_cat = create_category(
        workspace=ws,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
    )

    budget = create_budget(
        workspace=ws,
        name="Monthly Groceries",
        category_id=groceries_cat.id,
        amount="300.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        rollover_enabled=True,
        starts_on=date(2026, 11, 1),
    )

    return {
        "user": user,
        "workspace": ws,
        "account": account,
        "groceries_cat": groceries_cat,
        "budget": budget,
    }


@pytest.mark.django_db
def test_budgets_api_list_and_create(api_client, budget_api_setup):
    s = budget_api_setup
    api_client.force_authenticate(s["user"])

    # 1. List budgets
    res = api_client.get("/api/v1/budgets/")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["name"] == "Monthly Groceries"
    assert data[0]["base_amount"] == "300.00"
    assert data[0]["current_period"] is not None
    assert data[0]["current_period"]["remaining"] == "300.00"

    # 2. Create another budget
    dining_cat = create_category(
        workspace=s["workspace"],
        name="Dining Out",
        kind=CategoryKind.EXPENSE,
    )
    payload = {
        "name": "Dining Budget",
        "category_id": str(dining_cat.id),
        "amount": "150.00",
        "currency": "USD",
        "period_type": "monthly",
        "rollover_enabled": False,
        "starts_on": "2026-11-01",
    }
    create_res = api_client.post("/api/v1/budgets/", payload, format="json")
    assert create_res.status_code == 201
    created_data = create_res.json()
    assert created_data["name"] == "Dining Budget"
    assert created_data["base_amount"] == "150.00"


@pytest.mark.django_db
def test_budgets_api_overview_and_close_period(api_client, budget_api_setup):
    s = budget_api_setup
    ws = s["workspace"]
    user = s["user"]
    acc = s["account"]
    b = s["budget"]
    api_client.force_authenticate(user)

    # Spend $100 on groceries ($200 remaining out of $300)
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="100.00",
        currency="USD",
        occurred_on=date(2026, 11, 15),
        title="Weekly Shopping",
        category_id=s["groceries_cat"].id,
    )

    # 1. Overview check
    ov_res = api_client.get("/api/v1/budgets/overview/")
    assert ov_res.status_code == 200
    ov_data = ov_res.json()
    assert ov_data["total_budgeted"] == "300.00"
    assert ov_data["total_spent"] == "100.00"
    assert ov_data["total_remaining"] == "200.00"
    assert len(ov_data["budgets"]) == 1
    assert ov_data["budgets"][0]["health_status"] == "on_track"

    # 2. Close active period via API
    close_res = api_client.post(f"/api/v1/budgets/{b.id}/close_period/")
    assert close_res.status_code == 200
    close_data = close_res.json()
    assert close_data["closed_period"]["status"] == "closed"
    assert close_data["closed_period"]["rollover_out"] == "200.00"
    assert close_data["next_period"]["rollover_in"] == "200.00"
    assert close_data["next_period"]["total_available"] == "500.00"
