"""Integration tests for Budget creation and split-aware spending calculation."""

from __future__ import annotations

from datetime import date

import pytest

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.budgets.models import BudgetPeriodType
from apps.budgets.services.create import create_budget
from apps.budgets.services.spending import calculate_budget_period_spending
from apps.categories.models import CategoryKind
from apps.categories.services import create_category
from apps.transactions.services.create import SplitInput, create_transaction
from tests.factories.users import UserFactory


@pytest.fixture
def budget_test_setup():
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

    food_cat = create_category(
        workspace=ws,
        name="Food & Dining",
        kind=CategoryKind.EXPENSE,
    )
    restaurants_cat = create_category(
        workspace=ws,
        name="Restaurants",
        kind=CategoryKind.EXPENSE,
        parent_id=food_cat.id,
    )
    shopping_cat = create_category(
        workspace=ws,
        name="Shopping",
        kind=CategoryKind.EXPENSE,
    )

    return {
        "user": user,
        "workspace": ws,
        "account": account,
        "food_cat": food_cat,
        "restaurants_cat": restaurants_cat,
        "shopping_cat": shopping_cat,
    }


@pytest.mark.django_db
def test_budget_creation_and_initial_period(budget_test_setup):
    s = budget_test_setup
    ws = s["workspace"]

    budget = create_budget(
        workspace=ws,
        name="Dining Budget",
        category_id=s["food_cat"].id,
        amount="300.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        starts_on=date(2026, 11, 1),
    )

    assert budget.name == "Dining Budget"
    assert budget.base_amount_minor == 30000
    assert budget.periods.count() == 1

    period = budget.periods.first()
    assert period is not None
    assert period.period_start == date(2026, 11, 1)
    assert period.period_end == date(2026, 11, 30)
    assert period.total_available_minor == 30000
    assert period.spent_minor == 0
    assert period.remaining_minor == 30000


@pytest.mark.django_db
def test_split_aware_spending_calculation(budget_test_setup):
    s = budget_test_setup
    ws = s["workspace"]
    user = s["user"]
    acc = s["account"]

    budget = create_budget(
        workspace=ws,
        name="Dining Budget",
        category_id=s["food_cat"].id,
        amount="300.00",
        currency="USD",
        period_type=BudgetPeriodType.MONTHLY,
        starts_on=date(2026, 11, 1),
    )
    period = budget.periods.first()
    assert period is not None

    # 1. Direct expense on parent category ($50)
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="50.00",
        currency="USD",
        occurred_on=date(2026, 11, 10),
        title="Direct Grocery",
        category_id=s["food_cat"].id,
    )

    # 2. Split expense ($100 total): $40 on child category Restaurants, $60 on Shopping
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="100.00",
        currency="USD",
        occurred_on=date(2026, 11, 15),
        title="Costco Combo",
        splits=[
            SplitInput(category_id=s["restaurants_cat"].id, amount="40.00"),
            SplitInput(category_id=s["shopping_cat"].id, amount="60.00"),
        ],
    )

    # 3. Expense in December (outside period boundary)
    create_transaction(
        workspace=ws,
        actor=user,
        kind="expense",
        account_id=acc.id,
        amount="75.00",
        currency="USD",
        occurred_on=date(2026, 12, 5),
        title="Future Dining",
        category_id=s["food_cat"].id,
    )

    # Compute spending for November period: $50 direct + $40 split = $90 (9,000 minor)
    spent = calculate_budget_period_spending(period)
    assert spent == 9000
    assert period.base_amount_minor - spent == 21000
