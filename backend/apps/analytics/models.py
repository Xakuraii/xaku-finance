"""Analytics models: Emergency Fund configuration and targets."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, Q

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
