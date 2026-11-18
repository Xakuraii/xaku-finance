"""Account model: represents user financial accounts."""

from __future__ import annotations

from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint
from django.db.models.functions import Lower

from apps.common.models import ArchivedModel, WorkspaceScopedModel


class AccountType(models.TextChoices):
    CHECKING = "checking", "Checking"
    SAVINGS = "savings", "Savings"
    CASH = "cash", "Cash"
    EWALLET = "ewallet", "E-Wallet"
    CREDIT_CARD = "credit_card", "Credit Card"
    INVESTMENT = "investment", "Investment"
    OTHER = "other", "Other"


class AccountNature(models.TextChoices):
    ASSET = "asset", "Asset"
    LIABILITY = "liability", "Liability"


class Account(WorkspaceScopedModel, ArchivedModel):
    name = models.CharField(max_length=80)
    account_type = models.CharField(max_length=20, choices=AccountType.choices)
    currency = models.ForeignKey(
        "common.Currency",
        on_delete=models.PROTECT,
        db_column="currency_code",
        related_name="+",
    )
    nature = models.CharField(max_length=10, choices=AccountNature.choices)
    description = models.TextField(null=True, blank=True)
    is_spendable = models.BooleanField(default=False)
    allows_negative_balance = models.BooleanField(default=False)
    display_order = models.IntegerField(default=0)
    opened_on = models.DateField()
    archive_reason = models.CharField(max_length=240, null=True, blank=True)

    class Meta:
        db_table = "account"
        ordering = ["display_order", "name"]
        constraints = [
            UniqueConstraint(
                fields=["id", "currency"],
                name="account_id_currency_uq",
            ),
            UniqueConstraint(
                Lower("name"),
                "workspace",
                condition=Q(is_archived=False),
                name="account_workspace_lower_name_uq",
            ),
            CheckConstraint(
                condition=Q(account_type__in=AccountType.values),
                name="account_type_ck",
            ),
            CheckConstraint(
                condition=Q(nature__in=AccountNature.values),
                name="account_nature_ck",
            ),
            CheckConstraint(
                condition=~Q(account_type=AccountType.SAVINGS) | Q(is_spendable=False),
                name="account_savings_not_spendable_ck",
            ),
            CheckConstraint(
                condition=(
                    ~Q(account_type=AccountType.CREDIT_CARD) | Q(nature=AccountNature.LIABILITY)
                ),
                name="account_credit_card_is_liability_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "is_archived", "display_order"],
                name="account_ws_arch_order_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.currency_id})"
