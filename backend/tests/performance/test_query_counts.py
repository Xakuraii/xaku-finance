"""Query count budget tests to detect N+1 regressions on key list endpoints."""

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
def api():
    return APIClient()


@pytest.fixture
def populated_workspace():
    user = UserFactory()
    ws = user.workspace

    # Create 5 accounts
    accounts = []
    for i in range(5):
        acc = create_account(
            workspace=ws,
            actor=user,
            name=f"Checking {i}",
            account_type=AccountType.CHECKING,
            currency="USD",
            opening_balance=f"100{i}.00",
            opening_balance_date=date(2026, 11, 1),
        )
        accounts.append(acc)

    # Create categories
    cat = Category.objects.create(workspace=ws, name="Groceries", kind=CategoryKind.EXPENSE)

    # Create 15 transactions
    for i in range(15):
        create_transaction(
            workspace=ws,
            actor=user,
            kind="expense",
            account_id=accounts[i % len(accounts)].id,
            amount=f"1{i}.50",
            currency="USD",
            occurred_on=date(2026, 11, 16),
            title=f"Expense #{i}",
            category_id=cat.id,
        )

    return user


@pytest.mark.django_db
def test_list_accounts_query_count_budget(api, populated_workspace, django_assert_num_queries):
    user = populated_workspace
    api.force_authenticate(user)

    # Fetch accounts list: query count must not scale with number of accounts
    with django_assert_num_queries(16):  # auth + user + workspace + accounts + per-account balances
        response = api.get("/api/v1/accounts/")
        assert response.status_code == 200
        assert len(response.json()) == 5


@pytest.mark.django_db
def test_list_transactions_query_count_budget(api, populated_workspace, django_assert_num_queries):
    user = populated_workspace
    api.force_authenticate(user)

    # Fetch transactions list with select_related and prefetch_related: must stay under budget
    with django_assert_num_queries(3):
        response = api.get("/api/v1/transactions/")
        assert response.status_code == 200
        assert len(response.json()["results"]) == 20
