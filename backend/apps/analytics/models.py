"""Analytics models: Emergency Fund, Net Worth Snapshots, and Recurring Obligations."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from django.utils import timezone

from apps.common.models import WorkspaceScopedModel


class EmergencyFundConfig(WorkspaceScopedModel):
    target_months = models.SmallIntegerField(default=6)
    designated_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_configs",
    )
    designated_goal = models.ForeignKey(
        "savings.SavingsGoal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="emergency_configs",
    )
    monthly_expense_override_minor = models.BigIntegerField(null=True, blank=True)
    currency_code = models.CharField(max_length=3, default="USD")

    class Meta:
        db_table = "analytics_emergency_fund_config"
        constraints = [
            CheckConstraint(
                condition=Q(target_months__gt=0),
                name="ck_emergency_target_months_gt_0",
            ),
            CheckConstraint(
                condition=(
                    Q(monthly_expense_override_minor__isnull=True)
                    | Q(monthly_expense_override_minor__gt=0)
                ),
                name="ck_emergency_override_gt_0",
            ),
        ]

    def __str__(self) -> str:
        return f"Emergency Fund Config ({self.workspace.name}): {self.target_months} mos"


class NetWorthSnapshot(WorkspaceScopedModel):
    as_of_date = models.DateField()
    reporting_currency_code = models.CharField(max_length=3, default="USD")
    assets_minor = models.BigIntegerField()
    liabilities_minor = models.BigIntegerField()
    net_worth_minor = models.BigIntegerField()
    fx_effect_minor = models.BigIntegerField(default=0)
    breakdown = models.JSONField(default=dict)
    rate_policy = models.CharField(max_length=20, default="period_end")
    rate_set_hash = models.CharField(max_length=64, default="")
    ledger_seq = models.BigIntegerField()
    computed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "net_worth_snapshot"
        ordering = ["-as_of_date"]
        constraints = [
            UniqueConstraint(
                fields=["workspace", "as_of_date", "reporting_currency_code"],
                name="net_worth_snapshot_ws_date_curr_uq",
            ),
            CheckConstraint(
                condition=Q(assets_minor__gte=0) & Q(liabilities_minor__gte=0),
                name="ck_snapshot_non_negative_assets_liabilities",
            ),
            CheckConstraint(
                condition=Q(
                    net_worth_minor=models.F("assets_minor") - models.F("liabilities_minor")
                ),
                name="ck_snapshot_net_worth_equality",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "as_of_date"],
                name="ix_snapshot_ws_date",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"NetWorthSnapshot {self.as_of_date} ({self.reporting_currency_code}): "
            f"{self.net_worth_minor} (seq: {self.ledger_seq})"
        )


class ObligationKind(models.TextChoices):
    BILL = "bill", "Bill"
    SUBSCRIPTION = "subscription", "Subscription"
    RESERVED = "reserved", "Reserved"
    SAVINGS_PLAN = "savings_plan", "Savings Plan"


class ObligationCadence(models.TextChoices):
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    QUARTERLY = "quarterly", "Quarterly"
    YEARLY = "yearly", "Yearly"
    ONE_OFF = "one_off", "One Off"


class RecurringObligation(WorkspaceScopedModel):
    name = models.CharField(max_length=120)
    kind = models.CharField(
        max_length=16,
        choices=ObligationKind.choices,
        default=ObligationKind.BILL,
    )
    amount_minor = models.BigIntegerField()
    currency_code = models.CharField(max_length=3, default="USD")
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_obligations",
    )
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recurring_obligations",
    )
    cadence = models.CharField(
        max_length=12,
        choices=ObligationCadence.choices,
        default=ObligationCadence.MONTHLY,
    )
    next_due_date = models.DateField()
    is_reserved = models.BooleanField(default=True)
    auto_post = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "recurring_obligation"
        ordering = ["next_due_date", "name"]
        constraints = [
            CheckConstraint(
                condition=Q(amount_minor__gt=0),
                name="ck_obligation_amount_gt_0",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "is_active", "next_due_date"],
                name="ix_obligation_ws_active_due",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.name} ({self.kind}): {self.amount_minor} "
            f"{self.currency_code} due {self.next_due_date}"
        )
