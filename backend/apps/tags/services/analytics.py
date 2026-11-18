"""Analytics services for Tags and Spending Necessity breakdowns."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from django.db.models import Count, Sum

from apps.common.models import Currency
from apps.common.money import Money
from apps.transactions.models import (
    Transaction,
    TransactionStatus,
    TransactionTag,
    TransactionType,
)

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace


def get_spending_analytics(
    *,
    workspace: Workspace,
    start_date: date | None = None,
    end_date: date | None = None,
    currency_code: str | None = None,
) -> dict[str, Any]:
    """Calculate aggregate spending broken down by Tag and by Necessity classification.

    Follows immutable minor unit arithmetic with exact decimal serialization.
    """
    default_curr = getattr(workspace, "default_currency_code", "USD") or "USD"
    currency: str = str(currency_code or default_curr)
    curr_obj = Currency.objects.filter(code=currency).first()
    minor_unit = curr_obj.minor_unit if curr_obj else 2

    # Query expense transactions
    tx_qs = Transaction.objects.filter(
        workspace=workspace,
        is_archived=False,
        status=TransactionStatus.COMPLETED,
        transaction_type=TransactionType.EXPENSE,
    )

    if currency_code:
        tx_qs = tx_qs.filter(currency_id=currency)
    if start_date:
        tx_qs = tx_qs.filter(occurred_on__gte=start_date)
    if end_date:
        tx_qs = tx_qs.filter(occurred_on__lte=end_date)

    total_expense_minor = tx_qs.aggregate(total=Sum("amount_minor"))["total"] or 0
    total_expense_money = Money(total_expense_minor, currency, minor_unit)

    # 1. By Tag breakdown
    tag_aggregates = (
        TransactionTag.objects.filter(
            transaction__in=tx_qs,
        )
        .values("tag__name")
        .annotate(
            amount_minor=Sum("transaction__amount_minor"),
            count=Count("transaction_id", distinct=True),
        )
        .order_by("-amount_minor")
    )

    by_tag = []
    for item in tag_aggregates:
        t_minor = item["amount_minor"] or 0
        t_pct = round((t_minor / total_expense_minor * 100), 1) if total_expense_minor > 0 else 0.0
        by_tag.append(
            {
                "tag": item["tag__name"],
                "amount_minor": t_minor,
                "amount": Money(t_minor, currency, minor_unit).serialize(),
                "count": item["count"],
                "percentage": t_pct,
            }
        )

    # 2. By Necessity breakdown
    necessity_aggregates = (
        tx_qs.exclude(necessity__isnull=True)
        .values("necessity")
        .annotate(
            amount_minor=Sum("amount_minor"),
            count=Count("id"),
        )
        .order_by("-amount_minor")
    )

    by_necessity = []
    for item in necessity_aggregates:
        n_minor = item["amount_minor"] or 0
        n_pct = round((n_minor / total_expense_minor * 100), 1) if total_expense_minor > 0 else 0.0
        by_necessity.append(
            {
                "necessity": item["necessity"],
                "amount_minor": n_minor,
                "amount": Money(n_minor, currency, minor_unit).serialize(),
                "count": item["count"],
                "percentage": n_pct,
            }
        )

    return {
        "currency": currency,
        "total_expense_minor": total_expense_minor,
        "total_expense": total_expense_money.serialize(),
        "by_tag": by_tag,
        "by_necessity": by_necessity,
    }
