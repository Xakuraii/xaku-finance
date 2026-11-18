"""Performance query count budget tests for Phase 3 Financial Planning endpoints."""

from __future__ import annotations

from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.analytics.emergency_fund import update_emergency_fund_config
from apps.categories.models import Category, CategoryKind
from apps.debts.services import create_liability
from apps.savings.services import create_savings_goal, record_savings_contribution
from apps.transactions.models import (
    NecessityClassification,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from apps.transactions.services.opening import create_opening_balance
from tests.factories.users import UserFactory


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def phase3_populated_workspace():
    user = UserFactory()
    ws = user.workspace

    checking = create_account(
        workspace=ws,
        actor=user,
        name="Primary Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
    )
    savings = create_account(
        workspace=ws,
        actor=user,
        name="High Yield Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
    )
    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="10000.00",
        as_of=date.today(),
        actor=user,
    )
    create_opening_balance(
        workspace=ws,
        account=savings,
        amount="5000.00",
        as_of=date.today(),
        actor=user,
    )

    # 1. Create multiple savings goals and earmarks
    for i in range(3):
        goal = create_savings_goal(
            workspace=ws,
            actor=user,
            name=f"Savings Goal {i}",
            target_amount="2000.00",
            currency="USD",
            linked_account_id=str(savings.id),
        )
        record_savings_contribution(
            workspace=ws,
            actor=user,
            goal=goal,
            kind="earmark",
            amount="500.00",
            account_id=str(savings.id),
        )

    # 2. Create multiple liabilities (debts)
    for i in range(3):
        create_liability(
            workspace=ws,
            actor=user,
            name=f"Auto Loan {i}",
            original_principal="5000.00",
            currency="USD",
            interest_rate="0.05",
            initial_disbursement_account_id=str(checking.id),
        )

    # 3. Create essential expenses for emergency fund calculation
    groceries = Category.objects.create(
        workspace=ws,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
    )
    for i in range(5):
        Transaction.objects.create(
            workspace=ws,
            account=checking,
            category=groceries,
            title=f"Grocery Trip {i}",
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.COMPLETED,
            amount_minor=20000,
            currency_id="USD",
            occurred_on=date.today(),
            necessity=NecessityClassification.ESSENTIAL,
        )

    update_emergency_fund_config(
        workspace=ws,
        target_months=6,
        designated_account_id=str(savings.id),
    )

    return user


@pytest.mark.django_db
def test_savings_goals_list_query_budget(
    api, phase3_populated_workspace, django_assert_num_queries
):
    user = phase3_populated_workspace
    api.force_authenticate(user)

    # Fetching list of savings goals with prefetched allocations and linked accounts
    # Budget: <= 20 queries for complete list with progress calculation (no N+1 explosion)
    with django_assert_num_queries(20, exact=False):
        res = api.get("/api/v1/savings-goals/")
        assert res.status_code == 200
        assert len(res.json()) == 3


@pytest.mark.django_db
def test_debts_list_query_budget(api, phase3_populated_workspace, django_assert_num_queries):
    user = phase3_populated_workspace
    api.force_authenticate(user)

    # Fetching list of liabilities with ledger account balances and projections
    # Budget: <= 15 queries (no N+1 explosion)
    with django_assert_num_queries(15, exact=False):
        res = api.get("/api/v1/debts/")
        assert res.status_code == 200
        assert len(res.json()) == 3


@pytest.mark.django_db
def test_emergency_fund_status_query_budget(
    api, phase3_populated_workspace, django_assert_num_queries
):
    user = phase3_populated_workspace
    api.force_authenticate(user)

    # Fetching emergency fund status (config + essential spending aggregate + earmark check)
    # Budget: <= 12 queries
    with django_assert_num_queries(12, exact=False):
        res = api.get("/api/v1/emergency-fund/")
        assert res.status_code == 200
        assert res.json()["target_months"] == 6
