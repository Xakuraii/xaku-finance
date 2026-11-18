"""Integration tests for Emergency Fund analytics engine."""

from datetime import date, timedelta

import pytest

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.analytics.emergency_fund import (
    calculate_essential_monthly_expenses,
    get_emergency_fund_projection,
    get_emergency_fund_status,
    update_emergency_fund_config,
)
from apps.categories.models import Category, CategoryKind
from apps.identity.services.registration import register_user
from apps.savings.services import create_savings_goal, record_savings_contribution
from apps.transactions.models import (
    NecessityClassification,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def emergency_fund_setup(db):
    user = register_user(
        email="emergency_test@example.com",
        password="StrongPassword123!",
        display_name="Emergency User",
    )
    ws = user.workspace
    checking = create_account(
        workspace=ws,
        actor=user,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
    )
    savings = create_account(
        workspace=ws,
        actor=user,
        name="Emergency Savings Account",
        account_type=AccountType.SAVINGS,
        currency="USD",
    )
    create_opening_balance(
        workspace=ws,
        account=checking,
        amount="5000.00",
        as_of=date.today(),
        actor=user,
    )
    create_opening_balance(
        workspace=ws,
        account=savings,
        amount="2000.00",
        as_of=date.today(),
        actor=user,
    )

    groceries = Category.objects.create(
        workspace=ws,
        name="Groceries",
        kind=CategoryKind.EXPENSE,
    )
    dining = Category.objects.create(
        workspace=ws,
        name="Dining Out",
        kind=CategoryKind.EXPENSE,
    )

    # Seed 3 months of essential transactions ($300/mo = $900 total over 90 days)
    # Month 1: $300 essential
    Transaction.objects.create(
        workspace=ws,
        account=checking,
        category=groceries,
        title="Supermarket Essentials",
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.COMPLETED,
        amount_minor=30000,
        currency_id="USD",
        occurred_on=date.today() - timedelta(days=20),
        necessity=NecessityClassification.ESSENTIAL,
    )
    # Month 2: $300 essential
    Transaction.objects.create(
        workspace=ws,
        account=checking,
        category=groceries,
        title="Groceries Essentials",
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.COMPLETED,
        amount_minor=30000,
        currency_id="USD",
        occurred_on=date.today() - timedelta(days=50),
        necessity=NecessityClassification.ESSENTIAL,
    )
    # Month 3: $300 essential
    Transaction.objects.create(
        workspace=ws,
        account=checking,
        category=groceries,
        title="Farmers Market Essentials",
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.COMPLETED,
        amount_minor=30000,
        currency_id="USD",
        occurred_on=date.today() - timedelta(days=80),
        necessity=NecessityClassification.ESSENTIAL,
    )
    # Non-essential spending (dining out lifestyle - should be excluded)
    Transaction.objects.create(
        workspace=ws,
        account=checking,
        category=dining,
        title="Fancy Restaurant",
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.COMPLETED,
        amount_minor=50000,
        currency_id="USD",
        occurred_on=date.today() - timedelta(days=10),
        necessity=NecessityClassification.LIFESTYLE,
    )

    return user, ws, checking, savings


@pytest.mark.django_db
def test_calculate_essential_monthly_expenses(emergency_fund_setup):
    user, ws, checking, savings = emergency_fund_setup

    # $900 essential expenses over 90 days (~2.956 months) -> ~30400 / ~30000 minor units per month
    monthly = calculate_essential_monthly_expenses(ws, lookback_days=90)
    assert 29500 <= monthly <= 30500


@pytest.mark.django_db
def test_emergency_fund_status_and_override(emergency_fund_setup):
    user, ws, checking, savings = emergency_fund_setup

    update_emergency_fund_config(
        workspace=ws,
        target_months=6,
        designated_account_id=str(savings.id),
        monthly_expense_override="300.00",
    )

    status = get_emergency_fund_status(ws)
    assert status.target_months == 6
    assert status.is_override is True
    assert status.monthly_essential_expense == "300.00"
    # FR-EMG worked example: $300 x 6 = $1,800.00
    assert status.target_amount == "1800.00"
    assert status.target_amount_minor == 180000
    # Current savings from designated account ($2,000.00)
    assert status.current_savings == "2000.00"
    assert status.current_savings_minor == 200000
    assert status.progress_percent == 100.0
    assert status.remaining_target == "0.00"
    assert not status.has_earmark_conflict


@pytest.mark.django_db
def test_emergency_fund_earmark_conflict_detection(emergency_fund_setup):
    user, ws, checking, savings = emergency_fund_setup

    # Savings account has $2,000.00 balance
    # Set emergency fund target to $1,800 (6 mos x $300) linked to savings account
    update_emergency_fund_config(
        workspace=ws,
        target_months=6,
        designated_account_id=str(savings.id),
        monthly_expense_override="300.00",
    )

    # Another goal earmarks $1,500 of the savings account
    other_goal = create_savings_goal(
        workspace=ws,
        actor=user,
        name="Vacation Stash",
        target_amount="2000.00",
        currency="USD",
        linked_account_id=str(savings.id),
    )
    record_savings_contribution(
        workspace=ws,
        actor=user,
        goal=other_goal,
        kind="earmark",
        amount="1500.00",
        account_id=str(savings.id),
    )

    # Now, other earmarks ($1,500) + emergency target ($1,800) = $3,300 > $2,000 account balance
    # FR-EMG-06 conflict MUST be detected!
    status = get_emergency_fund_status(ws)
    assert status.has_earmark_conflict is True
    assert status.conflict_details is not None
    assert "earmarked to other goals" in status.conflict_details


@pytest.mark.django_db
def test_emergency_fund_projection(emergency_fund_setup):
    user, ws, checking, savings = emergency_fund_setup

    # Clear savings balance or set target higher than savings
    update_emergency_fund_config(
        workspace=ws,
        target_months=12,
        designated_account_id=str(savings.id),
        monthly_expense_override="500.00",
    )
    # Target = 12 x 500 = $6,000. Current savings = $2,000. Remaining = $4,000.
    proj = get_emergency_fund_projection(workspace=ws, monthly_contribution="200.00")
    assert proj.remaining_target_minor == 400000
    assert proj.monthly_contribution_minor == 20000
    # $4,000 / $200 = 20 months
    assert proj.months_to_target == 20.0
    assert proj.projected_completion_date is not None
