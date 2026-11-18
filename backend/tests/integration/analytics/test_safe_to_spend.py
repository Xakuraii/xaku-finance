"""Integration tests for Safe-to-Spend and Daily Spending Allowance calculation engines."""

from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.analytics.daily_allowance import calculate_daily_allowance
from apps.analytics.models import ObligationCadence, ObligationKind, RecurringObligation
from apps.analytics.safe_to_spend import calculate_safe_to_spend
from apps.budgets.models import BudgetPeriodType
from apps.budgets.services.create import create_budget
from apps.categories.models import Category, CategoryKind
from apps.identity.services.registration import register_user
from apps.savings.services import create_savings_goal, record_savings_contribution
from apps.transactions.services.create import create_transaction
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def sts_setup(db):
    user = register_user(
        email="sts_test@example.com",
        password="StrongPassword123!",
        display_name="STS User",
    )
    ws = user.workspace

    checking = create_account(
        workspace=ws,
        actor=user,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        is_spendable=True,
    )
    savings = create_account(
        workspace=ws,
        actor=user,
        name="Emergency Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
        is_spendable=False,
    )

    today = date(2026, 11, 15)

    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="2000.00",
        as_of=today,
        actor=user,
    )
    create_opening_balance(
        workspace=ws,
        account=savings,
        amount="5000.00",
        as_of=today,
        actor=user,
    )

    return {
        "user": user,
        "workspace": ws,
        "checking": checking,
        "savings": savings,
        "today": today,
    }


def test_safe_to_spend_full_itemization(sts_setup):
    ws = sts_setup["workspace"]
    user = sts_setup["user"]
    checking = sts_setup["checking"]
    savings = sts_setup["savings"]
    today = sts_setup["today"]

    cat = Category.objects.create(workspace=ws, name="Utilities", kind=CategoryKind.EXPENSE)

    # 1. Pending outflow: $200 on Checking
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=checking.id,
        category_id=cat.id,
        amount="200.00",
        currency="USD",
        occurred_on=today,
        title="Pending utility bill",
        status="pending",
    )

    # 2. Reserved obligation: $300 due on Nov 20 (within month horizon)
    RecurringObligation.objects.create(
        workspace=ws,
        name="Internet Subscription",
        kind=ObligationKind.BILL,
        amount_minor=30000,
        currency_code="USD",
        cadence=ObligationCadence.MONTHLY,
        next_due_date=today + timedelta(days=5),
        is_reserved=True,
    )

    # 3. Savings Goal earmark: $500 on spendable checking
    goal = create_savings_goal(
        workspace=ws,
        actor=user,
        name="Vacation Fund",
        target_amount="1000.00",
        currency="USD",
        strategy="earmark",
    )
    record_savings_contribution(
        workspace=ws,
        goal=goal,
        actor=user,
        amount="500.00",
        kind="earmark",
        account_id=str(checking.id),
    )

    # Calculate safe to spend
    # Checking = 2000.00
    # Pending = -200.00
    # Reserved bill = -300.00
    # Earmark = -500.00
    # Safe to spend = 2000 - 200 - 300 - 500 = 1000.00
    res = calculate_safe_to_spend(ws, horizon_type="period_end", as_of=today)

    assert res.currency == "USD"
    assert res.display == "1000.00"
    assert res.raw == "1000.00"
    assert res.is_negative is False
    assert res.components["spendable_balance"] == "2000.00"
    assert res.components["pending_outflows"] == "-200.00"
    assert res.components["reserved_bills"] == "-300.00"
    assert res.components["planned_savings"] == "-500.00"

    # Accounts check
    assert len(res.accounts) == 1
    assert res.accounts[0]["name"] == "Main Checking"
    assert res.accounts[0]["included"] is True

    # Excluded accounts check
    assert len(res.excluded_accounts) == 1
    assert res.excluded_accounts[0]["name"] == "Emergency Savings"
    assert res.excluded_accounts[0]["reason"] == "not_spendable"


def test_safe_to_spend_negative_flooring(sts_setup):
    ws = sts_setup["workspace"]
    today = sts_setup["today"]

    # Add a huge bill of $2,500 when spendable balance is $2,000
    RecurringObligation.objects.create(
        workspace=ws,
        name="Quarterly Insurance",
        kind=ObligationKind.BILL,
        amount_minor=250000,
        currency_code="USD",
        cadence=ObligationCadence.QUARTERLY,
        next_due_date=today + timedelta(days=3),
        is_reserved=True,
    )

    res = calculate_safe_to_spend(ws, horizon_type="period_end", as_of=today)
    # Raw is 2000 - 2500 = -500.00
    assert res.raw == "-500.00"
    assert res.display == "0.00"
    assert res.is_negative is True


def test_daily_allowance_calculation(sts_setup):
    ws = sts_setup["workspace"]
    user = sts_setup["user"]
    checking = sts_setup["checking"]
    today = sts_setup["today"]  # Nov 15 (16 days remaining in Nov: 15..30 inclusive)

    cat_groc = Category.objects.create(workspace=ws, name="Groceries", kind=CategoryKind.EXPENSE)
    cat_rent = Category.objects.create(workspace=ws, name="Rent", kind=CategoryKind.EXPENSE)

    # Budget 1: Groceries $480 flexible
    b_groc = create_budget(
        workspace=ws,
        name="Groceries Budget",
        category_id=cat_groc.id,
        amount="480.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        is_flexible=True,
        starts_on=date(2026, 11, 1),
    )

    # Budget 2: Rent $1,200 non-flexible
    b_rent = create_budget(
        workspace=ws,
        name="Rent Budget",
        category_id=cat_rent.id,
        amount="1200.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        is_flexible=False,
        starts_on=date(2026, 11, 1),
    )

    # 16 days left in November (15 to 30 inclusive)
    # Flexible budget remaining = 480.00
    # Allowance = 480.00 / 16 = 30.00/day
    res = calculate_daily_allowance(ws, as_of=today)
    assert res.state == "ok"
    assert res.remaining_days == 16
    assert res.flexible_remaining == "480.00"
    assert res.allowance == "30.00"
    assert len(res.budgets) == 1
    assert res.budgets[0]["name"] == "Groceries Budget"
    assert len(res.excluded) == 1
    assert res.excluded[0]["name"] == "Rent Budget"


def test_daily_allowance_over_budget(sts_setup):
    ws = sts_setup["workspace"]
    user = sts_setup["user"]
    checking = sts_setup["checking"]
    today = sts_setup["today"]

    cat_dine = Category.objects.create(workspace=ws, name="Dining Out", kind=CategoryKind.EXPENSE)

    b_dine = create_budget(
        workspace=ws,
        name="Dining Budget",
        category_id=cat_dine.id,
        amount="100.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        is_flexible=True,
        starts_on=date(2026, 11, 1),
    )

    # Spend $150 on dining -> over budget by $50
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=checking.id,
        category_id=cat_dine.id,
        amount="150.00",
        currency="USD",
        occurred_on=today,
        title="Fancy dinner",
        status="completed",
    )

    res = calculate_daily_allowance(ws, as_of=today)
    assert res.state == "over_budget"
    assert res.allowance == "0.00"
    assert "Dining Budget" in res.explanation
