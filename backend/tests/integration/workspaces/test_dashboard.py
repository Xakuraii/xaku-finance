from datetime import date

import pytest

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.budgets.models import BudgetPeriodType
from apps.budgets.services.create import create_budget
from apps.categories.models import Category, CategoryKind
from apps.common.models import Currency
from apps.identity.models import User
from apps.savings.models import SavingsGoal
from apps.transactions.services.create import create_transaction
from apps.workspaces.dashboard_registry import CANONICAL_WIDGETS, DEFAULT_WIDGET_ORDER
from apps.workspaces.models import Workspace
from apps.workspaces.services import (
    assemble_dashboard,
    get_user_layout,
    reset_user_layout,
    update_user_layout,
)


@pytest.fixture
def dashboard_user(db):
    user = User.objects.create_user(email="dashuser@example.com", password="password123456")
    ws = Workspace.objects.create(
        owner=user,
        name="Personal",
        reporting_currency=Currency.objects.get(code="USD"),
        timezone="UTC",
    )
    user.workspace = ws
    return user


def test_default_layout_initialization(dashboard_user):
    layout = get_user_layout(dashboard_user)
    assert len(layout) == len(DEFAULT_WIDGET_ORDER)
    keys = [w["key"] for w in layout]
    assert keys == DEFAULT_WIDGET_ORDER
    for w in layout:
        assert w["enabled"] is True
        assert w["key"] in CANONICAL_WIDGETS


def test_update_and_reset_layout(dashboard_user):
    custom = [
        {"key": "net_worth", "enabled": True},
        {"key": "safe_to_spend", "enabled": False},
        {"key": "total_balance", "enabled": True},
    ]
    updated = update_user_layout(dashboard_user, custom)
    assert len(updated) == 3
    assert updated[0]["key"] == "net_worth"
    assert updated[1]["enabled"] is False

    re_fetched = get_user_layout(dashboard_user)
    assert [w["key"] for w in re_fetched] == ["net_worth", "safe_to_spend", "total_balance"]

    # Reset
    reset = reset_user_layout(dashboard_user)
    assert len(reset) == len(DEFAULT_WIDGET_ORDER)
    assert [w["key"] for w in reset] == DEFAULT_WIDGET_ORDER


def test_assemble_dashboard_empty_workspace(dashboard_user):
    ws = dashboard_user.workspace
    data = assemble_dashboard(
        user=dashboard_user,
        workspace=ws,
        as_of=date(2026, 11, 15),
    )

    assert data["period"]["start"] == "2026-11-01"
    assert data["period"]["end"] == "2026-11-30"
    assert data["currency"] == "USD"
    assert "widget_order" in data
    assert data["balances"] == []
    assert data["converted_total"]["amount"] == "0.00"

    # Empty states must be descriptive, not fabricated
    assert data["budget_overview"]["state"] == "empty"
    assert data["budget_overview"]["reason"] == "no_budgets"

    assert data["savings_progress"]["state"] == "empty"
    assert data["savings_progress"]["reason"] == "no_goals"

    assert data["recent_transactions"]["state"] == "empty"
    assert data["recent_transactions"]["reason"] == "no_transactions"


def test_assemble_dashboard_with_data(dashboard_user):
    ws = dashboard_user.workspace
    today = date(2026, 11, 15)

    # 1. Create checking account with opening balance
    acc = create_account(
        workspace=ws,
        actor=dashboard_user,
        name="Main Checking",
        account_type=AccountType.CHECKING,
        currency="USD",
        opening_balance="3000.00",
        opening_balance_date=date(2026, 11, 2),
        is_spendable=True,
    )

    # 2. Expense transaction
    cat_groc = Category.objects.create(workspace=ws, name="Groceries", kind=CategoryKind.EXPENSE)
    create_transaction(
        workspace=ws,
        actor=dashboard_user,
        kind="expense",
        account_id=acc.id,
        amount="150.00",
        currency="USD",
        category_id=cat_groc.id,
        occurred_on=date(2026, 11, 10),
        title="Weekly Groceries",
    )

    # 3. Budget
    create_budget(
        workspace=ws,
        name="Groceries Budget",
        category_id=cat_groc.id,
        amount="400.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        starts_on=date(2026, 11, 1),
    )

    # 4. Savings Goal
    from apps.savings.models import ContributionKind, GoalStrategy, SavingsContribution
    goal = SavingsGoal.objects.create(
        workspace=ws,
        name="Vacation",
        target_amount_minor=100000,
        currency_code="USD",
        strategy=GoalStrategy.EARMARK,
    )
    SavingsContribution.objects.create(
        workspace=ws,
        goal=goal,
        account=acc,
        created_by=dashboard_user,
        kind=ContributionKind.ADJUSTMENT,
        amount_minor=20000,
        currency_code="USD",
        occurred_on=date(2026, 11, 5),
    )

    data = assemble_dashboard(
        user=dashboard_user,
        workspace=ws,
        as_of=today,
    )

    # Balances
    assert len(data["balances"]) == 1
    assert data["balances"][0]["currency"] == "USD"
    assert data["balances"][0]["total"] == "2850.00"
    assert data["converted_total"]["amount"] == "2850.00"

    # Net Worth
    assert data["net_worth"]["amount"] == "2850.00"

    # Safe-to-Spend
    assert data["safe_to_spend"]["display"] == "2850.00"

    # Daily allowance
    assert "daily_allowance" in data

    # Budget Overview
    assert data["budget_overview"]["state"] == "ok"
    assert len(data["budget_overview"]["items"]) == 1
    assert data["budget_overview"]["items"][0]["spent"] == "150.00"

    # Savings progress
    assert data["savings_progress"]["state"] == "ok"
    assert len(data["savings_progress"]["items"]) == 1
    assert data["savings_progress"]["items"][0]["contributed"] == "200.00"

    # Recent transactions
    assert data["recent_transactions"]["state"] == "ok"
    assert len(data["recent_transactions"]["items"]) >= 1
