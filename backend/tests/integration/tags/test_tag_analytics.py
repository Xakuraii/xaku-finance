"""Integration tests for Tag and Necessity analytics."""

from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.categories.models import Category, CategoryKind
from apps.transactions.services.create import create_transaction
from tests.factories.users import UserFactory


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def analytics_setup():
    user = UserFactory()
    ws = user.workspace

    acc = create_account(
        workspace=ws,
        actor=user,
        name="Main Account",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="5000.00",
        opening_balance_date=date(2026, 11, 1),
    )

    groceries_cat = Category.objects.create(
        workspace=ws,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
    )
    utilities_cat = Category.objects.create(
        workspace=ws,
        name="Utilities",
        kind=CategoryKind.EXPENSE,
    )

    # 1. $100 essential expense tagged "home", "family"
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="100.00",
        currency="USD",
        occurred_on=date(2026, 11, 15),
        title="Weekly groceries",
        category_id=groceries_cat.id,
        necessity="essential",
        tags=["home", "family"],
    )

    # 2. $50 lifestyle expense tagged "work"
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="50.00",
        currency="USD",
        occurred_on=date(2026, 11, 16),
        title="Coffee with team",
        category_id=groceries_cat.id,
        necessity="lifestyle",
        tags=["work"],
    )

    # 3. $50 important expense tagged "home"
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="50.00",
        currency="USD",
        occurred_on=date(2026, 11, 17),
        title="Internet bill",
        category_id=utilities_cat.id,
        necessity="important",
        tags=["home"],
    )

    return {"user": user, "workspace": ws, "account": acc}


@pytest.mark.django_db
def test_tag_and_necessity_analytics_api(api_client, analytics_setup):
    s = analytics_setup
    api_client.force_authenticate(s["user"])

    res = api_client.get("/api/v1/tags/analytics/")
    assert res.status_code == 200
    data = res.json()

    # Total expenses = $200.00 (20,000 minor units)
    assert data["total_expense_minor"] == 20000
    assert data["total_expense"] == "200.00"

    # Tag breakdowns
    tags_data = {t["tag"]: t for t in data["by_tag"]}
    assert "home" in tags_data
    # "home" is on $100 and $50 -> $150.00 (15,000 minor)
    assert tags_data["home"]["amount_minor"] == 15000
    assert tags_data["home"]["amount"] == "150.00"
    assert tags_data["home"]["count"] == 2

    # Necessity breakdown
    necessity_data = {n["necessity"]: n for n in data["by_necessity"]}
    assert necessity_data["essential"]["amount_minor"] == 10000
    assert necessity_data["essential"]["percentage"] == 50.0
    assert necessity_data["important"]["amount_minor"] == 5000
    assert necessity_data["important"]["percentage"] == 25.0
    assert necessity_data["lifestyle"]["amount_minor"] == 5000
    assert necessity_data["lifestyle"]["percentage"] == 25.0


@pytest.mark.django_db
def test_filter_transactions_by_tag(api_client, analytics_setup):
    s = analytics_setup
    api_client.force_authenticate(s["user"])

    # Filter by tag "work"
    res = api_client.get("/api/v1/transactions/?tag=work")
    assert res.status_code == 200
    results = res.json()["results"]
    assert len(results) == 1
    assert results[0]["title"] == "Coffee with team"
