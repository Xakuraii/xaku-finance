"""Emergency Fund analytics engine.

Calculates essential spending derivation, override management, and conflict auditing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.db.models import Sum

from apps.accounts.models import Account
from apps.accounts.selectors import account_balance
from apps.analytics.models import EmergencyFundConfig
from apps.common.money import Money
from apps.savings.models import SavingsAllocation, SavingsGoal
from apps.savings.selectors import get_goal_progress
from apps.transactions.models import (
    NecessityClassification,
    Transaction,
    TransactionSplit,
    TransactionStatus,
    TransactionType,
)

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace


@dataclass(frozen=True)
class EmergencyFundStatus:
    target_months: int
    designated_account_id: str | None
    designated_account_name: str | None
    designated_goal_id: str | None
    designated_goal_name: str | None
    is_override: bool
    monthly_essential_expense: str
    monthly_essential_expense_minor: int
    computed_monthly_expense: str
    computed_monthly_expense_minor: int
    override_monthly_expense: str | None
    target_amount: str
    target_amount_minor: int
    current_savings: str
    current_savings_minor: int
    remaining_target: str
    remaining_target_minor: int
    progress_percent: float
    currency: str
    has_earmark_conflict: bool
    conflict_details: str | None
    lookback_days: int


@dataclass(frozen=True)
class EmergencyFundProjection:
    target_amount_minor: int
    current_savings_minor: int
    remaining_target_minor: int
    monthly_contribution_minor: int
    currency: str
    months_to_target: float | None
    days_to_target: int | None
    projected_completion_date: str | None


def get_or_create_emergency_fund_config(workspace: Workspace) -> EmergencyFundConfig:
    """Ensure an EmergencyFundConfig exists for the workspace."""
    config, _ = EmergencyFundConfig.objects.get_or_create(
        workspace=workspace,
        defaults={"target_months": 6, "currency_code": "USD"},
    )
    return config


@transaction.atomic
def update_emergency_fund_config(
    *,
    workspace: Workspace,
    target_months: int | None = None,
    designated_account_id: str | None = None,
    designated_goal_id: str | None = None,
    monthly_expense_override: str | Decimal | int | None = None,
    clear_override: bool = False,
) -> EmergencyFundConfig:
    """Update user configuration for emergency fund coverage and sources."""
    config = get_or_create_emergency_fund_config(workspace)

    if target_months is not None:
        if target_months <= 0:
            raise ValueError("Target coverage months must be strictly positive.")
        config.target_months = target_months

    if designated_account_id is not None:
        if designated_account_id == "":
            config.designated_account = None
        else:
            try:
                acc = Account.objects.get(
                    id=designated_account_id,
                    workspace=workspace,
                    is_archived=False,
                )
                config.designated_account = acc
            except Account.DoesNotExist as exc:
                raise ValueError("Designated account not found or archived.") from exc

    if designated_goal_id is not None:
        if designated_goal_id == "":
            config.designated_goal = None
        else:
            try:
                goal = SavingsGoal.objects.get(
                    id=designated_goal_id,
                    workspace=workspace,
                    is_archived=False,
                )
                config.designated_goal = goal
            except SavingsGoal.DoesNotExist as exc:
                raise ValueError("Designated goal not found or archived.") from exc

    if clear_override:
        config.monthly_expense_override_minor = None
    elif monthly_expense_override is not None:
        if isinstance(monthly_expense_override, (int, Decimal)):
            override_minor = (
                int(monthly_expense_override)
                if isinstance(monthly_expense_override, int)
                else int(Decimal(monthly_expense_override) * 100)
            )
        else:
            override_minor = Money.parse(
                str(monthly_expense_override), config.currency_code, 2
            ).amount_minor
        if override_minor <= 0:
            raise ValueError("Monthly expense override must be strictly positive.")
        config.monthly_expense_override_minor = override_minor

    config.save()
    return config


def calculate_essential_monthly_expenses(
    workspace: Workspace,
    lookback_days: int = 90,
) -> int:
    """Calculate the average monthly essential expenses over the lookback window.

    Queries completed expense transactions and splits classified as 'essential',
    excluding internal transfers and opening balances.
    """
    start_date = date.today() - timedelta(days=lookback_days)

    # 1. Direct non-split essential expenses
    direct_minor = (
        Transaction.objects.filter(
            workspace=workspace,
            status=TransactionStatus.COMPLETED,
            transaction_type=TransactionType.EXPENSE,
            is_split=False,
            is_archived=False,
            occurred_on__gte=start_date,
            necessity=NecessityClassification.ESSENTIAL,
        ).aggregate(s=Sum("amount_minor"))["s"]
        or 0
    )

    # 2. Split items marked essential
    split_minor = (
        TransactionSplit.objects.filter(
            workspace=workspace,
            transaction__status=TransactionStatus.COMPLETED,
            transaction__transaction_type=TransactionType.EXPENSE,
            transaction__is_archived=False,
            transaction__occurred_on__gte=start_date,
            transaction__necessity=NecessityClassification.ESSENTIAL,
        ).aggregate(s=Sum("amount_minor"))["s"]
        or 0
    )

    total_essential_minor = direct_minor + split_minor

    # Normalize to 30.4375 days per average month
    months_in_lookback = max(1.0, lookback_days / 30.4375)
    monthly_minor = int(round(total_essential_minor / months_in_lookback))
    return monthly_minor


def get_emergency_fund_status(
    workspace: Workspace,
    lookback_days: int = 90,
) -> EmergencyFundStatus:
    """Compute complete emergency fund coverage metrics, sources, and conflict warnings."""
    config = get_or_create_emergency_fund_config(workspace)
    currency_code = config.currency_code

    computed_minor = calculate_essential_monthly_expenses(workspace, lookback_days=lookback_days)
    is_override = config.monthly_expense_override_minor is not None
    effective_monthly_minor = (
        config.monthly_expense_override_minor if is_override else computed_minor
    )

    target_minor = effective_monthly_minor * config.target_months

    # Determine current emergency savings
    current_savings_minor = 0
    if config.designated_goal:
        progress = get_goal_progress(config.designated_goal)
        current_savings_minor = progress.current_amount_minor
    elif config.designated_account:
        current_savings_minor = account_balance(account=config.designated_account).amount_minor

    remaining_minor = max(0, target_minor - current_savings_minor)
    pct = round((current_savings_minor / target_minor) * 100.0, 2) if target_minor > 0 else 100.0
    progress_percent = min(100.0, max(0.0, pct))

    # Check for earmark conflicts (FR-EMG-06)
    has_conflict = False
    conflict_details = None

    if config.designated_account:
        acct_bal = account_balance(account=config.designated_account).amount_minor
        other_earmarks_qs = SavingsAllocation.objects.filter(
            account=config.designated_account,
            goal__is_archived=False,
        )
        if config.designated_goal:
            other_earmarks_qs = other_earmarks_qs.exclude(goal=config.designated_goal)

        other_earmarks_minor = other_earmarks_qs.aggregate(s=Sum("allocated_minor"))["s"] or 0

        if other_earmarks_minor + target_minor > acct_bal:
            has_conflict = True
            conflict_details = (
                f"Designated account '{config.designated_account.name}' has "
                f"${(other_earmarks_minor / 100):.2f} earmarked to other goals, "
                f"leaving insufficient balance (${(acct_bal / 100):.2f}) for the full "
                f"${(target_minor / 100):.2f} emergency target."
            )

    return EmergencyFundStatus(
        target_months=config.target_months,
        designated_account_id=str(config.designated_account_id)
        if config.designated_account_id
        else None,
        designated_account_name=config.designated_account.name
        if config.designated_account
        else None,
        designated_goal_id=(str(config.designated_goal_id) if config.designated_goal_id else None),
        designated_goal_name=config.designated_goal.name if config.designated_goal else None,
        is_override=is_override,
        monthly_essential_expense=Money(effective_monthly_minor, currency_code, 2).serialize(),
        monthly_essential_expense_minor=effective_monthly_minor,
        computed_monthly_expense=Money(computed_minor, currency_code, 2).serialize(),
        computed_monthly_expense_minor=computed_minor,
        override_monthly_expense=(
            Money(config.monthly_expense_override_minor, currency_code, 2).serialize()
            if config.monthly_expense_override_minor is not None
            else None
        ),
        target_amount=Money(target_minor, currency_code, 2).serialize(),
        target_amount_minor=target_minor,
        current_savings=Money(current_savings_minor, currency_code, 2).serialize(),
        current_savings_minor=current_savings_minor,
        remaining_target=Money(remaining_minor, currency_code, 2).serialize(),
        remaining_target_minor=remaining_minor,
        progress_percent=progress_percent,
        currency=currency_code,
        has_earmark_conflict=has_conflict,
        conflict_details=conflict_details,
        lookback_days=lookback_days,
    )


def get_emergency_fund_projection(
    workspace: Workspace,
    monthly_contribution: str | Decimal | int,
) -> EmergencyFundProjection:
    """Project timeline and completion date given regular monthly contributions."""
    status = get_emergency_fund_status(workspace)
    currency_code = status.currency

    if isinstance(monthly_contribution, (int, Decimal)):
        contrib_minor = (
            int(monthly_contribution)
            if isinstance(monthly_contribution, int)
            else int(Decimal(monthly_contribution) * 100)
        )
    else:
        contrib_minor = Money.parse(str(monthly_contribution), currency_code, 2).amount_minor

    if contrib_minor <= 0:
        raise ValueError("Monthly contribution must be strictly positive.")

    remaining_minor = status.remaining_target_minor
    if remaining_minor == 0:
        return EmergencyFundProjection(
            target_amount_minor=status.target_amount_minor,
            current_savings_minor=status.current_savings_minor,
            remaining_target_minor=0,
            monthly_contribution_minor=contrib_minor,
            currency=currency_code,
            months_to_target=0.0,
            days_to_target=0,
            projected_completion_date=date.today().isoformat(),
        )

    months_float = round(remaining_minor / contrib_minor, 1)
    days = int(round(months_float * 30.4375))
    target_date = date.today() + timedelta(days=days)

    return EmergencyFundProjection(
        target_amount_minor=status.target_amount_minor,
        current_savings_minor=status.current_savings_minor,
        remaining_target_minor=remaining_minor,
        monthly_contribution_minor=contrib_minor,
        currency=currency_code,
        months_to_target=months_float,
        days_to_target=days,
        projected_completion_date=target_date.isoformat(),
    )
