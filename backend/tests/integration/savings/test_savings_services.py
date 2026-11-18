"""Tests for savings domain services and selectors."""

from datetime import date, timedelta

import pytest

from apps.accounts.models import AccountType
from apps.accounts.selectors import account_balance
from apps.accounts.services import create_account
from apps.identity.services.registration import register_user
from apps.savings.models import (
    ContributionKind,
    GoalStatus,
    GoalStrategy,
)
from apps.savings.selectors import (
    get_account_unallocated_balance,
    get_goal_progress,
    get_goal_projection,
)
from apps.savings.services import (
    AllocationCapacityError,
    GoalArchivedError,
    SavingsError,
    archive_savings_goal,
    create_savings_goal,
    record_savings_contribution,
    restore_savings_goal,
    update_savings_goal,
)
from apps.transactions.services.opening import create_opening_balance


@pytest.fixture
def funded_savings_setup(db):
    user = register_user(
        email="savings_svc_test@example.com",
        password="StrongPassword123!",
        display_name="Savings Services User",
    )
    ws = user.workspace
    account = create_account(
        workspace=ws,
        actor=user,
        name="High Yield Savings",
        account_type=AccountType.SAVINGS,
        currency="USD",
    )
    # Fund account with $1,000 opening balance
    create_opening_balance(
        workspace=ws,
        account=account,
        amount="1000.00",
        as_of=date.today(),
        actor=user,
    )
    return user, ws, account


@pytest.mark.django_db
def test_create_and_update_savings_goal(funded_savings_setup):
    user, ws, account = funded_savings_setup

    target_date = date.today() + timedelta(days=90)
    goal = create_savings_goal(
        workspace=ws,
        actor=user,
        name="MacBook Pro",
        target_amount="2000.00",
        currency="USD",
        target_date=target_date,
        linked_account_id=str(account.id),
        strategy=GoalStrategy.LINKED_ACCOUNT,
    )
    assert goal.id is not None
    assert goal.target_amount_minor == 200000
    assert goal.status == GoalStatus.ACTIVE

    # Update metadata
    updated = update_savings_goal(
        goal=goal,
        actor=user,
        name="MacBook M4 Pro",
        target_amount="2500.00",
    )
    assert updated.name == "MacBook M4 Pro"
    assert updated.target_amount_minor == 250000

    # Linked account currency mismatch
    khr_account = create_account(
        workspace=ws,
        actor=user,
        name="KHR Account",
        account_type=AccountType.SAVINGS,
        currency="KHR",
    )
    with pytest.raises(SavingsError, match="currency"):
        create_savings_goal(
            workspace=ws,
            actor=user,
            name="Mismatch Goal",
            target_amount="100.00",
            currency="USD",
            linked_account_id=str(khr_account.id),
        )


@pytest.mark.django_db
def test_earmark_contribution_and_capacity_constraint(funded_savings_setup):
    user, ws, account = funded_savings_setup

    goal = create_savings_goal(
        workspace=ws,
        actor=user,
        name="Emergency Stash",
        target_amount="1000.00",
        currency="USD",
        linked_account_id=str(account.id),
    )

    # Initial state: account has 1000.00, unallocated 1000.00
    assert account_balance(account=account).amount_minor == 100000
    assert get_account_unallocated_balance(account) == 100000

    # 1. Earmark $300.00 (30,000 minor)
    contrib = record_savings_contribution(
        workspace=ws,
        actor=user,
        goal=goal,
        kind=ContributionKind.EARMARK,
        amount="300.00",
        account_id=str(account.id),
        note="First buffer",
    )
    assert contrib.amount_minor == 30000
    assert contrib.kind == ContributionKind.EARMARK

    # Balance is still $1000.00! Earmarks NEVER change ledger balance
    assert account_balance(account=account).amount_minor == 100000
    # But unallocated capacity is now $700.00
    assert get_account_unallocated_balance(account) == 70000

    progress = get_goal_progress(goal)
    assert progress.current_amount_minor == 30000
    assert progress.progress_percent == 30.0
    assert not progress.is_overfunded

    # 2. Try to earmark $800.00 -> should FAIL because available unallocated is only 700.00
    with pytest.raises(AllocationCapacityError, match="exceeds available unallocated capacity"):
        record_savings_contribution(
            workspace=ws,
            actor=user,
            goal=goal,
            kind=ContributionKind.EARMARK,
            amount="800.00",
            account_id=str(account.id),
        )

    # 3. Earmark $700.00 exactly -> meets goal target $1000.00
    record_savings_contribution(
        workspace=ws,
        actor=user,
        goal=goal,
        kind=ContributionKind.EARMARK,
        amount="700.00",
        account_id=str(account.id),
    )
    goal.refresh_from_db()
    assert goal.status == GoalStatus.ACHIEVED
    assert goal.achieved_at is not None
    assert get_account_unallocated_balance(account) == 0


@pytest.mark.django_db
def test_withdrawal_and_overfunding(funded_savings_setup):
    user, ws, account = funded_savings_setup

    goal = create_savings_goal(
        workspace=ws,
        actor=user,
        name="Gift Fund",
        target_amount="500.00",
        currency="USD",
        linked_account_id=str(account.id),
    )

    # Earmark 600.00 -> overfunded
    record_savings_contribution(
        workspace=ws,
        actor=user,
        goal=goal,
        kind=ContributionKind.EARMARK,
        amount="600.00",
        account_id=str(account.id),
    )
    progress = get_goal_progress(goal)
    assert progress.is_overfunded is True
    assert progress.overfunded_amount_minor == 10000
    assert progress.progress_percent == 100.0

    # Withdraw 200.00
    withdrawal = record_savings_contribution(
        workspace=ws,
        actor=user,
        goal=goal,
        kind=ContributionKind.WITHDRAWAL,
        amount="200.00",
        account_id=str(account.id),
        note="Bought present",
    )
    assert withdrawal.amount_minor == -20000
    progress = get_goal_progress(goal)
    assert progress.current_amount_minor == 40000
    assert not progress.is_overfunded
    assert progress.progress_percent == 80.0


@pytest.mark.django_db
def test_archive_releases_earmarks_without_moving_funds(funded_savings_setup):
    user, ws, account = funded_savings_setup

    goal = create_savings_goal(
        workspace=ws,
        actor=user,
        name="Project Car",
        target_amount="1000.00",
        currency="USD",
        linked_account_id=str(account.id),
    )
    record_savings_contribution(
        workspace=ws,
        actor=user,
        goal=goal,
        kind=ContributionKind.EARMARK,
        amount="500.00",
        account_id=str(account.id),
    )
    assert get_account_unallocated_balance(account) == 50000

    # Archive goal
    archive_savings_goal(goal=goal, actor=user)
    goal.refresh_from_db()
    assert goal.is_archived is True
    assert goal.status == GoalStatus.ARCHIVED

    # Allocation zeroed out and unallocated capacity restored to 1,000.00
    assert get_account_unallocated_balance(account) == 100000
    assert account_balance(account=account).amount_minor == 100000

    # Contributing to archived goal raises error
    with pytest.raises(GoalArchivedError):
        record_savings_contribution(
            workspace=ws,
            actor=user,
            goal=goal,
            kind=ContributionKind.EARMARK,
            amount="100.00",
            account_id=str(account.id),
        )

    # Restore goal
    restore_savings_goal(goal=goal, actor=user)
    goal.refresh_from_db()
    assert goal.is_archived is False
    assert goal.status == GoalStatus.ACTIVE


@pytest.mark.django_db
def test_savings_projection(funded_savings_setup):
    user, ws, account = funded_savings_setup

    # Target 3 months from now, target 900.00
    target_date = date.today() + timedelta(days=91)
    goal = create_savings_goal(
        workspace=ws,
        actor=user,
        name="Summer Trip",
        target_amount="900.00",
        currency="USD",
        target_date=target_date,
        linked_account_id=str(account.id),
    )
    record_savings_contribution(
        workspace=ws,
        actor=user,
        goal=goal,
        kind=ContributionKind.EARMARK,
        amount="300.00",
        account_id=str(account.id),
    )

    proj = get_goal_projection(goal)
    assert proj.remaining_amount_minor == 60000
    assert proj.days_remaining is not None and proj.days_remaining > 80
    assert proj.required_monthly_contribution is not None
    # 600.00 / 3 months ≈ 200.00
    assert proj.required_monthly_contribution.startswith("200.")
