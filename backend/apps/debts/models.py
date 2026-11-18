"""Debt models: liabilities, split repayments, and accrued interest records."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, Q

from apps.common.models import WorkspaceScopedModel


class LiabilityType(models.TextChoices):
    PERSONAL_LOAN = "personal_loan", "Personal Loan"
    STUDENT_LOAN = "student_loan", "Student Loan"
    CREDIT_CARD = "credit_card", "Credit Card"
    MORTGAGE = "mortgage", "Mortgage"
    FAMILY_LOAN = "family_loan", "Family Loan"
    OTHER = "other", "Other"


class InterestType(models.TextChoices):
    NONE = "none", "None"
    SIMPLE = "simple", "Simple"
    COMPOUND = "compound", "Compound"


class LiabilityStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    PAID_OFF = "paid_off", "Paid Off"
    ARCHIVED = "archived", "Archived"


class Liability(WorkspaceScopedModel):
    name = models.CharField(max_length=120)
    liability_type = models.CharField(
        max_length=20,
        choices=LiabilityType.choices,
        default=LiabilityType.PERSONAL_LOAN,
    )
    currency_code = models.CharField(max_length=3)
    original_principal_minor = models.BigIntegerField()
    interest_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
    )
    interest_type = models.CharField(
        max_length=8,
        choices=InterestType.choices,
        default=InterestType.NONE,
    )
    lender = models.CharField(max_length=120, null=True, blank=True)
    due_day = models.SmallIntegerField(null=True, blank=True)
    next_due_date = models.DateField(null=True, blank=True)
    linked_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="linked_liabilities",
    )
    ledger_account = models.OneToOneField(
        "ledger.LedgerAccount",
        on_delete=models.PROTECT,
        related_name="liability",
    )
    status = models.CharField(
        max_length=12,
        choices=LiabilityStatus.choices,
        default=LiabilityStatus.ACTIVE,
    )
    is_archived = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "liability"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["workspace", "status", "next_due_date"],
                name="ix_liability_ws_status_due",
            ),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(original_principal_minor__gt=0),
                name="ck_liability_principal_gt_0",
            ),
            CheckConstraint(
                condition=Q(interest_rate__isnull=True) | Q(interest_rate__gte=0),
                name="ck_liability_interest_rate_non_negative",
            ),
            CheckConstraint(
                condition=Q(interest_type=InterestType.NONE) | Q(interest_rate__isnull=False),
                name="ck_liability_interest_type_requires_rate",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.liability_type})"

    @property
    def original_principal(self) -> str:
        from apps.common.money import Money

        return Money(self.original_principal_minor, self.currency_code, 2).serialize()


class DebtRepayment(WorkspaceScopedModel):
    liability = models.ForeignKey(
        Liability,
        on_delete=models.PROTECT,
        related_name="repayments",
    )
    transaction = models.OneToOneField(
        "transactions.Transaction",
        on_delete=models.PROTECT,
        related_name="debt_repayment",
    )
    principal_minor = models.BigIntegerField(default=0)
    interest_minor = models.BigIntegerField(default=0)
    fee_minor = models.BigIntegerField(default=0)
    currency_code = models.CharField(max_length=3)
    paid_on = models.DateField()
    note = models.CharField(max_length=240, null=True, blank=True)

    class Meta:
        db_table = "debt_repayment"
        ordering = ["-paid_on", "-created_at"]
        indexes = [
            models.Index(
                fields=["liability", "-paid_on"],
                name="ix_debt_repay_liab_paid_on",
            ),
        ]
        constraints = [
            CheckConstraint(
                condition=(
                    Q(principal_minor__gte=0) & Q(interest_minor__gte=0) & Q(fee_minor__gte=0)
                ),
                name="ck_debt_repayment_components_non_negative",
            ),
            CheckConstraint(
                condition=Q(principal_minor__gt=0) | Q(interest_minor__gt=0) | Q(fee_minor__gt=0),
                name="ck_debt_repayment_total_gt_0",
            ),
        ]

    def __str__(self) -> str:
        total = self.principal_minor + self.interest_minor + self.fee_minor
        return (
            f"Repayment to {self.liability.name}: {total} {self.currency_code} "
            f"(P:{self.principal_minor} I:{self.interest_minor} F:{self.fee_minor})"
        )

    @property
    def total_amount_minor(self) -> int:
        return self.principal_minor + self.interest_minor + self.fee_minor


class DebtInterestRecord(WorkspaceScopedModel):
    liability = models.ForeignKey(
        Liability,
        on_delete=models.PROTECT,
        related_name="interest_records",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    amount_minor = models.BigIntegerField()
    rate_used = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        null=True,
        blank=True,
    )
    interest_type = models.CharField(
        max_length=8,
        choices=InterestType.choices,
        default=InterestType.SIMPLE,
    )
    posted_transaction = models.ForeignKey(
        "transactions.Transaction",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="accrued_interest_records",
    )
    note = models.CharField(max_length=240, null=True, blank=True)

    class Meta:
        db_table = "debt_interest_record"
        ordering = ["-period_end", "-created_at"]
        indexes = [
            models.Index(
                fields=["liability", "-period_end"],
                name="ix_debt_interest_liab_end",
            ),
        ]
        constraints = [
            CheckConstraint(
                condition=Q(amount_minor__gt=0) & Q(period_end__gte=models.F("period_start")),
                name="ck_debt_interest_amount_and_dates",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Interest on {self.liability.name}: {self.amount_minor} {self.liability.currency_code}"
        )
