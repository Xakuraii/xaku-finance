"""Performance query count budget tests for Phase 5 User Experience endpoints."""

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
from apps.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
)
from apps.notifications.services.notifications import ensure_user_preferences
from apps.transactions.models import Transaction, TransactionStatus, TransactionType
from apps.transactions.services.opening import create_opening_balance
from apps.workspaces.services.dashboard import reset_user_layout
from tests.factories.users import UserFactory


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def phase5_populated_workspace():
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

    create_liability(
        workspace=ws,
        actor=user,
        name="Auto Loan",
        original_principal="3000.00",
        currency="USD",
        initial_disbursement_account_id=str(checking.id),
    )

    RecurringObligation.objects.create(
        workspace=ws,
        name="Monthly Rent",
        kind=ObligationKind.BILL,
        amount_minor=100000,
        currency_code="USD",
        cadence=ObligationCadence.MONTHLY,
        next_due_date=date.today() + timedelta(days=3),
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

    for i in range(5):
        Transaction.objects.create(
            workspace=ws,
            account=checking,
            category=cat_groc,
            title=f"Grocery item {i}",
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.COMPLETED,
            amount_minor=2500,
            currency_id="USD",
            occurred_on=date.today(),
        )

    # Notifications & Preferences
    ensure_user_preferences(user)
    for i in range(3):
        Notification.objects.create(
            user=user,
            workspace=ws,
            category=NotificationCategory.BUDGET,
            severity=NotificationSeverity.INFO,
            title=f"Notice {i}",
            body=f"Test notice {i}",
            dedupe_key=f"perf:notif:{i}",
        )

    reset_user_layout(user)
    return user


@pytest.mark.django_db
def test_dashboard_assembled_query_budget(
    api, phase5_populated_workspace, django_assert_num_queries
):
    user = phase5_populated_workspace
    api.force_authenticate(user)

    # Dashboard assembly compiles 9 distinct widgets across ledger, budgets, obligations
    # Should execute within 75 queries
    with django_assert_num_queries(75, exact=False):
        res = api.get("/api/v1/dashboard/")
        assert res.status_code == 200
        data = res.json()
        assert "widget_order" in data
        assert "balances" in data


@pytest.mark.django_db
def test_dashboard_layout_query_budget(api, phase5_populated_workspace, django_assert_num_queries):
    user = phase5_populated_workspace
    api.force_authenticate(user)

    with django_assert_num_queries(8, exact=False):
        res = api.get("/api/v1/dashboard/layout/")
        assert res.status_code == 200
        assert "widgets" in res.json()


@pytest.mark.django_db
def test_notifications_query_budget(api, phase5_populated_workspace, django_assert_num_queries):
    user = phase5_populated_workspace
    api.force_authenticate(user)

    with django_assert_num_queries(6, exact=False):
        res = api.get("/api/v1/notifications/")
        assert res.status_code == 200
        assert len(res.json()) >= 3


@pytest.mark.django_db
def test_unread_count_query_budget(api, phase5_populated_workspace, django_assert_num_queries):
    user = phase5_populated_workspace
    api.force_authenticate(user)

    with django_assert_num_queries(4, exact=False):
        res = api.get("/api/v1/notifications/unread-count/")
        assert res.status_code == 200
        assert res.json()["unread_count"] >= 3


@pytest.mark.django_db
def test_notification_preferences_query_budget(
    api, phase5_populated_workspace, django_assert_num_queries
):
    user = phase5_populated_workspace
    api.force_authenticate(user)

    with django_assert_num_queries(6, exact=False):
        res = api.get("/api/v1/notification-preferences/")
        assert res.status_code == 200


@pytest.mark.django_db
def test_me_and_workspace_summary_query_budget(
    api, phase5_populated_workspace, django_assert_num_queries
):
    user = phase5_populated_workspace
    api.force_authenticate(user)

    with django_assert_num_queries(6, exact=False):
        res = api.get("/api/v1/me/")
        assert res.status_code == 200

    with django_assert_num_queries(12, exact=False):
        res = api.get("/api/v1/workspace/summary/")
        assert res.status_code == 200
        assert res.json()["accounts_count"] >= 2
