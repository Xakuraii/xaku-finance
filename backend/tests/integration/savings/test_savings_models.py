"""Tests for savings models: goals, contributions, and allocations."""

from datetime import date

import pytest
from django.db import IntegrityError, transaction

from apps.accounts.models import AccountType
from apps.accounts.services import create_account
from apps.identity.services.registration import register_user
from apps.savings.models import (
    ContributionKind,
    GoalStatus,
    GoalStrategy,
    SavingsAllocation,
    SavingsContribution,
    SavingsGoal,
)
from apps.transactions.models import Transaction, TransactionType


@pytest.fixture
def user_and_workspace(db):
    user = register_user(
        email="savings_test@example.com",
        password="StrongPassword123!",
        display_name="Savings User",
    )
    ws = user.workspace
    account = create_account(
        workspace=ws,
        actor=user,
        name="Emergency Savings Account",
        account_type=AccountType.SAVINGS,
        currency="USD",
    )
    return user, ws, account


@pytest.mark.django_db
def test_savings_goal_creation_and_constraints(user_and_workspace):
    user, ws, account = user_and_workspace

    # Valid goal with linked account
    goal = SavingsGoal.objects.create(
        workspace=ws,
        name="Emergency Fund",
        target_amount_minor=100000,
        currency_code="USD",
        target_date=date(2027, 1, 1),
        linked_account=account,
        strategy=GoalStrategy.LINKED_ACCOUNT,
    )
    assert goal.id is not None
    assert goal.status == GoalStatus.ACTIVE
    assert goal.target_amount == "1000.00"

    # Non-positive target amount violates constraint
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SavingsGoal.objects.create(
                workspace=ws,
                name="Invalid Target",
                target_amount_minor=0,
                currency_code="USD",
                linked_account=account,
                strategy=GoalStrategy.LINKED_ACCOUNT,
            )

    # Linked account strategy requires linked_account
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SavingsGoal.objects.create(
                workspace=ws,
                name="Missing Account",
                target_amount_minor=50000,
                currency_code="USD",
                linked_account=None,
                strategy=GoalStrategy.LINKED_ACCOUNT,
            )


@pytest.mark.django_db
def test_savings_contribution_constraints(user_and_workspace):
    user, ws, account = user_and_workspace

    goal = SavingsGoal.objects.create(
        workspace=ws,
        name="Vacation Fund",
        target_amount_minor=50000,
        currency_code="USD",
        linked_account=account,
        strategy=GoalStrategy.LINKED_ACCOUNT,
    )

    # Valid earmark contribution
    contrib = SavingsContribution.objects.create(
        workspace=ws,
        goal=goal,
        account=account,
        kind=ContributionKind.EARMARK,
        amount_minor=10000,
        currency_code="USD",
        occurred_on=date.today(),
        created_by=user,
    )
    assert contrib.id is not None

    # Earmark cannot have a transfer_transaction
    dummy_tx = Transaction.objects.create(
        workspace=ws,
        account=account,
        title="Test Transaction",
        transaction_type=TransactionType.TRANSFER,
        amount_minor=1000,
        currency_id="USD",
        occurred_on=date.today(),
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SavingsContribution.objects.create(
                workspace=ws,
                goal=goal,
                account=account,
                transfer_transaction=dummy_tx,
                kind=ContributionKind.EARMARK,
                amount_minor=5000,
                currency_code="USD",
                occurred_on=date.today(),
                created_by=user,
            )

    # Withdrawal must be negative
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SavingsContribution.objects.create(
                workspace=ws,
                goal=goal,
                account=account,
                kind=ContributionKind.WITHDRAWAL,
                amount_minor=5000,  # positive is illegal
                currency_code="USD",
                occurred_on=date.today(),
                created_by=user,
            )


@pytest.mark.django_db
def test_savings_allocation_constraints(user_and_workspace):
    user, ws, account = user_and_workspace

    goal = SavingsGoal.objects.create(
        workspace=ws,
        name="New Laptop",
        target_amount_minor=200000,
        currency_code="USD",
        linked_account=account,
        strategy=GoalStrategy.LINKED_ACCOUNT,
    )

    alloc = SavingsAllocation.objects.create(
        workspace=ws,
        goal=goal,
        account=account,
        allocated_minor=50000,
        currency_code="USD",
    )
    assert alloc.id is not None

    # Negative allocation violates constraint
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SavingsAllocation.objects.create(
                workspace=ws,
                goal=SavingsGoal.objects.create(
                    workspace=ws,
                    name="Second Goal",
                    target_amount_minor=10000,
                    currency_code="USD",
                    linked_account=account,
                ),
                account=account,
                allocated_minor=-100,
                currency_code="USD",
            )

    # Unique constraint on (goal, account)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            SavingsAllocation.objects.create(
                workspace=ws,
                goal=goal,
                account=account,
                allocated_minor=10000,
                currency_code="USD",
            )
