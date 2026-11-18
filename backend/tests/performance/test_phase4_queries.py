"""Performance query count budget tests for Phase 4 Financial Intelligence endpoints."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.analytics.models import ObligationCadence, ObligationKind, RecurringObligation
from apps.budgets.models import BudgetPeriodType
from apps.budgets.services.create import create_budget
from apps.categories.models import Category, CategoryKind
from apps.debts.services import create_liability
from apps.transactions.models import Transaction, TransactionStatus, TransactionType
from apps.transactions.services.opening import create_opening_balance
from tests.factories.users import UserFactory


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def phase4_populated_workspace():
    user = UserFactory()
    ws = user.workspace

    checking = create_account(
        workspace=ws,
        actor=user,
        name="Primary Checking",
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
        amount="15000.00",
        as_of=date.today(),
        actor=user,
    )
    create_opening_balance(
        workspace=ws,
        account=savings,
        amount="8000.00",
        as_of=date.today(),
        actor=user,
    )

    create_liability(
        workspace=ws,
        actor=user,
        name="Car Loan",
        original_principal="5000.00",
        currency="USD",
        initial_disbursement_account_id=str(checking.id),
    )

    RecurringObligation.objects.create(
        workspace=ws,
        name="Monthly Rent",
        kind=ObligationKind.BILL,
        amount_minor=120000,
        currency_code="USD",
        cadence=ObligationCadence.MONTHLY,
        next_due_date=date.today() + timedelta(days=5),
        is_reserved=True,
    )

    cat_groc = Category.objects.create(workspace=ws, name="Groceries", kind=CategoryKind.EXPENSE)
    create_budget(
        workspace=ws,
        name="Groceries Budget",
        category_id=cat_groc.id,
        amount="500.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        is_flexible=True,
    )

    # Some transactions
    for i in range(5):
        Transaction.objects.create(
            workspace=ws,
            account=checking,
            category=cat_groc,
            title=f"Grocery Shopping {i}",
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.COMPLETED,
            amount_minor=5000,
            currency_id="USD",
            occurred_on=date.today(),
        )

    return user


@pytest.mark.django_db
def test_net_worth_fresh_query_budget(api, phase4_populated_workspace, django_assert_num_queries):
    user = phase4_populated_workspace
    api.force_authenticate(user)

    # Fresh computation over ledger postings and snapshot write (<= 15 queries)
    with django_assert_num_queries(15, exact=False):
        res = api.get("/api/v1/net-worth/")
        assert res.status_code == 200
        assert res.json()["computed_from"] == "ledger"


@pytest.mark.django_db
def test_net_worth_cached_query_budget(api, phase4_populated_workspace, django_assert_num_queries):
    user = phase4_populated_workspace
    api.force_authenticate(user)

    # 1. Warm cache
    api.get("/api/v1/net-worth/")

    # 2. Cached retrieval from NetWorthSnapshot
    # Budget: <= 5 queries (auth + user + workspace + snapshot + prior snapshot)
    with django_assert_num_queries(5, exact=False):
        res = api.get("/api/v1/net-worth/")
        assert res.status_code == 200
        assert res.json()["computed_from"] == "snapshot"


@pytest.mark.django_db
def test_safe_to_spend_query_budget(api, phase4_populated_workspace, django_assert_num_queries):
    user = phase4_populated_workspace
    api.force_authenticate(user)

    # Calculation across accounts, pending transactions, obligations, and earmarks
    with django_assert_num_queries(10, exact=False):
        res = api.get("/api/v1/safe-to-spend/")
        assert res.status_code == 200
        assert "components" in res.json()


@pytest.mark.django_db
def test_daily_allowance_query_budget(api, phase4_populated_workspace, django_assert_num_queries):
    user = phase4_populated_workspace
    api.force_authenticate(user)

    # Querying flexible budgets, periods, and spending
    with django_assert_num_queries(10, exact=False):
        res = api.get("/api/v1/daily-allowance/")
        assert res.status_code == 200
        assert res.json()["state"] == "ok"


@pytest.mark.django_db
def test_reports_income_query_budget(api, phase4_populated_workspace, django_assert_num_queries):
    user = phase4_populated_workspace
    api.force_authenticate(user)

    with django_assert_num_queries(8, exact=False):
        res = api.get("/api/v1/reports/income/")
        assert res.status_code == 200
        assert "reconciliation" in res.json()


@pytest.mark.django_db
def test_reports_categories_query_budget(
    api, phase4_populated_workspace, django_assert_num_queries
):
    user = phase4_populated_workspace
    api.force_authenticate(user)

    with django_assert_num_queries(8, exact=False):
        res = api.get("/api/v1/reports/categories/")
        assert res.status_code == 200
        assert "reconciliation" in res.json()


@pytest.mark.django_db
def test_reports_cashflow_query_budget(api, phase4_populated_workspace, django_assert_num_queries):
    user = phase4_populated_workspace
    api.force_authenticate(user)

    with django_assert_num_queries(8, exact=False):
        res = api.get("/api/v1/reports/cashflow/")
        assert res.status_code == 200
        assert "reconciliation" in res.json()
