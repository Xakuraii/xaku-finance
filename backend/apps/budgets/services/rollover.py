"""Budget period rollover engine.

Strict Accounting Rule (ADR-0002 & ACCOUNTING_RULES.md):
Rollover is positive-only. Unused budget rolls forward. Overspending NEVER produces
negative rollover into the next period (overspending produces rollover_out = 0).
"""

from __future__ import annotations

import calendar
import uuid
from datetime import date, timedelta
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.budgets.models import (
    BudgetPeriod,
    BudgetPeriodStatus,
    BudgetPeriodType,
    BudgetRollover,
)
from apps.budgets.services.spending import calculate_budget_period_spending

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace


def get_next_period_bounds(period: BudgetPeriod) -> tuple[date, date] | None:
    """Calculate next period boundaries based on budget period type."""
    budget = period.budget
    if budget.period_type == BudgetPeriodType.MONTHLY:
        # Move to next calendar month
        cur_end = period.period_end
        if cur_end.month == 12:
            next_year = cur_end.year + 1
            next_month = 1
        else:
            next_year = cur_end.year
            next_month = cur_end.month + 1
        start = date(next_year, next_month, 1)
        _, num_days = calendar.monthrange(next_year, next_month)
        end = date(next_year, next_month, num_days)
        return start, end

    if budget.period_type == BudgetPeriodType.WEEKLY:
        start = period.period_end + timedelta(days=1)
        end = start + timedelta(days=6)
        return start, end

    # Custom periods do not automatically roll into an unbounded next period
    return None


def close_budget_period(
    *,
    workspace: Workspace,
    period_id: uuid.UUID,
) -> tuple[BudgetPeriod, BudgetPeriod | None]:
    """Close a budget period, compute final spending and positive rollover, and advance."""
    with transaction.atomic():
        period = (
            BudgetPeriod.objects.select_for_update()
            .select_related("budget")
            .get(id=period_id, workspace=workspace)
        )

        if period.status == BudgetPeriodStatus.CLOSED:
            # Idempotent: already closed
            return period, None

        budget = period.budget

        # Recompute final spending within the period boundaries
        spent = calculate_budget_period_spending(period)
        period.spent_minor = spent

        total_available = period.base_amount_minor + period.rollover_in_minor

        # STRICT: Positive-only rollover.
        # If actual spending exceeds total available, rollover_out is strictly 0.
        if spent >= total_available or not budget.rollover_enabled:
            rollover_out = 0
        else:
            unspent = total_available - spent
            if budget.rollover_cap_minor is not None:
                rollover_out = min(unspent, budget.rollover_cap_minor)
            else:
                rollover_out = unspent

        period.rollover_out_minor = rollover_out
        period.status = BudgetPeriodStatus.CLOSED
        period.computed_at = timezone.now()
        period.save(
            update_fields=[
                "spent_minor",
                "rollover_out_minor",
                "status",
                "computed_at",
                "updated_at",
            ]
        )

        # Advance to next period if applicable
        next_bounds = get_next_period_bounds(period)
        next_period = None
        if next_bounds:
            next_start, next_end = next_bounds
            if not budget.ends_on or next_start <= budget.ends_on:
                next_period, created = BudgetPeriod.objects.get_or_create(
                    budget=budget,
                    period_start=next_start,
                    defaults={
                        "workspace": workspace,
                        "period_end": next_end,
                        "base_amount_minor": budget.base_amount_minor,
                        "rollover_in_minor": rollover_out,
                        "spent_minor": 0,
                    },
                )
                if not created:
                    next_period.rollover_in_minor = rollover_out
                    next_period.save(update_fields=["rollover_in_minor", "updated_at"])

                # Record immutable audit trail of the rollover
                BudgetRollover.objects.get_or_create(
                    budget_period=next_period,
                    source_period=period,
                    defaults={
                        "workspace": workspace,
                        "amount_minor": rollover_out,
                    },
                )

                # Compute any existing transactions that fall into the new period
                next_period.spent_minor = calculate_budget_period_spending(next_period)
                next_period.save(update_fields=["spent_minor"])

        return period, next_period


def refresh_budget_period_spending(*, workspace: Workspace, period_id: uuid.UUID) -> BudgetPeriod:
    """Refresh the cached spent_minor for an active budget period."""
    with transaction.atomic():
        period = BudgetPeriod.objects.select_for_update().get(
            id=period_id,
            workspace=workspace,
        )
        if period.status != BudgetPeriodStatus.CLOSED:
            period.spent_minor = calculate_budget_period_spending(period)
            period.save(update_fields=["spent_minor", "updated_at"])
        return period
