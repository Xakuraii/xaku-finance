"""Performance query count budget tests for Phase 2 endpoints."""

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
from apps.transactions.services.transfer import create_transfer
from tests.factories.users import UserFactory


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def phase2_populated_workspace():
    user = UserFactory()
    ws = user.workspace

    acc1 = create_account(
        workspace=ws,
        actor=user,
        name="Checking USD",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="5000.00",
        opening_balance_date=date(2026, 11, 1),
    )
    acc2 = create_account(
        workspace=ws,
        actor=user,
        name="Savings USD",
        account_type=AccountType.SAVINGS,
        currency="USD",
        opening_balance="1000.00",
        opening_balance_date=date(2026, 11, 1),
    )

    parent_cat = create_category(workspace=ws, name="Food", kind=CategoryKind.EXPENSE)
    create_category(
        workspace=ws,
        name="Restaurants",
        kind=CategoryKind.EXPENSE,
        parent_id=parent_cat.id,
    )
    create_category(
        workspace=ws,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
        parent_id=parent_cat.id,
    )

    # 3 transfers
    for i in range(3):
        create_transfer(
            workspace=ws,
            actor=user,
            source_account_id=acc1.id,
            destination_account_id=acc2.id,
            amount=f"10{i}.00",
            occurred_on=date(2026, 11, 10 + i),
        )

    # 1 budget
    create_budget(
        workspace=ws,
        name="Monthly Food",
        category_id=parent_cat.id,
        amount="500.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        starts_on=date(2026, 11, 1),
    )

    # Tagged transactions
    for i in range(5):
        create_transaction(
            workspace=ws,
            actor=user,
            kind="expense",
            account_id=acc1.id,
            amount=f"2{i}.00",
            currency="USD",
            occurred_on=date(2026, 11, 15),
            title=f"Meal {i}",
            category_id=parent_cat.id,
            tags=["dining", "weekend"],
            necessity="lifestyle",
        )

    return user


@pytest.mark.django_db
def test_transfers_list_query_budget(api, phase2_populated_workspace, django_assert_num_queries):
    user = phase2_populated_workspace
    api.force_authenticate(user)

    # select_related accounts, categories, currencies
    with django_assert_num_queries(1):
        res = api.get("/api/v1/transfers/")
        assert res.status_code == 200
        assert len(res.json()["results"]) == 3


@pytest.mark.django_db
def test_categories_tree_list_query_budget(api, phase2_populated_workspace, django_assert_num_queries):
    user = phase2_populated_workspace
    api.force_authenticate(user)

    # Prefetched children
    with django_assert_num_queries(4):
        res = api.get("/api/v1/categories/")
        assert res.status_code == 200
        assert len(res.json()) >= 1


@pytest.mark.django_db
def test_tag_analytics_query_budget(api, phase2_populated_workspace, django_assert_num_queries):
    user = phase2_populated_workspace
    api.force_authenticate(user)

    with django_assert_num_queries(4):
        res = api.get("/api/v1/tags/analytics/")
        assert res.status_code == 200
        assert res.json()["total_expense_minor"] > 0
