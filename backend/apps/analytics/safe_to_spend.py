"""Safe-to-Spend selector and domain calculator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Account
from apps.accounts.selectors import account_balance
from apps.analytics.models import ObligationKind, RecurringObligation
from apps.analytics.net_worth import get_exchange_rate
from apps.budgets.models import FinancialPeriod
from apps.common.models import Currency
from apps.common.money import Money, convert
from apps.savings.models import SavingsAllocation
from apps.transactions.models import Transaction, TransactionStatus, TransactionType
from apps.workspaces.models import Workspace


@dataclass
class SafeToSpendResult:
    currency: str
    display: str
    raw: str
    is_negative: bool
    horizon: dict[str, str]
    components: dict[str, str]
    accounts: list[dict[str, Any]]
    excluded_accounts: list[dict[str, Any]]
    notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "currency": self.currency,
            "display": self.display,
            "raw": self.raw,
            "is_negative": self.is_negative,
            "horizon": self.horizon,
            "components": self.components,
            "accounts": self.accounts,
            "excluded_accounts": self.excluded_accounts,
            "notes": self.notes,
        }


def calculate_safe_to_spend(
    workspace: Workspace,
    horizon_type: str = "period_end",
    horizon_days: int | None = None,
    currency_code: str | None = None,
    as_of: date | None = None,
) -> SafeToSpendResult:
    """
    Calculate the spendable liquid allowance available after reserved obligations
    and pending outflows.
    """
    today = as_of or timezone.localdate()
    target_currency = currency_code or str(workspace.reporting_currency_id)

    curr_obj = Currency.objects.get(code=target_currency)
    target_minor_unit = curr_obj.minor_unit

    # 1. Determine Horizon
    if horizon_days is not None and horizon_days > 0:
        start_date = today
        end_date = today + timedelta(days=horizon_days)
        horizon_label = f"next {horizon_days} days"
    else:
        # Check for active FinancialPeriod
        active_period = (
            FinancialPeriod.objects.filter(
                workspace=workspace,
                is_active=True,
                start_date__lte=today,
                end_date__gte=today,
            )
            .order_by("start_date")
            .first()
        )
        if active_period:
            start_date = today
            end_date = active_period.end_date
            horizon_label = f"to end of {active_period.name}"
        else:
            # End of calendar month
            next_m = today.replace(day=28) + timedelta(days=4)
            end_date = next_m - timedelta(days=next_m.day)
            start_date = today
            horizon_label = "to end of month"

    horizon = {
        "start": start_date.isoformat(),
        "end": end_date.isoformat(),
        "label": horizon_label,
    }

    # 2. Spendable Accounts
    all_accounts = Account.objects.filter(
        workspace=workspace,
        is_archived=False,
    ).select_related("currency")

    included_accounts: list[dict[str, Any]] = []
    excluded_accounts: list[dict[str, Any]] = []
    spendable_balance_minor = 0

    for acc in all_accounts:
        if acc.is_spendable:
            bal = account_balance(account=acc)
            rate_info = get_exchange_rate(workspace, acc.currency_id, target_currency, today)
            rate_val = rate_info[0] if rate_info else None
            converted = (
                convert(bal, rate_val, target_currency, target_minor_unit)
                if rate_val
                else Money(bal.amount_minor, target_currency, target_minor_unit)
            )

            spendable_balance_minor += converted.amount_minor
            included_accounts.append(
                {
                    "id": str(acc.id),
                    "name": acc.name,
                    "included": True,
                    "balance": converted.serialize(),
                    "reason": "spendable",
                }
            )
        else:
            excluded_accounts.append(
                {
                    "id": str(acc.id),
                    "name": acc.name,
                    "reason": "not_spendable",
                }
            )

    # 3. Pending Outflows
    pending_txs = Transaction.objects.filter(
        workspace=workspace,
        account__is_spendable=True,
        status=TransactionStatus.PENDING,
        transaction_type__in=[TransactionType.EXPENSE, TransactionType.TRANSFER],
    ).select_related("currency")

    pending_outflows_minor = 0
    for tx in pending_txs:
        tx_money = Money(tx.amount_minor, tx.currency_id, tx.currency.minor_unit)
        rate_info = get_exchange_rate(workspace, tx.currency_id, target_currency, today)
        rate_val = rate_info[0] if rate_info else None
        converted = (
            convert(tx_money, rate_val, target_currency, target_minor_unit)
            if rate_val
            else Money(tx.amount_minor, target_currency, target_minor_unit)
        )
        pending_outflows_minor += converted.amount_minor

    # 4. Reserved Obligations within horizon
    reserved_obligations = RecurringObligation.objects.filter(
        workspace=workspace,
        is_active=True,
        is_reserved=True,
        next_due_date__gte=today,
        next_due_date__lte=end_date,
    )

    reserved_bills_minor = 0
    for ro in reserved_obligations:
        ro_money = Money(ro.amount_minor, ro.currency_code, 2)
        rate_info = get_exchange_rate(workspace, ro.currency_code, target_currency, today)
        rate_val = rate_info[0] if rate_info else None
        converted = (
            convert(ro_money, rate_val, target_currency, target_minor_unit)
            if rate_val
            else Money(ro.amount_minor, target_currency, target_minor_unit)
        )
        reserved_bills_minor += converted.amount_minor

    # 5. Planned Savings / Earmarks on Spendable Accounts
    earmarks_qs = (
        SavingsAllocation.objects.filter(
            account__workspace=workspace,
            account__is_spendable=True,
            goal__is_archived=False,
        )
        .select_related("account__currency")
        .values("account__currency_id")
        .annotate(total=Sum("allocated_minor"))
    )

    planned_savings_minor = 0
    for row in earmarks_qs:
        acc_curr = row["account__currency_id"]
        alloc_minor = row["total"] or 0
        acc_money = Money(alloc_minor, acc_curr, 2)
        rate_info = get_exchange_rate(workspace, acc_curr, target_currency, today)
        rate_val = rate_info[0] if rate_info else None
        converted = (
            convert(acc_money, rate_val, target_currency, target_minor_unit)
            if rate_val
            else Money(alloc_minor, target_currency, target_minor_unit)
        )
        planned_savings_minor += converted.amount_minor

    # Also include savings plan obligations
    savings_plans = RecurringObligation.objects.filter(
        workspace=workspace,
        is_active=True,
        kind=ObligationKind.SAVINGS_PLAN,
        next_due_date__gte=today,
        next_due_date__lte=end_date,
    )
    for sp in savings_plans:
        sp_money = Money(sp.amount_minor, sp.currency_code, 2)
        rate_info = get_exchange_rate(workspace, sp.currency_code, target_currency, today)
        rate_val = rate_info[0] if rate_info else None
        converted = (
            convert(sp_money, rate_val, target_currency, target_minor_unit)
            if rate_val
            else Money(sp.amount_minor, target_currency, target_minor_unit)
        )
        planned_savings_minor += converted.amount_minor

    # 6. Raw & Display Arithmetic
    raw_minor = (
        spendable_balance_minor
        - pending_outflows_minor
        - reserved_bills_minor
        - planned_savings_minor
    )
    display_minor = max(0, raw_minor)
    is_negative = raw_minor < 0

    spendable_str = Money(spendable_balance_minor, target_currency, target_minor_unit).serialize()
    pending_str = (
        f"-{Money(pending_outflows_minor, target_currency, target_minor_unit).serialize()}"
        if pending_outflows_minor > 0
        else "0.00"
    )
    bills_str = (
        f"-{Money(reserved_bills_minor, target_currency, target_minor_unit).serialize()}"
        if reserved_bills_minor > 0
        else "0.00"
    )
    savings_str = (
        f"-{Money(planned_savings_minor, target_currency, target_minor_unit).serialize()}"
        if planned_savings_minor > 0
        else "0.00"
    )

    display_str = Money(display_minor, target_currency, target_minor_unit).serialize()
    raw_str = Money(raw_minor, target_currency, target_minor_unit).serialize()

    return SafeToSpendResult(
        currency=target_currency,
        display=display_str,
        raw=raw_str,
        is_negative=is_negative,
        horizon=horizon,
        components={
            "spendable_balance": spendable_str,
            "pending_outflows": pending_str,
            "reserved_bills": bills_str,
            "planned_savings": savings_str,
        },
        accounts=included_accounts,
        excluded_accounts=excluded_accounts,
        notes=["Pending transactions are not yet deducted from balances."],
    )
