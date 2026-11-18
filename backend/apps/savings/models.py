"""Savings models: goals, allocations, and contribution history."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from apps.common.models import WorkspaceScopedModel


class GoalStrategy(models.TextChoices):
    LINKED_ACCOUNT = "linked_account", "Linked Account"
    EARMARK = "earmark", "Earmark"


class GoalStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    ACHIEVED = "achieved", "Achieved"
    PAUSED = "paused", "Paused"
    ARCHIVED = "archived", "Archived"


class ContributionKind(models.TextChoices):
    TRANSFER_IN = "transfer_in", "Transfer In"
    EARMARK = "earmark", "Earmark"
    ADJUSTMENT = "adjustment", "Adjustment"
    WITHDRAWAL = "withdrawal", "Withdrawal"


class SavingsGoal(WorkspaceScopedModel):
    name = models.CharField(max_length=120)
    target_amount_minor = models.BigIntegerField()
    currency_code = models.CharField(max_length=3)
    target_date = models.DateField(null=True, blank=True)
    linked_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="savings_goals",
    )
    strategy = models.CharField(
        max_length=16,
        choices=GoalStrategy.choices,
        default=GoalStrategy.LINKED_ACCOUNT,
    )
    status = models.CharField(
        max_length=12,
        choices=GoalStatus.choices,
        default=GoalStatus.ACTIVE,
    )
    notes = models.TextField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)
    achieved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "savings_goal"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["workspace", "status", "target_date"],
                name="ix_savings_goal_ws_status_date",
            ),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(target_amount_minor__gt=0),
                name="ck_savings_goal_target_gt_0",
            ),
            CheckConstraint(
                condition=(
                    ~Q(strategy=GoalStrategy.LINKED_ACCOUNT) | Q(linked_account__isnull=False)
                ),
                name="ck_savings_goal_linked_account_required",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.target_amount} {self.currency_code})"

    @property
    def target_amount(self) -> str:
        from apps.common.money import Money

        return Money(self.target_amount_minor, self.currency_code, 2).serialize()


class SavingsContribution(WorkspaceScopedModel):
    goal = models.ForeignKey(
        SavingsGoal,
        on_delete=models.PROTECT,
        related_name="contributions",
    )
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="savings_contributions",
    )
    transfer_transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="savings_contributions",
    )
    kind = models.CharField(
        max_length=16,
        choices=ContributionKind.choices,
    )
    amount_minor = models.BigIntegerField()  # signed: positive adds, negative withdraws
    currency_code = models.CharField(max_length=3)
    occurred_on = models.DateField()
    note = models.CharField(max_length=240, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="savings_contributions",
    )

    class Meta:
        db_table = "savings_contribution"
        ordering = ["-occurred_on", "-created_at"]
        indexes = [
            models.Index(
                fields=["goal", "-occurred_on"],
                name="ix_savings_contrib_goal_date",
            ),
            models.Index(
                fields=["account", "-occurred_on"],
                name="ix_savings_contrib_acct_date",
            ),
        ]
        constraints = [
            CheckConstraint(
                condition=~Q(amount_minor=0),
                name="ck_savings_contrib_amount_not_zero",
            ),
            CheckConstraint(
                condition=(
                    ~Q(kind=ContributionKind.TRANSFER_IN)
                    | (Q(transfer_transaction__isnull=False) & Q(amount_minor__gt=0))
                ),
                name="ck_savings_contrib_transfer_requires_tx",
            ),
            CheckConstraint(
                condition=(~Q(kind=ContributionKind.WITHDRAWAL) | Q(amount_minor__lt=0)),
                name="ck_savings_contrib_withdrawal_negative",
            ),
            CheckConstraint(
                condition=(
                    ~Q(kind__in=[ContributionKind.EARMARK, ContributionKind.ADJUSTMENT])
                    | Q(transfer_transaction__isnull=True)
                ),
                name="ck_savings_contrib_earmark_no_transfer_tx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.kind}: {self.amount_minor} {self.currency_code} -> {self.goal.name}"


class SavingsAllocation(WorkspaceScopedModel):
    goal = models.ForeignKey(
        SavingsGoal,
        on_delete=models.PROTECT,
        related_name="allocations",
    )
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="savings_allocations",
    )
    allocated_minor = models.BigIntegerField(default=0)
    currency_code = models.CharField(max_length=3)

    class Meta:
        db_table = "savings_allocation"
        indexes = [
            models.Index(fields=["account"], name="ix_savings_alloc_acct"),
        ]
        constraints = [
            UniqueConstraint(
                fields=["goal", "account"],
                name="uq_savings_allocation_goal_account",
            ),
            CheckConstraint(
                condition=Q(allocated_minor__gte=0),
                name="ck_savings_allocation_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.goal.name} @ {self.account.name}: {self.allocated_minor} {self.currency_code}"
        )
