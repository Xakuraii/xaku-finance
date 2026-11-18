"""Automated background evaluators generating deduplicated notifications.

Evaluates budget thresholds, upcoming bill reminders, and savings milestones.
See docs/SRS.md FR-NOT-03..05.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from django.db.models import Sum
from django.utils import timezone

from apps.analytics.models import RecurringObligation
from apps.budgets.models import Budget
from apps.budgets.services.spending import get_budget_category_ids
from apps.common.models import Currency
from apps.common.money import Money
from apps.common.periods import resolve_period
from apps.notifications.models import (
    Notification,
    NotificationCategory,
    NotificationSeverity,
)
from apps.notifications.services.notifications import create_notification
from apps.savings.models import SavingsContribution, SavingsGoal
from apps.transactions.models import (
    Transaction,
    TransactionSplit,
    TransactionStatus,
    TransactionType,
)

if TYPE_CHECKING:
    from apps.workspaces.models import Workspace


def evaluate_budget_notifications(
    workspace: Workspace,
    as_of: date | None = None,
) -> list[Notification]:
    """Scan active budgets and generate threshold warnings (default 80% and 100%)."""
    today = as_of or timezone.localdate()
    range_obj = resolve_period(
        period="calendar_month",
        timezone=workspace.timezone,
        anchor=today,
        week_start=getattr(workspace, "week_start", 1),
    )
    period_start, period_end = range_obj.start, range_obj.end

    created_notifs: list[Notification] = []
    budgets = Budget.objects.filter(workspace=workspace, is_archived=False).select_related(
        "category"
    )

    for b in budgets:
        target_cats = get_budget_category_ids(b)
        direct_spent = (
            Transaction.objects.filter(
                workspace_id=workspace.id,
                currency_id=b.currency_id,
                status=TransactionStatus.COMPLETED,
                is_archived=False,
                transaction_type=TransactionType.EXPENSE,
                is_split=False,
                category_id__in=target_cats,
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
                category_id__in=target_cats,
            ).aggregate(total=Sum("amount_minor"))["total"]
            or 0
        )
        total_spent_minor = direct_spent + split_spent
        if b.base_amount_minor <= 0:
            continue

        pct = (total_spent_minor / b.base_amount_minor) * 100.0
        b_curr = Currency.objects.get(code=b.currency_id)
        spent_str = Money(total_spent_minor, b.currency_id, b_curr.minor_unit).serialize()
        base_str = Money(b.base_amount_minor, b.currency_id, b_curr.minor_unit).serialize()

        # 1. 100% threshold
        if pct >= float(b.alert_at_percent):
            notif, created = create_notification(
                user=workspace.owner,
                workspace=workspace,
                category=NotificationCategory.BUDGET,
                severity=NotificationSeverity.CRITICAL,
                title=f"Budget Exceeded: {b.name}",
                body=(
                    f"You have spent {spent_str} of your {base_str} "
                    f"{b.currency_id} budget ({round(pct, 1)}%)."
                ),
                dedupe_key=f"budget:{b.id}:{period_start}:100",
                data={
                    "budget_id": str(b.id),
                    "budget_name": b.name,
                    "spent": spent_str,
                    "base": base_str,
                    "percent": round(pct, 1),
                },
            )
            if created and notif:
                created_notifs.append(notif)
        # 2. 80% threshold
        elif pct >= float(b.warn_at_percent):
            notif, created = create_notification(
                user=workspace.owner,
                workspace=workspace,
                category=NotificationCategory.BUDGET,
                severity=NotificationSeverity.WARNING,
                title=f"Budget Warning: {b.name}",
                body=(
                    f"You have used {round(pct, 1)}% of your {base_str} "
                    f"{b.currency_id} budget ({spent_str} spent)."
                ),
                dedupe_key=f"budget:{b.id}:{period_start}:80",
                data={
                    "budget_id": str(b.id),
                    "budget_name": b.name,
                    "spent": spent_str,
                    "base": base_str,
                    "percent": round(pct, 1),
                },
            )
            if created and notif:
                created_notifs.append(notif)

    return created_notifs


def evaluate_bill_notifications(
    workspace: Workspace,
    as_of: date | None = None,
    window_days: int = 3,
) -> list[Notification]:
    """Scan active recurring obligations due within the lookahead window."""
    today = as_of or timezone.localdate()
    lookahead = today + timedelta(days=window_days)

    created_notifs: list[Notification] = []
    obligations = RecurringObligation.objects.filter(
        workspace=workspace,
        is_active=True,
        next_due_date__gte=today,
        next_due_date__lte=lookahead,
    )

    for obl in obligations:
        c_obj = Currency.objects.get(code=obl.currency_code)
        amt_str = Money(obl.amount_minor, obl.currency_code, c_obj.minor_unit).serialize()
        days_diff = (obl.next_due_date - today).days

        when_str = "today" if days_diff == 0 else f"in {days_diff} days"
        dedupe_key = f"bill:{obl.id}:{obl.next_due_date.isoformat()}"

        notif, created = create_notification(
            user=workspace.owner,
            workspace=workspace,
            category=NotificationCategory.BILL,
            severity=NotificationSeverity.INFO if days_diff > 1 else NotificationSeverity.WARNING,
            title=f"Upcoming Payment: {obl.name}",
            body=(
                f"{obl.name} payment of {amt_str} {obl.currency_code} "
                f"is due {when_str} on {obl.next_due_date.isoformat()}."
            ),
            dedupe_key=dedupe_key,
            data={
                "obligation_id": str(obl.id),
                "name": obl.name,
                "amount": amt_str,
                "due_date": obl.next_due_date.isoformat(),
            },
        )
        if created and notif:
            created_notifs.append(notif)

    return created_notifs


def evaluate_savings_notifications(
    workspace: Workspace,
) -> list[Notification]:
    """Scan active savings goals for milestone achievements (50% and 100%)."""
    created_notifs: list[Notification] = []
    goals = SavingsGoal.objects.filter(workspace=workspace, is_archived=False)

    for g in goals:
        if g.target_amount_minor <= 0:
            continue
        contrib_minor = (
            SavingsContribution.objects.filter(goal=g).aggregate(s=Sum("amount_minor"))["s"] or 0
        )
        pct = (contrib_minor / g.target_amount_minor) * 100.0

        g_curr = Currency.objects.get(code=g.currency_code)
        contrib_str = Money(contrib_minor, g.currency_code, g_curr.minor_unit).serialize()
        target_str = Money(g.target_amount_minor, g.currency_code, g_curr.minor_unit).serialize()

        # 100% Milestone
        if pct >= 100.0:
            notif, created = create_notification(
                user=workspace.owner,
                workspace=workspace,
                category=NotificationCategory.SAVINGS,
                severity=NotificationSeverity.INFO,
                title=f"Goal Achieved: {g.name}!",
                body=(
                    f"Congratulations! You reached 100% of your target "
                    f"for {g.name} ({target_str} {g.currency_code})."
                ),
                dedupe_key=f"savings:{g.id}:100",
                data={"goal_id": str(g.id), "name": g.name, "milestone": 100},
            )
            if created and notif:
                created_notifs.append(notif)
        # 50% Milestone
        elif pct >= 50.0:
            notif, created = create_notification(
                user=workspace.owner,
                workspace=workspace,
                category=NotificationCategory.SAVINGS,
                severity=NotificationSeverity.INFO,
                title=f"Goal Halfway There: {g.name}",
                body=(
                    f"You've saved {contrib_str} of your {target_str} "
                    f"{g.currency_code} target for {g.name} (50%+)."
                ),
                dedupe_key=f"savings:{g.id}:50",
                data={"goal_id": str(g.id), "name": g.name, "milestone": 50},
            )
            if created and notif:
                created_notifs.append(notif)

    return created_notifs
