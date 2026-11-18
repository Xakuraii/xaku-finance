"""Budget models: category budgeting, period lifecycles, and positive-only rollover records."""

from __future__ import annotations

from decimal import Decimal

from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from apps.common.models import WorkspaceScopedModel


class PeriodKind(models.TextChoices):
    CALENDAR_MONTH = "calendar_month", "Calendar Month"
    CALENDAR_WEEK = "calendar_week", "Calendar Week"
    CALENDAR_YEAR = "calendar_year", "Calendar Year"
    CUSTOM = "custom", "Custom"


class FinancialPeriod(WorkspaceScopedModel):
    name = models.CharField(max_length=80)
    kind = models.CharField(
        max_length=16,
        choices=PeriodKind.choices,
        default=PeriodKind.CUSTOM,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "financial_period"
        ordering = ["start_date"]
        constraints = [
            CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="fin_period_end_gte_start_ck",
            ),
            UniqueConstraint(
                fields=["workspace", "kind", "start_date", "end_date"],
                name="fin_period_ws_kind_dates_uq",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_date} to {self.end_date})"


class BudgetPeriodType(models.TextChoices):
    MONTHLY = "monthly", "Monthly"
    WEEKLY = "weekly", "Weekly"
    CUSTOM = "custom", "Custom"


class Budget(WorkspaceScopedModel):
    name = models.CharField(max_length=80)
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.PROTECT,
        related_name="budgets",
    )
    currency = models.ForeignKey(
        "common.Currency",
        on_delete=models.PROTECT,
        db_column="currency_code",
        related_name="+",
    )
    period_type = models.CharField(
        max_length=16,
        choices=BudgetPeriodType.choices,
        default=BudgetPeriodType.MONTHLY,
    )
    custom_period = models.ForeignKey(
        FinancialPeriod,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="budgets",
    )
    base_amount_minor = models.BigIntegerField()
    rollover_enabled = models.BooleanField(default=False)
    rollover_cap_minor = models.BigIntegerField(null=True, blank=True)
    is_flexible = models.BooleanField(default=True)
    warn_at_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("80.00"),
    )
    alert_at_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
    )
    is_archived = models.BooleanField(default=False)
    starts_on = models.DateField()
    ends_on = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "budget"
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["workspace", "is_archived", "period_type"],
                name="budget_ws_arch_type_idx",
            ),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(base_amount_minor__gte=0),
                name="budget_base_minor_nonneg_ck",
            ),
            CheckConstraint(
                condition=Q(rollover_cap_minor__isnull=True) | Q(rollover_cap_minor__gte=0),
                name="budget_rollover_cap_nonneg_ck",
            ),
            CheckConstraint(
                condition=Q(warn_at_percent__gt=0)
                & Q(warn_at_percent__lte=models.F("alert_at_percent")),
                name="budget_warn_alert_pct_ck",
            ),
            CheckConstraint(
                condition=Q(ends_on__isnull=True) | Q(ends_on__gte=models.F("starts_on")),
                name="budget_ends_gte_starts_ck",
            ),
            CheckConstraint(
                condition=~Q(period_type=BudgetPeriodType.CUSTOM) | Q(custom_period__isnull=False),
                name="budget_custom_requires_period_ck",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name}: {self.base_amount_minor} {self.currency_id} ({self.period_type})"


class BudgetPeriodStatus(models.TextChoices):
    OPEN = "open", "Open"
    CLOSED = "closed", "Closed"


class BudgetPeriod(WorkspaceScopedModel):
    budget = models.ForeignKey(
        Budget,
        on_delete=models.PROTECT,
        related_name="periods",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    base_amount_minor = models.BigIntegerField()
    rollover_in_minor = models.BigIntegerField(default=0)
    spent_minor = models.BigIntegerField(default=0)
    rollover_out_minor = models.BigIntegerField(default=0)
    status = models.CharField(
        max_length=8,
        choices=BudgetPeriodStatus.choices,
        default=BudgetPeriodStatus.OPEN,
    )
    ledger_seq = models.BigIntegerField(default=0)
    computed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "budget_period"
        ordering = ["-period_start"]
        indexes = [
            models.Index(
                fields=["workspace", "status", "period_end"],
                name="bdg_period_ws_stat_end_idx",
            ),
        ]
        constraints = [
            UniqueConstraint(
                fields=["budget", "period_start"],
                name="bdg_period_budget_start_uq",
            ),
            CheckConstraint(
                condition=Q(period_end__gte=models.F("period_start")),
                name="bdg_period_end_gte_start_ck",
            ),
            CheckConstraint(
                condition=(
                    Q(base_amount_minor__gte=0)
                    & Q(rollover_in_minor__gte=0)
                    & Q(spent_minor__gte=0)
                    & Q(rollover_out_minor__gte=0)
                ),
                name="bdg_period_amounts_nonneg_ck",
            ),
            CheckConstraint(
                condition=~Q(status=BudgetPeriodStatus.CLOSED) | Q(computed_at__isnull=False),
                name="bdg_period_closed_has_computed_at_ck",
            ),
        ]

    @property
    def total_available_minor(self) -> int:
        return self.base_amount_minor + self.rollover_in_minor

    @property
    def remaining_minor(self) -> int:
        return self.total_available_minor - self.spent_minor

    def __str__(self) -> str:
        return (
            f"Period for {self.budget.name}: {self.period_start}..{self.period_end} "
            f"({self.status}, spent={self.spent_minor}/{self.total_available_minor})"
        )


class BudgetRollover(WorkspaceScopedModel):
    budget_period = models.OneToOneField(
        BudgetPeriod,
        on_delete=models.PROTECT,
        related_name="rollover_in_record",
    )
    source_period = models.ForeignKey(
        BudgetPeriod,
        on_delete=models.PROTECT,
        related_name="rollover_out_record",
    )
    amount_minor = models.BigIntegerField()
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "budget_rollover"
        constraints = [
            CheckConstraint(
                condition=Q(amount_minor__gte=0),
                name="bdg_rollover_amount_nonneg_ck",
            ),
            CheckConstraint(
                condition=~Q(budget_period=models.F("source_period")),
                name="bdg_rollover_distinct_periods_ck",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Rollover of {self.amount_minor} from "
            f"{self.source_period_id} to {self.budget_period_id}"
        )
