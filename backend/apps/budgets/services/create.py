"""Budget creation service: validation, period boundaries, and initial generation."""

from __future__ import annotations

import calendar
import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.budgets.models import Budget, BudgetPeriod, BudgetPeriodType, FinancialPeriod
from apps.budgets.services.spending import calculate_budget_period_spending
from apps.categories.models import Category, CategoryKind
from apps.common.models import Currency
from apps.common.money import Money

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace


def compute_period_bounds(
    period_type: str,
    as_of: date,
    custom_period: FinancialPeriod | None = None,
) -> tuple[date, date]:
    """Compute period start and end dates based on period type and reference date."""
    if period_type == BudgetPeriodType.MONTHLY:
        start = date(as_of.year, as_of.month, 1)
        _, num_days = calendar.monthrange(as_of.year, as_of.month)
        end = date(as_of.year, as_of.month, num_days)
        return start, end

    if period_type == BudgetPeriodType.WEEKLY:
        # Start on Monday of the current week (ISO week)
        start = as_of - timedelta(days=as_of.weekday())
        end = start + timedelta(days=6)
        return start, end

    if period_type == BudgetPeriodType.CUSTOM:
        if not custom_period:
            raise ValueError("custom_period must be provided for CUSTOM period type.")
        return custom_period.start_date, custom_period.end_date

    raise ValueError(f"Unsupported period type: {period_type}")


def create_budget(
    *,
    workspace: Workspace,
    name: str,
    category_id: uuid.UUID,
    amount: str,
    currency: str,
    period_type: str = "monthly",
    rollover_enabled: bool = False,
    rollover_cap: str | None = None,
    is_flexible: bool = True,
    warn_at_percent: Decimal = Decimal("80.00"),
    alert_at_percent: Decimal = Decimal("100.00"),
    starts_on: date | None = None,
    ends_on: date | None = None,
    custom_period_id: uuid.UUID | None = None,
) -> Budget:
    """Create a new category budget and generate its initial budget period."""
    category = Category.objects.get(id=category_id, workspace=workspace)
    if category.kind != CategoryKind.EXPENSE:
        raise ValueError("Budgets can only be assigned to expense categories.")

    curr_obj = Currency.objects.get(code=currency)
    base_money = Money.parse(amount, curr_obj.code, curr_obj.minor_unit)
    if base_money.amount_minor <= 0:
        raise ValueError("Budget amount must be strictly positive.")

    cap_minor = None
    if rollover_cap is not None:
        cap_money = Money.parse(rollover_cap, curr_obj.code, curr_obj.minor_unit)
        cap_minor = cap_money.amount_minor

    ref_date = starts_on or timezone.now().date()
    custom_period = None
    if custom_period_id:
        custom_period = FinancialPeriod.objects.get(id=custom_period_id, workspace=workspace)

    with transaction.atomic():
        budget = Budget.objects.create(
            workspace=workspace,
            name=name.strip(),
            category=category,
            currency=curr_obj,
            period_type=period_type,
            custom_period=custom_period,
            base_amount_minor=base_money.amount_minor,
            rollover_enabled=rollover_enabled,
            rollover_cap_minor=cap_minor,
            is_flexible=is_flexible,
            warn_at_percent=warn_at_percent,
            alert_at_percent=alert_at_percent,
            starts_on=ref_date,
            ends_on=ends_on,
        )

        p_start, p_end = compute_period_bounds(period_type, ref_date, custom_period)
        period = BudgetPeriod.objects.create(
            workspace=workspace,
            budget=budget,
            period_start=p_start,
            period_end=p_end,
            base_amount_minor=base_money.amount_minor,
            rollover_in_minor=0,
            spent_minor=0,
        )
        period.spent_minor = calculate_budget_period_spending(period)
        period.save(update_fields=["spent_minor"])

        return budget
