"""Split-aware spending calculations for budgets and financial periods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Sum

from apps.categories.models import Category
from apps.transactions.models import (
    Transaction,
    TransactionSplit,
    TransactionStatus,
    TransactionType,
)

if TYPE_CHECKING:
    from apps.budgets.models import Budget, BudgetPeriod


def get_budget_category_ids(budget: Budget) -> set:
    """Retrieve category IDs covered by this budget, including any direct subcategories."""
    cat_ids = {budget.category_id}
    child_ids = Category.objects.filter(
        parent_id=budget.category_id,
        workspace_id=budget.workspace_id,
    ).values_list("id", flat=True)
    cat_ids.update(child_ids)
    return cat_ids


def calculate_budget_period_spending(period: BudgetPeriod) -> int:
    """Calculate exact total expense spent in minor units for a budget period.

    Aggregates both direct transactions and multi-category transaction splits
    matching the budget's category or its subcategories within the period boundary.
    """
    budget = period.budget
    target_category_ids = get_budget_category_ids(budget)

    # 1. Non-split completed expense transactions
    direct_spent = (
        Transaction.objects.filter(
            workspace_id=period.workspace_id,
            currency_id=budget.currency_id,
            status=TransactionStatus.COMPLETED,
            is_archived=False,
            transaction_type=TransactionType.EXPENSE,
            is_split=False,
            category_id__in=target_category_ids,
            occurred_on__gte=period.period_start,
            occurred_on__lte=period.period_end,
        ).aggregate(total=Sum("amount_minor"))["total"]
        or 0
    )

    # 2. Multi-category transaction splits on completed expense transactions
    split_spent = (
        TransactionSplit.objects.filter(
            transaction__workspace_id=period.workspace_id,
            transaction__currency_id=budget.currency_id,
            transaction__status=TransactionStatus.COMPLETED,
            transaction__is_archived=False,
            transaction__transaction_type=TransactionType.EXPENSE,
            transaction__occurred_on__gte=period.period_start,
            transaction__occurred_on__lte=period.period_end,
            category_id__in=target_category_ids,
        ).aggregate(total=Sum("amount_minor"))["total"]
        or 0
    )

    return direct_spent + split_spent
