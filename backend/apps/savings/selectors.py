"""Savings selectors: goal progress, account unallocated balances, and projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from django.db.models import Sum

from apps.accounts.selectors import account_balance
from apps.common.money import Money
from apps.savings.models import SavingsAllocation, SavingsGoal

if TYPE_CHECKING:
    from apps.accounts.models import Account


@dataclass(frozen=True)
class GoalProgress:
    current_amount_minor: int
    target_amount_minor: int
    progress_percent: float
    is_overfunded: bool
    overfunded_amount_minor: int
    current_amount: str
    target_amount: str


@dataclass(frozen=True)
class GoalProjection:
    goal_id: str
    currency: str
    target_amount_minor: int
    current_amount_minor: int
    remaining_amount_minor: int
    target_date: str | None
    days_remaining: int | None
    months_remaining: float | None
    required_monthly_contribution: str | None
    projected_completion_date: str | None


def get_goal_progress(goal: SavingsGoal) -> GoalProgress:
    """Calculate the current funded progress for a savings goal."""
    current_minor = (
        SavingsAllocation.objects.filter(goal=goal).aggregate(s=Sum("allocated_minor"))["s"] or 0
    )
    target_minor = goal.target_amount_minor

    pct = round((current_minor / target_minor) * 100.0, 2) if target_minor > 0 else 0.0
    progress_percent = min(100.0, pct)
    is_overfunded = current_minor > target_minor
    overfunded_minor = max(0, current_minor - target_minor)

    curr_str = Money(current_minor, goal.currency_code, 2).serialize()
    targ_str = Money(target_minor, goal.currency_code, 2).serialize()

    return GoalProgress(
        current_amount_minor=current_minor,
        target_amount_minor=target_minor,
        progress_percent=progress_percent,
        is_overfunded=is_overfunded,
        overfunded_amount_minor=overfunded_minor,
        current_amount=curr_str,
        target_amount=targ_str,
    )


def get_account_unallocated_balance(account: Account) -> int:
    """Calculate the balance of an account that has not been earmarked to any active goal."""
    total_balance = account_balance(account=account).amount_minor
    total_allocated = (
        SavingsAllocation.objects.filter(
            account=account,
            goal__is_archived=False,
        ).aggregate(s=Sum("allocated_minor"))["s"]
        or 0
    )
    return max(0, total_balance - total_allocated)


def get_goal_projection(goal: SavingsGoal) -> GoalProjection:
    """Calculate projection and required regular contributions to meet target by target_date."""
    progress = get_goal_progress(goal)
    remaining_minor = max(0, goal.target_amount_minor - progress.current_amount_minor)

    days_remaining = None
    months_remaining = None
    required_monthly = None
    target_date_str = None

    if goal.target_date:
        target_date_str = goal.target_date.isoformat()
        today = date.today()
        days = (goal.target_date - today).days
        if days > 0:
            days_remaining = days
            months = days / 30.4375  # average days in month
            months_remaining = round(months, 1)
            if months > 0 and remaining_minor > 0:
                monthly_minor = int(round(remaining_minor / months))
                required_monthly = Money(monthly_minor, goal.currency_code, 2).serialize()
            elif remaining_minor == 0:
                required_monthly = "0.00"
        else:
            days_remaining = 0
            months_remaining = 0.0
            required_monthly = Money(remaining_minor, goal.currency_code, 2).serialize()

    return GoalProjection(
        goal_id=str(goal.id),
        currency=goal.currency_code,
        target_amount_minor=goal.target_amount_minor,
        current_amount_minor=progress.current_amount_minor,
        remaining_amount_minor=remaining_minor,
        target_date=target_date_str,
        days_remaining=days_remaining,
        months_remaining=months_remaining,
        required_monthly_contribution=required_monthly,
        projected_completion_date=target_date_str,
    )
