"""Financial Reports & Analytics engine with double-entry ledger reconciliation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Account
from apps.analytics.net_worth import get_exchange_rate
from apps.categories.models import Category
from apps.common.models import Currency
from apps.common.money import Money, convert
from apps.ledger.models import (
    JournalEntryStatus,
    LedgerAccount,
    LedgerAccountKind,
    Posting,
)
from apps.transactions.models import (
    Transaction,
    TransactionSplit,
    TransactionStatus,
    TransactionType,
)
from apps.workspaces.models import Workspace


@dataclass
class ReportReconciliation:
    ledger_income: str
    reported_income: str
    income_difference: str
    ledger_expense: str
    reported_expense: str
    expense_difference: str
    checked_at: str

    def to_dict(self) -> dict[str, str]:
        return {
            "ledger_income": self.ledger_income,
            "reported_income": self.reported_income,
            "difference": self.income_difference if self.income_difference != "0.00" else self.expense_difference,
            "ledger_expense": self.ledger_expense,
            "reported_expense": self.reported_expense,
            "checked_at": self.checked_at,
        }


def compute_ledger_reconciliation(
    workspace: Workspace,
    start_date: date,
    end_date: date,
    target_currency: str,
) -> ReportReconciliation:
    """Compute exact posting sums for income and expense ledger accounts and compare to transaction figures."""
    curr_obj = Currency.objects.get(code=target_currency)
    m_unit = curr_obj.minor_unit

    # 1. Income postings sum: Income normal balance is credit (-), so income = -sum(postings)
    income_postings_minor = (
        Posting.objects.filter(
            workspace_id=workspace.id,
            ledger_account__kind=LedgerAccountKind.INCOME,
            journal_entry__status__in=[JournalEntryStatus.POSTED, JournalEntryStatus.REVERSED],
            journal_entry__effective_date__gte=start_date,
            journal_entry__effective_date__lte=end_date,
        ).aggregate(s=Sum("amount_minor"))["s"]
        or 0
    )
    ledger_income_minor = max(0, -income_postings_minor)

    # 2. Expense postings sum: Expense normal balance is debit (+), so expense = +sum(postings)
    # Exclude system FX gain/loss if any, or include all operational expenses
    expense_postings_minor = (
        Posting.objects.filter(
            workspace_id=workspace.id,
            ledger_account__kind=LedgerAccountKind.EXPENSE,
            journal_entry__status__in=[JournalEntryStatus.POSTED, JournalEntryStatus.REVERSED],
            journal_entry__effective_date__gte=start_date,
            journal_entry__effective_date__lte=end_date,
        ).aggregate(s=Sum("amount_minor"))["s"]
        or 0
    )
    ledger_expense_minor = max(0, expense_postings_minor)

    # 3. Transaction-level reported sums
    reported_income_minor = (
        Transaction.objects.filter(
            workspace_id=workspace.id,
            transaction_type=TransactionType.INCOME,
            status=TransactionStatus.COMPLETED,
            is_archived=False,
            occurred_on__gte=start_date,
            occurred_on__lte=end_date,
        ).aggregate(s=Sum("amount_minor"))["s"]
        or 0
    )

    reported_expense_minor = (
        Transaction.objects.filter(
            workspace_id=workspace.id,
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.COMPLETED,
            is_archived=False,
            occurred_on__gte=start_date,
            occurred_on__lte=end_date,
        ).aggregate(s=Sum("amount_minor"))["s"]
        or 0
    )

    diff_inc_minor = ledger_income_minor - reported_income_minor
    diff_exp_minor = ledger_expense_minor - reported_expense_minor

    return ReportReconciliation(
        ledger_income=Money(ledger_income_minor, target_currency, m_unit).serialize(),
        reported_income=Money(reported_income_minor, target_currency, m_unit).serialize(),
        income_difference=Money(diff_inc_minor, target_currency, m_unit).serialize(),
        ledger_expense=Money(ledger_expense_minor, target_currency, m_unit).serialize(),
        reported_expense=Money(reported_expense_minor, target_currency, m_unit).serialize(),
        expense_difference=Money(diff_exp_minor, target_currency, m_unit).serialize(),
        checked_at=timezone.now().isoformat(),
    )


def get_income_expense_report(
    workspace: Workspace,
    start_date: date,
    end_date: date,
    currency_code: str | None = None,
) -> dict[str, Any]:
    """Generate the Income vs Expense statement with monthly series and ledger reconciliation."""
    target_currency = currency_code or str(workspace.reporting_currency_id)
    curr_obj = Currency.objects.get(code=target_currency)
    m_unit = curr_obj.minor_unit

    recon = compute_ledger_reconciliation(workspace, start_date, end_date, target_currency)

    # Series by month
    monthly_data: dict[str, dict[str, int]] = {}
    curr = start_date.replace(day=1)
    while curr <= end_date:
        key = curr.strftime("%Y-%m")
        monthly_data[key] = {"income": 0, "expense": 0}
        next_m = curr.replace(day=28) + timedelta(days=4)
        curr = next_m.replace(day=1)

    income_txs = Transaction.objects.filter(
        workspace_id=workspace.id,
        transaction_type=TransactionType.INCOME,
        status=TransactionStatus.COMPLETED,
        is_archived=False,
        occurred_on__gte=start_date,
        occurred_on__lte=end_date,
    )
    for tx in income_txs:
        k = tx.occurred_on.strftime("%Y-%m")
        if k in monthly_data:
            monthly_data[k]["income"] += tx.amount_minor

    expense_txs = Transaction.objects.filter(
        workspace_id=workspace.id,
        transaction_type=TransactionType.EXPENSE,
        status=TransactionStatus.COMPLETED,
        is_archived=False,
        occurred_on__gte=start_date,
        occurred_on__lte=end_date,
    )
    for tx in expense_txs:
        k = tx.occurred_on.strftime("%Y-%m")
        if k in monthly_data:
            monthly_data[k]["expense"] += tx.amount_minor

    series = []
    table = []
    total_inc = 0
    total_exp = 0

    for m_key in sorted(monthly_data.keys()):
        inc_m = monthly_data[m_key]["income"]
        exp_m = monthly_data[m_key]["expense"]
        net_m = inc_m - exp_m
        total_inc += inc_m
        total_exp += exp_m

        pt = {
            "period": m_key,
            "income": Money(inc_m, target_currency, m_unit).serialize(),
            "expense": Money(exp_m, target_currency, m_unit).serialize(),
            "net": Money(net_m, target_currency, m_unit).serialize(),
        }
        series.append(pt)
        table.append(pt)

    total_net = total_inc - total_exp

    return {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "currency": target_currency,
        "totals": {
            "income": Money(total_inc, target_currency, m_unit).serialize(),
            "expense": Money(total_exp, target_currency, m_unit).serialize(),
            "net": Money(total_net, target_currency, m_unit).serialize(),
        },
        "series": series,
        "table": table,
        "rate_policy": "transaction_date",
        "rates_used": [],
        "generated_from": "ledger",
        "reconciliation": recon.to_dict(),
    }


def get_category_report(
    workspace: Workspace,
    start_date: date,
    end_date: date,
    currency_code: str | None = None,
) -> dict[str, Any]:
    """Generate category breakdown with amounts and percentage shares."""
    target_currency = currency_code or str(workspace.reporting_currency_id)
    curr_obj = Currency.objects.get(code=target_currency)
    m_unit = curr_obj.minor_unit

    recon = compute_ledger_reconciliation(workspace, start_date, end_date, target_currency)

    # 1. Non-split completed expense transactions
    direct_spending = (
        Transaction.objects.filter(
            workspace_id=workspace.id,
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.COMPLETED,
            is_archived=False,
            is_split=False,
            category__isnull=False,
            occurred_on__gte=start_date,
            occurred_on__lte=end_date,
        )
        .values("category_id", "category__name")
        .annotate(total_minor=Sum("amount_minor"))
    )

    cat_map: dict[str, dict[str, Any]] = {}
    total_spending_minor = 0

    for row in direct_spending:
        cid = str(row["category_id"])
        cname = row["category__name"]
        amt = row["total_minor"] or 0
        cat_map[cid] = {"id": cid, "name": cname, "amount_minor": amt, "count": 1}
        total_spending_minor += amt

    # 2. Transaction splits
    splits = (
        TransactionSplit.objects.filter(
            transaction__workspace_id=workspace.id,
            transaction__transaction_type=TransactionType.EXPENSE,
            transaction__status=TransactionStatus.COMPLETED,
            transaction__is_archived=False,
            transaction__occurred_on__gte=start_date,
            transaction__occurred_on__lte=end_date,
        )
        .values("category_id", "category__name")
        .annotate(total_minor=Sum("amount_minor"))
    )

    for row in splits:
        cid = str(row["category_id"])
        cname = row["category__name"]
        amt = row["total_minor"] or 0
        if cid in cat_map:
            cat_map[cid]["amount_minor"] += amt
        else:
            cat_map[cid] = {"id": cid, "name": cname, "amount_minor": amt, "count": 1}
        total_spending_minor += amt

    table = []
    for cid, val in cat_map.items():
        amt_minor = val["amount_minor"]
        pct = (amt_minor / total_spending_minor * 100.0) if total_spending_minor > 0 else 0.0
        table.append({
            "category_id": cid,
            "category_name": val["name"],
            "amount": Money(amt_minor, target_currency, m_unit).serialize(),
            "amount_minor": amt_minor,
            "percentage": round(pct, 2),
        })

    # Sort descending by amount
    table.sort(key=lambda x: x["amount_minor"], reverse=True)

    return {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "currency": target_currency,
        "totals": {
            "total_spending": Money(total_spending_minor, target_currency, m_unit).serialize(),
        },
        "series": [],
        "table": table,
        "rate_policy": "transaction_date",
        "rates_used": [],
        "generated_from": "ledger",
        "reconciliation": recon.to_dict(),
    }


def get_cash_flow_statement(
    workspace: Workspace,
    start_date: date,
    end_date: date,
    currency_code: str | None = None,
) -> dict[str, Any]:
    """Generate the Cash Flow Statement: inflows and outflows excluding internal transfers."""
    target_currency = currency_code or str(workspace.reporting_currency_id)
    curr_obj = Currency.objects.get(code=target_currency)
    m_unit = curr_obj.minor_unit

    recon = compute_ledger_reconciliation(workspace, start_date, end_date, target_currency)

    # Inflows: completed income transactions
    inflows_minor = (
        Transaction.objects.filter(
            workspace_id=workspace.id,
            transaction_type=TransactionType.INCOME,
            status=TransactionStatus.COMPLETED,
            is_archived=False,
            occurred_on__gte=start_date,
            occurred_on__lte=end_date,
        ).aggregate(s=Sum("amount_minor"))["s"]
        or 0
    )

    # Outflows: completed expense transactions
    outflows_minor = (
        Transaction.objects.filter(
            workspace_id=workspace.id,
            transaction_type=TransactionType.EXPENSE,
            status=TransactionStatus.COMPLETED,
            is_archived=False,
            occurred_on__gte=start_date,
            occurred_on__lte=end_date,
        ).aggregate(s=Sum("amount_minor"))["s"]
        or 0
    )

    net_cash_flow_minor = inflows_minor - outflows_minor

    table = [
        {"item": "Operating Inflows", "amount": Money(inflows_minor, target_currency, m_unit).serialize()},
        {"item": "Operating Outflows", "amount": f"-{Money(outflows_minor, target_currency, m_unit).serialize()}"},
        {"item": "Net Cash Flow", "amount": Money(net_cash_flow_minor, target_currency, m_unit).serialize()},
    ]

    return {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "currency": target_currency,
        "totals": {
            "inflows": Money(inflows_minor, target_currency, m_unit).serialize(),
            "outflows": Money(outflows_minor, target_currency, m_unit).serialize(),
            "net_cash_flow": Money(net_cash_flow_minor, target_currency, m_unit).serialize(),
        },
        "series": [],
        "table": table,
        "rate_policy": "transaction_date",
        "rates_used": [],
        "generated_from": "ledger",
        "reconciliation": recon.to_dict(),
    }
