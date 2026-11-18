"""Dashboard assembly and layout management service."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.db.models import Sum
from django.utils import timezone

from apps.accounts.models import Account
from apps.analytics.daily_allowance import calculate_daily_allowance
from apps.analytics.net_worth import get_exchange_rate, get_or_create_snapshot
from apps.analytics.reports import get_cash_flow_statement, get_category_report
from apps.analytics.safe_to_spend import calculate_safe_to_spend
from apps.budgets.models import Budget
from apps.common.models import Currency
from apps.common.money import Money, convert
from apps.common.periods import resolve_period
from apps.identity.models import DashboardLayout
from apps.savings.models import SavingsGoal
from apps.transactions.models import Transaction, TransactionStatus, TransactionType
from apps.workspaces.dashboard_registry import get_default_layout, validate_widget_list

if TYPE_CHECKING:
    from apps.identity.models import User
    from apps.workspaces.models import Workspace


def get_user_layout(user: User) -> list[dict[str, Any]]:
    """Retrieve the user's dashboard layout, initializing with canonical defaults if missing."""
    layout, created = DashboardLayout.objects.get_or_create(
        user=user,
        defaults={"widgets": get_default_layout()},
    )
    if not layout.widgets:
        layout.widgets = get_default_layout()
        layout.save(update_fields=["widgets", "updated_at"])
    return list(layout.widgets)


def update_user_layout(user: User, widgets: list[Any]) -> list[dict[str, Any]]:
    """Validate and persist an updated dashboard layout."""
    sanitized = validate_widget_list(widgets)
    layout, _created = DashboardLayout.objects.get_or_create(
        user=user,
        defaults={"widgets": sanitized},
    )
    layout.widgets = sanitized
    layout.version += 1
    layout.save(update_fields=["widgets", "version", "updated_at"])
    return sanitized


def reset_user_layout(user: User) -> list[dict[str, Any]]:
    """Reset the user's dashboard layout to canonical defaults."""
    defaults = get_default_layout()
    layout, _created = DashboardLayout.objects.get_or_create(
        user=user,
        defaults={"widgets": defaults},
    )
    layout.widgets = defaults
    layout.version += 1
    layout.save(update_fields=["widgets", "version", "updated_at"])
    return defaults


def assemble_dashboard(
    user: User,
    workspace: Workspace,
    period_type: str = "calendar_month",
    start_date: date | None = None,
    end_date: date | None = None,
    currency_code: str | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Assemble the aggregated dashboard payload according to user's layout and active period."""
    today = as_of or timezone.localdate()
    target_currency = currency_code or str(workspace.reporting_currency_id)
    curr_map = {c.code: c for c in Currency.objects.all()}
    curr_obj = curr_map.get(target_currency) or Currency.objects.get(code=target_currency)
    target_minor_unit = curr_obj.minor_unit

    # 1. Resolve Period Boundaries
    period_range = resolve_period(
        period=period_type,
        timezone=workspace.timezone,
        anchor=today if period_type != "custom" else None,
        start=start_date if period_type == "custom" else None,
        end=end_date if period_type == "custom" else None,
        week_start=getattr(workspace, "week_start", 1),
    )
    period_start, period_end = period_range.start, period_range.end

    # 2. Retrieve Layout
    layout = get_user_layout(user)
    enabled_keys = [w["key"] for w in layout if w.get("enabled", True)]

    payload: dict[str, Any] = {
        "period": {
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
            "timezone": workspace.timezone,
        },
        "widget_order": enabled_keys,
        "currency": target_currency,
    }

    # 3. Widget: Total Balance per Currency & Converted Consolidated Total
    if "total_balance" in enabled_keys:
        from apps.accounts.selectors import account_balance

        active_accounts = Account.objects.filter(
            workspace=workspace, is_archived=False
        ).select_related("currency")
        balances_by_curr: dict[str, int] = {}
        for acc in active_accounts:
            c_code = acc.currency_id
            bal = account_balance(account=acc, as_of=today)
            balances_by_curr[c_code] = balances_by_curr.get(c_code, 0) + bal.amount_minor

        balances_list: list[dict[str, str]] = []
        converted_sum_minor = 0
        rates_used: list[dict[str, Any]] = []

        for c_code, minor_amt in sorted(balances_by_curr.items()):
            c_obj = curr_map.get(c_code) or Currency.objects.get(code=c_code)
            native_money = Money(minor_amt, c_code, c_obj.minor_unit)
            balances_list.append({
                "currency": c_code,
                "total": native_money.serialize(),
            })

            # Convert to target currency
            rate_info = get_exchange_rate(workspace, c_code, target_currency, today)
            rate_val = rate_info[0] if rate_info else Decimal("1.0")
            if rate_info and c_code != target_currency:
                rates_used.append({
                    "pair": f"{c_code}/{target_currency}",
                    "rate": str(rate_info[0]),
                    "date": rate_info[1].isoformat(),
                })
            converted = convert(native_money, rate_val, target_currency, target_minor_unit)
            converted_sum_minor += converted.amount_minor

        payload["balances"] = balances_list
        payload["converted_total"] = {
            "amount": Money(converted_sum_minor, target_currency, target_minor_unit).serialize(),
            "currency": target_currency,
            "rate_policy": "period_end",
            "rates_used": rates_used,
        }

    # 4. Widget: Net Worth
    if "net_worth" in enabled_keys:
        nw_calc = get_or_create_snapshot(workspace, as_of=today, currency_code=target_currency)
        payload["net_worth"] = {
            "amount": nw_calc.net_worth,
            "currency": nw_calc.currency,
            "assets": nw_calc.assets,
            "liabilities": nw_calc.liabilities,
            "change": nw_calc.change,
            "breakdown": nw_calc.breakdown,
        }

    # 5. Widget: Safe-to-Spend
    if "safe_to_spend" in enabled_keys:
        sts_calc = calculate_safe_to_spend(
            workspace,
            currency_code=target_currency,
            as_of=today,
        )
        payload["safe_to_spend"] = sts_calc.to_dict()

    # 6. Widget: Daily Allowance
    if "daily_allowance" in enabled_keys:
        da_calc = calculate_daily_allowance(
            workspace,
            as_of=today,
            currency_code=target_currency,
        )
        payload["daily_allowance"] = da_calc.to_dict()

    # 7. Widget: Cash Flow (Period Inflows, Outflows, Net)
    if "cash_flow" in enabled_keys:
        cf_data = get_cash_flow_statement(
            workspace=workspace,
            start_date=period_start,
            end_date=period_end,
            currency_code=target_currency,
        )
        payload["cash_flow"] = cf_data

    # 8. Widget: Budget Health / Overview
    if "budget_overview" in enabled_keys:
        active_budgets = (
            Budget.objects.filter(workspace=workspace, is_archived=False)
            .select_related("category")
        )
        if not active_budgets.exists():
            payload["budget_overview"] = {
                "state": "empty",
                "reason": "no_budgets",
                "items": [],
            }
        else:
            from apps.budgets.services.spending import get_budget_category_ids
            from apps.transactions.models import TransactionSplit

            b_items: list[dict[str, Any]] = []
            for b in active_budgets:
                target_cat_ids = get_budget_category_ids(b)
                direct_spent = (
                    Transaction.objects.filter(
                        workspace_id=workspace.id,
                        currency_id=b.currency_id,
                        status=TransactionStatus.COMPLETED,
                        is_archived=False,
                        transaction_type=TransactionType.EXPENSE,
                        is_split=False,
                        category_id__in=target_cat_ids,
                        occurred_on__gte=period_start,
                        occurred_on__lte=period_end,
                    ).aggregate(total=Sum("amount_minor"))["total"]
                    or 0
                )
                split_spent = (
                    TransactionSplit.objects.filter(
                        transaction__workspace_id=workspace.id,
                        transaction__currency_id=b.currency_id,
                        transaction__status=TransactionStatus.COMPLETED,
                        transaction__is_archived=False,
                        transaction__transaction_type=TransactionType.EXPENSE,
                        transaction__occurred_on__gte=period_start,
                        transaction__occurred_on__lte=period_end,
                        category_id__in=target_cat_ids,
                    ).aggregate(total=Sum("amount_minor"))["total"]
                    or 0
                )
                spent_minor = direct_spent + split_spent
                b_curr_code = b.currency_id
                b_curr = curr_map.get(b_curr_code) or Currency.objects.get(code=b_curr_code)
                spent_money = Money(spent_minor, b_curr_code, b_curr.minor_unit)
                base_money = Money(b.base_amount_minor, b_curr_code, b_curr.minor_unit)
                remaining_minor = max(0, b.base_amount_minor - spent_minor)
                remaining_money = Money(remaining_minor, b_curr_code, b_curr.minor_unit)
                pct = (
                    round((spent_minor / b.base_amount_minor * 100.0), 1)
                    if b.base_amount_minor > 0
                    else 0.0
                )

                b_items.append({
                    "id": str(b.id),
                    "name": b.name,
                    "category_name": b.category.name if b.category else None,
                    "spent": spent_money.serialize(),
                    "base": base_money.serialize(),
                    "remaining": remaining_money.serialize(),
                    "percent_used": pct,
                    "is_over_budget": spent_minor > b.base_amount_minor,
                    "currency": b_curr_code,
                })
            payload["budget_overview"] = {
                "state": "ok",
                "items": b_items,
            }

    # 9. Widget: Savings Progress
    if "savings_progress" in enabled_keys:
        active_goals = SavingsGoal.objects.filter(workspace=workspace, is_archived=False)
        if not active_goals.exists():
            payload["savings_progress"] = {
                "state": "empty",
                "reason": "no_goals",
                "items": [],
            }
        else:
            from apps.savings.models import SavingsContribution

            g_items: list[dict[str, Any]] = []
            for g in active_goals:
                g_curr = curr_map.get(g.currency_code) or Currency.objects.get(code=g.currency_code)
                target_m = Money(g.target_amount_minor, g.currency_code, g_curr.minor_unit)
                total_contrib_minor = (
                    SavingsContribution.objects.filter(goal=g).aggregate(
                        s=Sum("amount_minor")
                    )["s"]
                    or 0
                )
                contrib_m = Money(total_contrib_minor, g.currency_code, g_curr.minor_unit)
                pct = (
                    round((total_contrib_minor / g.target_amount_minor * 100.0), 1)
                    if g.target_amount_minor > 0
                    else 0.0
                )
                g_items.append({
                    "id": str(g.id),
                    "name": g.name,
                    "target": target_m.serialize(),
                    "contributed": contrib_m.serialize(),
                    "progress_percent": pct,
                    "target_date": g.target_date.isoformat() if g.target_date else None,
                    "currency": g.currency_code,
                })
            payload["savings_progress"] = {
                "state": "ok",
                "items": g_items,
            }

    # 10. Widget: Recent Transactions
    if "recent_transactions" in enabled_keys:
        recent_txs = (
            Transaction.objects.filter(workspace=workspace)
            .exclude(status=TransactionStatus.CANCELLED)
            .select_related("account", "category")
            .order_by("-occurred_on", "-created_at")[:8]
        )
        if not recent_txs.exists():
            payload["recent_transactions"] = {
                "state": "empty",
                "reason": "no_transactions",
                "items": [],
            }
        else:
            tx_items: list[dict[str, Any]] = []
            for tx in recent_txs:
                t_curr = tx.currency
                t_money = Money(tx.amount_minor, tx.currency_id, t_curr.minor_unit)
                tx_items.append({
                    "id": str(tx.id),
                    "title": tx.title,
                    "amount": t_money.serialize(),
                    "currency": tx.currency_id,
                    "account_name": tx.account.name if tx.account else None,
                    "category_name": tx.category.name if tx.category else None,
                    "occurred_on": tx.occurred_on.isoformat(),
                    "status": tx.status,
                })
            payload["recent_transactions"] = {
                "state": "ok",
                "items": tx_items,
            }

    # 11. Widget: Spending by Category
    if "spending_by_category" in enabled_keys:
        cat_report = get_category_report(
            workspace=workspace,
            start_date=period_start,
            end_date=period_end,
            currency_code=target_currency,
        )
        cat_items = cat_report.get("table", [])
        if not cat_items:
            payload["spending_by_category"] = {
                "state": "empty",
                "reason": "no_expenses",
                "categories": [],
            }
        else:
            payload["spending_by_category"] = {
                "state": "ok",
                "categories": cat_items[:6],
                "total_spending": cat_report.get("totals", {}).get("total_spending", "0.00"),
            }

    return payload
