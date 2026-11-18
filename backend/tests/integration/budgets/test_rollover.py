"""Integration tests for the positive-only rollover engine."""

from __future__ import annotations

from datetime import date

import pytest

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.budgets.models import BudgetPeriodStatus, BudgetPeriodType, BudgetRollover
from apps.budgets.services.create import create_budget
from apps.budgets.services.rollover import close_budget_period
from apps.categories.models import CategoryKind
from apps.categories.services import create_category
from apps.transactions.services.create import create_transaction
from tests.factories.users import UserFactory


@pytest.fixture
def rollover_test_setup():
    user = UserFactory()
    ws = user.workspace

    account = create_account(
        workspace=ws,
        actor=user,
        name="Checking Account",
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

    return {
        "user": user,
        "workspace": ws,
        "account": account,
        "groceries_cat": groceries_cat,
    }


@pytest.mark.django_db
def test_positive_rollover_transfers_forward(rollover_test_setup):
    s = rollover_test_setup
    ws = s["workspace"]
    user = s["user"]
    acc = s["account"]

    budget = create_budget(
        workspace=ws,
        name="Monthly Groceries",
        category_id=s["groceries_cat"].id,
        amount="200.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        rollover_enabled=True,
        starts_on=date(2026, 11, 1),
    )
    p1 = budget.periods.first()
    assert p1 is not None

    # Spend $140 in November ($60 unused)
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="140.00",
        currency="USD",
        occurred_on=date(2026, 11, 20),
        title="Supermarket run",
        category_id=s["groceries_cat"].id,
    )

    # Close Period 1
    closed_p1, next_p2 = close_budget_period(workspace=ws, period_id=p1.id)

    assert closed_p1.status == BudgetPeriodStatus.CLOSED
    assert closed_p1.spent_minor == 14000
    assert closed_p1.rollover_out_minor == 6000

    assert next_p2 is not None
    assert next_p2.period_start == date(2026, 12, 1)
    assert next_p2.period_end == date(2026, 12, 31)
    assert next_p2.base_amount_minor == 20000
    assert next_p2.rollover_in_minor == 6000
    assert next_p2.total_available_minor == 26000
    assert next_p2.remaining_minor == 26000

    # Rollover audit trail
    ro = BudgetRollover.objects.get(budget_period=next_p2)
    assert ro.source_period_id == closed_p1.id
    assert ro.amount_minor == 6000


@pytest.mark.django_db
def test_overspending_produces_zero_negative_rollover(rollover_test_setup):
    s = rollover_test_setup
    ws = s["workspace"]
    user = s["user"]
    acc = s["account"]

    budget = create_budget(
        workspace=ws,
        name="Monthly Groceries",
        category_id=s["groceries_cat"].id,
        amount="200.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        rollover_enabled=True,
        starts_on=date(2026, 11, 1),
    )
    p1 = budget.periods.first()
    assert p1 is not None

    # Overspend $250 in November ($50 over budget)
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="250.00",
        currency="USD",
        occurred_on=date(2026, 11, 22),
        title="Excess Groceries",
        category_id=s["groceries_cat"].id,
    )

    closed_p1, next_p2 = close_budget_period(workspace=ws, period_id=p1.id)

    assert closed_p1.spent_minor == 25000
    # STRICT ACCOUNTING RULE: Rollover is positive only. Rollover out MUST be 0!
    assert closed_p1.rollover_out_minor == 0

    assert next_p2 is not None
    assert next_p2.rollover_in_minor == 0
    assert next_p2.total_available_minor == 20000


@pytest.mark.django_db
def test_rollover_cap_enforced(rollover_test_setup):
    s = rollover_test_setup
    ws = s["workspace"]
    user = s["user"]
    acc = s["account"]

    budget = create_budget(
        workspace=ws,
        name="Monthly Groceries",
        category_id=s["groceries_cat"].id,
        amount="200.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        rollover_enabled=True,
        rollover_cap="40.00",  # Max rollover 4,000 minor
        starts_on=date(2026, 11, 1),
    )
    p1 = budget.periods.first()
    assert p1 is not None

    # Spend only $100 ($100 unused)
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="100.00",
        currency="USD",
        occurred_on=date(2026, 11, 10),
        title="Light Groceries",
        category_id=s["groceries_cat"].id,
    )

    closed_p1, next_p2 = close_budget_period(workspace=ws, period_id=p1.id)

    assert closed_p1.spent_minor == 10000
    # Unspent was $100 (10,000 minor), but cap is $40 (4,000 minor)
    assert closed_p1.rollover_out_minor == 4000
    assert next_p2 is not None
    assert next_p2.rollover_in_minor == 4000
    assert next_p2.total_available_minor == 24000


@pytest.mark.django_db
def test_closed_period_is_idempotent(rollover_test_setup):
    s = rollover_test_setup
    ws = s["workspace"]

    budget = create_budget(
        workspace=ws,
        name="Monthly Groceries",
        category_id=s["groceries_cat"].id,
        amount="200.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        starts_on=date(2026, 11, 1),
    )
    p1 = budget.periods.first()
    assert p1 is not None

    closed_p1, next_p2 = close_budget_period(workspace=ws, period_id=p1.id)
    assert closed_p1.status == BudgetPeriodStatus.CLOSED

    # Calling close again on already closed period
    again_p1, again_next = close_budget_period(workspace=ws, period_id=p1.id)
    assert again_p1.status == BudgetPeriodStatus.CLOSED
    assert again_next is None
    # No duplicate periods created
    assert budget.periods.count() == 2
