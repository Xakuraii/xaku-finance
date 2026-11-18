"""Savings domain services.

Handles goal lifecycle, earmarks with row-locked capacity checks, and contributions.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Account
from apps.accounts.selectors import account_balance
from apps.common.money import Money
from apps.savings.models import (
    ContributionKind,
    GoalStatus,
    GoalStrategy,
    SavingsAllocation,
    SavingsContribution,
    SavingsGoal,
)

if TYPE_CHECKING:
    from apps.identity.models import User
    from apps.transactions.models import Transaction
    from apps.workspaces.models import Workspace


class SavingsError(ValueError):
    """Base error for savings operations."""


class AllocationCapacityError(SavingsError):
    """Raised when an earmark exceeds the unallocated available balance of the backing account."""


class GoalArchivedError(SavingsError):
    """Raised when attempting to contribute to an archived goal."""


def create_savings_goal(
    *,
    workspace: Workspace,
    actor: User,
    name: str,
    target_amount: str | Decimal | int,
    currency: str,
    target_date: date | None = None,
    linked_account_id: str | None = None,
    strategy: str = "linked_account",
    notes: str | None = None,
) -> SavingsGoal:
    """Create a new savings goal."""
    if isinstance(target_amount, (int, Decimal)):
        money = Money(
            int(target_amount)
            if isinstance(target_amount, int)
            else int(Decimal(target_amount) * 100),
            currency,
            2,
        )
    else:
        money = Money.parse(str(target_amount), currency, 2)

    if money.amount_minor <= 0:
        raise SavingsError("Target amount must be strictly positive.")

    linked_account = None
    if strategy == GoalStrategy.LINKED_ACCOUNT or linked_account_id:
        if not linked_account_id:
            raise SavingsError("A linked account is required for the 'linked_account' strategy.")
        try:
            linked_account = Account.objects.get(
                id=linked_account_id,
                workspace=workspace,
                is_archived=False,
            )
        except Account.DoesNotExist as exc:
            raise SavingsError("Linked account not found or archived.") from exc

        if linked_account.currency_id != currency.upper():
            raise SavingsError(
                f"Linked account currency ({linked_account.currency_id}) "
                f"does not match goal currency ({currency})."
            )

    goal = SavingsGoal.objects.create(
        workspace=workspace,
        name=name.strip(),
        target_amount_minor=money.amount_minor,
        currency_code=currency.upper(),
        target_date=target_date,
        linked_account=linked_account,
        strategy=strategy,
        notes=notes,
        status=GoalStatus.ACTIVE,
    )
    return goal


def update_savings_goal(
    *,
    goal: SavingsGoal,
    actor: User,
    name: str | None = None,
    target_amount: str | Decimal | None = None,
    target_date: date | None = None,
    notes: str | None = None,
    status: str | None = None,
) -> SavingsGoal:
    """Update metadata or target of a savings goal."""
    if name is not None:
        goal.name = name.strip()
    if target_amount is not None:
        money = Money.parse(str(target_amount), goal.currency_code, 2)
        if money.amount_minor <= 0:
            raise SavingsError("Target amount must be strictly positive.")
        goal.target_amount_minor = money.amount_minor
    if target_date is not None:
        goal.target_date = target_date
    if notes is not None:
        goal.notes = notes
    if status is not None:
        goal.status = status
    goal.save()
    return goal


@transaction.atomic
def archive_savings_goal(*, goal: SavingsGoal, actor: User) -> SavingsGoal:
    """Archive a savings goal and release all associated earmarks without moving funds."""
    goal.is_archived = True
    goal.status = GoalStatus.ARCHIVED
    goal.save(update_fields=["is_archived", "status", "updated_at"])

    # Release all allocations for this goal (zero out allocated_minor)
    SavingsAllocation.objects.filter(goal=goal).update(allocated_minor=0)
    return goal


@transaction.atomic
def restore_savings_goal(*, goal: SavingsGoal, actor: User) -> SavingsGoal:
    """Restore an archived savings goal."""
    goal.is_archived = False
    goal.status = GoalStatus.ACTIVE
    goal.save(update_fields=["is_archived", "status", "updated_at"])
    return goal


@transaction.atomic
def record_savings_contribution(
    *,
    workspace: Workspace,
    actor: User,
    goal: SavingsGoal,
    kind: str,
    amount: str | Decimal | int,
    account_id: str,
    transfer_transaction: Transaction | None = None,
    occurred_on: date | None = None,
    note: str | None = None,
) -> SavingsContribution:
    """Record a savings contribution, enforcing allocation capacity under a row lock."""
    if goal.is_archived or goal.status == GoalStatus.ARCHIVED:
        raise GoalArchivedError("Cannot contribute to an archived goal.")

    if isinstance(amount, (int, Decimal)):
        money = Money(
            int(amount) if isinstance(amount, int) else int(Decimal(amount) * 100),
            goal.currency_code,
            2,
        )
    else:
        money = Money.parse(str(amount), goal.currency_code, 2)

    abs_amount_minor = abs(money.amount_minor)
    if abs_amount_minor == 0:
        raise SavingsError("Contribution amount cannot be zero.")

    # Acquire lock on the account to prevent race conditions on allocation
    try:
        account = Account.objects.select_for_update().get(
            id=account_id, workspace=workspace, is_archived=False
        )
    except Account.DoesNotExist as exc:
        raise SavingsError("Account not found or archived.") from exc

    if account.currency_id != goal.currency_code:
        raise SavingsError(
            f"Account currency ({account.currency_id}) "
            f"does not match goal currency ({goal.currency_code})."
        )

    event_date = occurred_on or date.today()

    # Get or lock existing allocation for this (goal, account)
    allocation, _ = SavingsAllocation.objects.select_for_update().get_or_create(
        workspace=workspace,
        goal=goal,
        account=account,
        defaults={"allocated_minor": 0, "currency_code": goal.currency_code},
    )

    if kind == ContributionKind.EARMARK:
        # Check unallocated available balance on the account
        current_balance = account_balance(account=account).amount_minor
        other_allocations_sum = (
            SavingsAllocation.objects.filter(
                account=account,
                goal__is_archived=False,
            )
            .exclude(id=allocation.id)
            .aggregate(s=Sum("allocated_minor"))["s"]
            or 0
        )
        total_after = other_allocations_sum + allocation.allocated_minor + abs_amount_minor
        if total_after > current_balance:
            available_capacity = max(
                0, current_balance - (other_allocations_sum + allocation.allocated_minor)
            )
            raise AllocationCapacityError(
                f"Earmark of {abs_amount_minor} minor units exceeds available "
                f"unallocated capacity ({available_capacity}) on account '{account.name}'."
            )

        allocation.allocated_minor += abs_amount_minor
        allocation.save(update_fields=["allocated_minor", "updated_at"])

        contribution = SavingsContribution.objects.create(
            workspace=workspace,
            goal=goal,
            account=account,
            kind=ContributionKind.EARMARK,
            amount_minor=abs_amount_minor,
            currency_code=goal.currency_code,
            occurred_on=event_date,
            note=note,
            created_by=actor,
        )

    elif kind == ContributionKind.WITHDRAWAL:
        if allocation.allocated_minor < abs_amount_minor:
            raise SavingsError(
                f"Cannot withdraw {abs_amount_minor} minor units; goal has only "
                f"{allocation.allocated_minor} allocated from this account."
            )
        allocation.allocated_minor -= abs_amount_minor
        allocation.save(update_fields=["allocated_minor", "updated_at"])

        contribution = SavingsContribution.objects.create(
            workspace=workspace,
            goal=goal,
            account=account,
            kind=ContributionKind.WITHDRAWAL,
            amount_minor=-abs_amount_minor,
            currency_code=goal.currency_code,
            occurred_on=event_date,
            note=note,
            created_by=actor,
        )

    elif kind == ContributionKind.TRANSFER_IN:
        if not transfer_transaction:
            raise SavingsError(
                "Transfer-in contribution requires an associated transfer transaction."
            )
        allocation.allocated_minor += abs_amount_minor
        allocation.save(update_fields=["allocated_minor", "updated_at"])

        contribution = SavingsContribution.objects.create(
            workspace=workspace,
            goal=goal,
            account=account,
            transfer_transaction=transfer_transaction,
            kind=ContributionKind.TRANSFER_IN,
            amount_minor=abs_amount_minor,
            currency_code=goal.currency_code,
            occurred_on=event_date,
            note=note,
            created_by=actor,
        )

    elif kind == ContributionKind.ADJUSTMENT:
        signed_amount = money.amount_minor
        new_allocated = allocation.allocated_minor + signed_amount
        if new_allocated < 0:
            raise SavingsError("Adjustment cannot reduce allocated amount below zero.")
        allocation.allocated_minor = new_allocated
        allocation.save(update_fields=["allocated_minor", "updated_at"])

        contribution = SavingsContribution.objects.create(
            workspace=workspace,
            goal=goal,
            account=account,
            kind=ContributionKind.ADJUSTMENT,
            amount_minor=signed_amount,
            currency_code=goal.currency_code,
            occurred_on=event_date,
            note=note,
            created_by=actor,
        )
    else:
        raise SavingsError(f"Unknown contribution kind: {kind}")

    # Check goal achievement
    total_goal_allocated = (
        SavingsAllocation.objects.filter(goal=goal).aggregate(s=Sum("allocated_minor"))["s"] or 0
    )
    if total_goal_allocated >= goal.target_amount_minor and goal.status == GoalStatus.ACTIVE:
        goal.status = GoalStatus.ACHIEVED
        goal.achieved_at = timezone.now()
        goal.save(update_fields=["status", "achieved_at", "updated_at"])

    return contribution
