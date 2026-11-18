"""Net Worth analytics engine: ledger-backed as-of balances and snapshot caching."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Account
from apps.analytics.models import NetWorthSnapshot
from apps.common.models import Currency
from apps.common.money import Money, convert
from apps.debts.models import Liability
from apps.ledger.models import (
    ExchangeRate,
    JournalEntryStatus,
    LedgerAccount,
    LedgerAccountKind,
    Posting,
)
from apps.workspaces.models import Workspace


@dataclass
class RateUsed:
    pair: str
    rate: str
    date: str


@dataclass
class NetWorthChange:
    amount: str
    since: str
    direction: str


@dataclass
class NetWorthBreakdownItem:
    account_id: str | None
    liability_id: str | None
    name: str
    kind: str
    currency: str
    native_amount: str
    amount: str  # Converted to reporting currency


@dataclass
class NetWorthCalculation:
    as_of: str
    currency: str
    assets: str
    liabilities: str
    net_worth: str
    assets_minor: int
    liabilities_minor: int
    net_worth_minor: int
    change: dict[str, Any] | None
    breakdown: dict[str, list[dict[str, Any]]]
    fx_effect: str
    rate_policy: str
    rates_used: list[dict[str, Any]]
    ledger_seq: int
    computed_from: str
    conversion_unavailable: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": self.as_of,
            "currency": self.currency,
            "assets": self.assets,
            "liabilities": self.liabilities,
            "net_worth": self.net_worth,
            "change": self.change,
            "breakdown": self.breakdown,
            "fx_effect": self.fx_effect,
            "rate_policy": self.rate_policy,
            "rates_used": self.rates_used,
            "ledger_seq": self.ledger_seq,
            "computed_from": self.computed_from,
            "conversion_unavailable": self.conversion_unavailable,
        }


def get_exchange_rate(
    workspace: Workspace,
    from_currency: str,
    to_currency: str,
    as_of: date,
) -> tuple[Decimal, date] | None:
    """Resolve the applicable exchange rate on or before as_of date.

    Priority: workspace rate -> global rate.
    Handles inverted rate if direct rate is missing.
    Returns (rate, effective_date) where rate converts 1 from_curr to to_curr.
    """
    if from_currency == to_currency:
        return Decimal("1.0"), as_of

    # 1. Direct rate: base=from, quote=to
    direct_rate = (
        ExchangeRate.objects.filter(
            workspace=workspace,
            base_currency_id=from_currency,
            quote_currency_id=to_currency,
            effective_date__lte=as_of,
        )
        .order_by("-effective_date")
        .first()
    )
    if not direct_rate:
        direct_rate = (
            ExchangeRate.objects.filter(
                workspace__isnull=True,
                base_currency_id=from_currency,
                quote_currency_id=to_currency,
                effective_date__lte=as_of,
            )
            .order_by("-effective_date")
            .first()
        )

    if direct_rate:
        return direct_rate.rate, direct_rate.effective_date

    # 2. Inverted rate: base=to, quote=from
    inverted_rate = (
        ExchangeRate.objects.filter(
            workspace=workspace,
            base_currency_id=to_currency,
            quote_currency_id=from_currency,
            effective_date__lte=as_of,
        )
        .order_by("-effective_date")
        .first()
    )
    if not inverted_rate:
        inverted_rate = (
            ExchangeRate.objects.filter(
                workspace__isnull=True,
                base_currency_id=to_currency,
                quote_currency_id=from_currency,
                effective_date__lte=as_of,
            )
            .order_by("-effective_date")
            .first()
        )

    if inverted_rate and inverted_rate.rate > 0:
        inv = Decimal("1.0") / inverted_rate.rate
        return inv, inverted_rate.effective_date

    return None


def calculate_net_worth(
    workspace: Workspace,
    as_of: date | None = None,
    currency_code: str | None = None,
) -> NetWorthCalculation:
    """Calculate Net Worth as of a given date from double-entry ledger postings."""
    target_date = as_of or timezone.localdate()
    target_currency = currency_code or str(workspace.reporting_currency_id)

    curr_obj = Currency.objects.get(code=target_currency)
    target_minor_unit = curr_obj.minor_unit

    rates_used: list[dict[str, Any]] = []
    conversion_unavailable = False

    # 1. Query postings sum per ledger account as of target_date
    postings_qs = (
        Posting.objects.filter(
            workspace_id=workspace.id,
            journal_entry__status__in=[JournalEntryStatus.POSTED, JournalEntryStatus.REVERSED],
            journal_entry__effective_date__lte=target_date,
        )
        .values("ledger_account_id")
        .annotate(total_minor=Sum("amount_minor"))
    )
    postings_by_account = {row["ledger_account_id"]: row["total_minor"] for row in postings_qs}

    # 2. Fetch all ledger accounts for the workspace
    ledger_accounts = LedgerAccount.objects.filter(
        workspace_id=workspace.id,
        is_active=True,
    ).select_related("currency")

    # Map accounts and liabilities for display names and IDs
    user_accounts = {
        acc.id: acc
        for acc in Account.objects.filter(workspace_id=workspace.id).select_related("currency")
    }
    user_liabilities = {
        liab.id: liab for liab in Liability.objects.filter(workspace_id=workspace.id)
    }

    asset_items: list[dict[str, Any]] = []
    liability_items: list[dict[str, Any]] = []

    sum_assets_minor = 0
    sum_liabilities_minor = 0
    fx_effect_minor = 0

    for la in ledger_accounts:
        balance_minor = postings_by_account.get(la.id, 0)
        if balance_minor == 0:
            continue

        acc_curr = la.currency_id
        acc_minor_unit = la.currency.minor_unit

        rate_info = get_exchange_rate(workspace, acc_curr, target_currency, target_date)
        if not rate_info:
            conversion_unavailable = True
            rate_val = Decimal("1.0")
        else:
            rate_val, rate_date = rate_info
            if acc_curr != target_currency:
                rates_used.append(
                    {
                        "pair": f"{acc_curr}/{target_currency}",
                        "rate": str(rate_val),
                        "date": rate_date.isoformat(),
                    }
                )

        native_money = Money(abs(balance_minor), acc_curr, acc_minor_unit)
        converted_money = convert(native_money, rate_val, target_currency, target_minor_unit)

        # Asset accounts (Debit normal: positive balance is asset)
        if la.kind == LedgerAccountKind.ASSET:
            account_id = str(la.owner_id) if la.owner_type == "account" and la.owner_id else None
            account_name = (
                user_accounts[la.owner_id].name if la.owner_id in user_accounts else la.name
            )

            item = {
                "account_id": account_id,
                "name": account_name,
                "kind": "asset",
                "currency": acc_curr,
                "native_amount": Money(balance_minor, acc_curr, acc_minor_unit).serialize(),
                "amount": converted_money.serialize()
                if balance_minor > 0
                else f"-{converted_money.serialize()}",
            }
            asset_items.append(item)
            if balance_minor > 0:
                sum_assets_minor += converted_money.amount_minor
            else:
                sum_assets_minor -= converted_money.amount_minor

        # Liability accounts (Credit normal: negative balance is outstanding debt)
        elif la.kind == LedgerAccountKind.LIABILITY:
            liability_id = (
                str(la.owner_id) if la.owner_type == "liability" and la.owner_id else None
            )
            account_id = str(la.owner_id) if la.owner_type == "account" and la.owner_id else None

            if la.owner_type == "liability" and la.owner_id in user_liabilities:
                disp_name = user_liabilities[la.owner_id].name
            elif la.owner_type == "account" and la.owner_id in user_accounts:
                disp_name = user_accounts[la.owner_id].name
            else:
                disp_name = la.name

            outstanding_minor = max(0, -balance_minor)
            converted_out = convert(
                Money(outstanding_minor, acc_curr, acc_minor_unit),
                rate_val,
                target_currency,
                target_minor_unit,
            )

            item = {
                "liability_id": liability_id,
                "account_id": account_id,
                "name": disp_name,
                "kind": "liability",
                "currency": acc_curr,
                "native_amount": Money(outstanding_minor, acc_curr, acc_minor_unit).serialize(),
                "outstanding": converted_out.serialize(),
                "amount": converted_out.serialize(),
            }
            liability_items.append(item)
            sum_liabilities_minor += converted_out.amount_minor

    # Guarantee non-negative assets and liabilities for database integrity
    final_assets_minor = max(0, sum_assets_minor)
    final_liabilities_minor = sum_liabilities_minor + (
        abs(sum_assets_minor) if sum_assets_minor < 0 else 0
    )
    final_net_worth_minor = final_assets_minor - final_liabilities_minor

    assets_str = Money(final_assets_minor, target_currency, target_minor_unit).serialize()
    liabilities_str = Money(final_liabilities_minor, target_currency, target_minor_unit).serialize()
    net_worth_str = Money(final_net_worth_minor, target_currency, target_minor_unit).serialize()
    fx_effect_str = Money(fx_effect_minor, target_currency, target_minor_unit).serialize()

    # Calculate change since prior month or prior snapshot
    prior_snapshot = (
        NetWorthSnapshot.objects.filter(
            workspace=workspace,
            reporting_currency_code=target_currency,
            as_of_date__lt=target_date,
        )
        .order_by("-as_of_date")
        .first()
    )

    change: dict[str, Any] | None = None
    if prior_snapshot:
        diff_minor = final_net_worth_minor - prior_snapshot.net_worth_minor
        direction = "up" if diff_minor > 0 else ("down" if diff_minor < 0 else "flat")
        change = {
            "amount": Money(diff_minor, target_currency, target_minor_unit).serialize(),
            "since": prior_snapshot.as_of_date.isoformat(),
            "direction": direction,
        }

    return NetWorthCalculation(
        as_of=target_date.isoformat(),
        currency=target_currency,
        assets=assets_str,
        liabilities=liabilities_str,
        net_worth=net_worth_str,
        assets_minor=final_assets_minor,
        liabilities_minor=final_liabilities_minor,
        net_worth_minor=final_net_worth_minor,
        change=change,
        breakdown={"assets": asset_items, "liabilities": liability_items},
        fx_effect=fx_effect_str,
        rate_policy="period_end",
        rates_used=rates_used,
        ledger_seq=workspace.ledger_seq,
        computed_from="ledger",
        conversion_unavailable=conversion_unavailable,
    )


def compute_rate_set_hash(rates_used: list[dict[str, Any]]) -> str:
    """Compute a deterministic hash for the rates used in a snapshot."""
    if not rates_used:
        return ""
    sorted_rates = sorted(rates_used, key=lambda r: (r.get("pair", ""), r.get("date", "")))
    raw = json.dumps(sorted_rates, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_or_create_snapshot(
    workspace: Workspace,
    as_of: date | None = None,
    currency_code: str | None = None,
) -> NetWorthCalculation:
    """Retrieve a valid cached snapshot or compute a fresh one from the ledger.

    If the workspace sequence has advanced past the snapshot's ledger_seq,
    the cache is considered stale and recomputed.
    """
    target_date = as_of or timezone.localdate()
    target_currency = currency_code or str(workspace.reporting_currency_id)

    snapshot = NetWorthSnapshot.objects.filter(
        workspace=workspace,
        as_of_date=target_date,
        reporting_currency_code=target_currency,
    ).first()

    # Cache hit and fresh: sequence matches workspace.ledger_seq
    if snapshot and snapshot.ledger_seq == workspace.ledger_seq:
        curr_obj = Currency.objects.get(code=target_currency)
        assets_str = Money(snapshot.assets_minor, target_currency, curr_obj.minor_unit).serialize()
        liabilities_str = Money(
            snapshot.liabilities_minor, target_currency, curr_obj.minor_unit
        ).serialize()
        nw_str = Money(snapshot.net_worth_minor, target_currency, curr_obj.minor_unit).serialize()
        fx_str = Money(snapshot.fx_effect_minor, target_currency, curr_obj.minor_unit).serialize()

        # Fetch prior snapshot for change computation
        prior = (
            NetWorthSnapshot.objects.filter(
                workspace=workspace,
                reporting_currency_code=target_currency,
                as_of_date__lt=target_date,
            )
            .order_by("-as_of_date")
            .first()
        )
        change = None
        if prior:
            diff = snapshot.net_worth_minor - prior.net_worth_minor
            direction = "up" if diff > 0 else ("down" if diff < 0 else "flat")
            change = {
                "amount": Money(diff, target_currency, curr_obj.minor_unit).serialize(),
                "since": prior.as_of_date.isoformat(),
                "direction": direction,
            }

        return NetWorthCalculation(
            as_of=snapshot.as_of_date.isoformat(),
            currency=snapshot.reporting_currency_code,
            assets=assets_str,
            liabilities=liabilities_str,
            net_worth=nw_str,
            assets_minor=snapshot.assets_minor,
            liabilities_minor=snapshot.liabilities_minor,
            net_worth_minor=snapshot.net_worth_minor,
            change=change,
            breakdown=snapshot.breakdown,
            fx_effect=fx_str,
            rate_policy=snapshot.rate_policy,
            rates_used=[],
            ledger_seq=snapshot.ledger_seq,
            computed_from="snapshot",
            conversion_unavailable=False,
        )

    # Cache miss or stale: compute from ledger
    calc = calculate_net_worth(workspace, target_date, target_currency)
    rate_hash = compute_rate_set_hash(calc.rates_used)

    NetWorthSnapshot.objects.update_or_create(
        workspace=workspace,
        as_of_date=target_date,
        reporting_currency_code=target_currency,
        defaults={
            "assets_minor": calc.assets_minor,
            "liabilities_minor": calc.liabilities_minor,
            "net_worth_minor": calc.net_worth_minor,
            "fx_effect_minor": 0,
            "breakdown": calc.breakdown,
            "rate_policy": calc.rate_policy,
            "rate_set_hash": rate_hash,
            "ledger_seq": workspace.ledger_seq,
            "computed_at": timezone.now(),
        },
    )

    return calc


def get_net_worth_history(
    workspace: Workspace,
    from_date: date,
    to_date: date,
    granularity: str = "month",
    currency_code: str | None = None,
) -> dict[str, Any]:
    """Return historical net worth series and table across a date interval."""
    target_currency = currency_code or str(workspace.reporting_currency_id)

    # Generate dates according to granularity
    dates: list[date] = []
    curr = from_date

    if granularity == "day":
        step = timedelta(days=1)
        while curr <= to_date:
            dates.append(curr)
            curr += step
    elif granularity == "week":
        step = timedelta(days=7)
        while curr <= to_date:
            dates.append(curr)
            curr += step
        if dates[-1] != to_date:
            dates.append(to_date)
    else:  # month
        while curr <= to_date:
            # End of current month
            next_month = curr.replace(day=28) + timedelta(days=4)
            end_of_month = next_month - timedelta(days=next_month.day)
            point = min(end_of_month, to_date)
            dates.append(point)
            # Advance to first day of next month
            curr = end_of_month + timedelta(days=1)

    # Remove duplicates and sort
    sorted_dates = sorted(set(dates))

    series: list[dict[str, Any]] = []
    table: list[dict[str, Any]] = []

    for d in sorted_dates:
        calc = get_or_create_snapshot(workspace, as_of=d, currency_code=target_currency)
        stale = calc.ledger_seq < workspace.ledger_seq

        pt = {
            "date": d.isoformat(),
            "assets": calc.assets,
            "liabilities": calc.liabilities,
            "net_worth": calc.net_worth,
            "stale": stale,
        }
        series.append(pt)
        table.append(
            {
                "date": d.isoformat(),
                "assets": calc.assets,
                "liabilities": calc.liabilities,
                "net_worth": calc.net_worth,
            }
        )

    return {
        "currency": target_currency,
        "from": from_date.isoformat(),
        "to": to_date.isoformat(),
        "granularity": granularity,
        "series": series,
        "table": table,
    }
