"""Daily Spending Allowance selector and pacing calculator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.utils import timezone

from apps.budgets.models import Budget, BudgetPeriod
from apps.budgets.services.spending import calculate_budget_period_spending
from apps.common.models import Currency
from apps.common.money import Money
from apps.workspaces.models import Workspace


@dataclass
class DailyAllowanceResult:
    currency: str
    period: dict[str, str]
    remaining_days: int
    flexible_remaining: str
    allowance: str
    state: str  # "ok" | "over_budget" | "period_ended"
    explanation: str
    budgets: list[dict[str, Any]]
    excluded: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "period": self.period,
            "remaining_days": self.remaining_days,
            "flexible_remaining": self.flexible_remaining,
            "allowance": self.allowance,
            "state": self.state,
            "explanation": self.explanation,
            "budgets": self.budgets,
            "excluded": self.excluded,
        }


def calculate_daily_allowance(
    workspace: Workspace,
    period_kind: str = "calendar_month",
    currency_code: str | None = None,
    as_of: date | None = None,
) -> DailyAllowanceResult:
    """Calculate the remaining daily spending allowance across flexible budget categories."""
    today = as_of or timezone.localdate()
    target_currency = currency_code or str(workspace.reporting_currency_id)

    curr_obj = Currency.objects.get(code=target_currency)
    target_minor_unit = curr_obj.minor_unit

    # 1. Determine Period
    start_date = today.replace(day=1)
    next_m = today.replace(day=28) + timedelta(days=4)
    end_date = next_m - timedelta(days=next_m.day)

    period_dict = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "timezone": workspace.timezone or "UTC",
    }

    if today > end_date:
        return DailyAllowanceResult(
            currency=target_currency,
            period=period_dict,
            remaining_days=0,
            flexible_remaining="0.00",
            allowance="0.00",
            state="period_ended",
            explanation="The financial period has ended. Please roll over to the next period.",
            budgets=[],
            excluded=[],
        )

    remaining_days = (end_date - today).days + 1

    # 2. Query Budgets
    all_budgets = (
        Budget.objects.filter(
            workspace=workspace,
            is_archived=False,
        )
        .select_related("category", "currency")
        .prefetch_related("periods")
    )

    flexible_budgets: list[dict[str, Any]] = []
    excluded_budgets: list[dict[str, Any]] = []

    total_flexible_remaining_minor = 0
    over_budget_categories: list[str] = []

    for b in all_budgets:
        # Find overlapping period
        b_period = (
            BudgetPeriod.objects.filter(
                budget=b,
                period_start__lte=today,
                period_end__gte=today,
            )
            .order_by("-period_start")
            .first()
        )

        if b_period:
            spent_minor = calculate_budget_period_spending(b_period)
            avail_minor = b_period.base_amount_minor + b_period.rollover_in_minor
            rem_minor = avail_minor - spent_minor
        else:
            rem_minor = b.base_amount_minor

        b_curr = b.currency_id
        rem_str = Money(rem_minor, b_curr, b.currency.minor_unit).serialize()

        if b.is_flexible:
            flexible_budgets.append(
                {
                    "id": str(b.id),
                    "name": b.name,
                    "remaining": rem_str,
                    "flexible": True,
                }
            )
            if rem_minor < 0:
                over_budget_categories.append(b.name)
            else:
                total_flexible_remaining_minor += rem_minor
        else:
            excluded_budgets.append(
                {
                    "id": str(b.id),
                    "name": b.name,
                    "remaining": rem_str,
                    "reason": "not_flexible",
                }
            )

    flex_str = Money(
        max(0, total_flexible_remaining_minor),
        target_currency,
        target_minor_unit,
    ).serialize()

    # 3. State & Allowance Determination
    if over_budget_categories:
        state = "over_budget"
        allowance_str = "0.00"
        cats_str = ", ".join(over_budget_categories)
        explanation = f"Over budget on {cats_str}."
    elif total_flexible_remaining_minor == 0:
        state = "over_budget"
        allowance_str = "0.00"
        explanation = "Flexible budgets are fully spent for this period."
    else:
        allowance_minor = total_flexible_remaining_minor // remaining_days
        allowance_str = Money(allowance_minor, target_currency, target_minor_unit).serialize()
        state = "ok"
        explanation = (
            f"{flex_str} {target_currency} flexible budget remaining across {remaining_days} days."
        )

    return DailyAllowanceResult(
        currency=target_currency,
        period=period_dict,
        remaining_days=remaining_days,
        flexible_remaining=flex_str,
        allowance=allowance_str,
        state=state,
        explanation=explanation,
        budgets=flexible_budgets,
        excluded=excluded_budgets,
    )
