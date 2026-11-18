"""Management command to close expired budget periods and roll balances forward."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.budgets.models import BudgetPeriod, BudgetPeriodStatus
from apps.budgets.services.rollover import close_budget_period


class Command(BaseCommand):
    help = "Close expired budget periods and process positive rollover."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--as-of",
            type=str,
            default=None,
            help="Reference date YYYY-MM-DD (defaults to today).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        as_of_str = options.get("as_of")
        if as_of_str:
            as_of = date.fromisoformat(as_of_str)
        else:
            as_of = timezone.now().date()

        expired_periods = BudgetPeriod.objects.filter(
            status=BudgetPeriodStatus.OPEN,
            period_end__lt=as_of,
        ).order_by("period_start")

        closed_count = 0
        for period in expired_periods:
            close_budget_period(workspace=period.workspace, period_id=period.id)
            closed_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully closed {closed_count} budget period(s) as of {as_of}."
            )
        )
