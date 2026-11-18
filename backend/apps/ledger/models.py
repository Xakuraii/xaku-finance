"""Ledger models: LedgerAccount, JournalEntry, Posting, and ExchangeRate."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, F, Q, UniqueConstraint

from apps.common.models import WorkspaceScopedModel


class LedgerAccountKind(models.TextChoices):
    ASSET = "asset", "Asset"
    LIABILITY = "liability", "Liability"
    EQUITY = "equity", "Equity"
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"


class JournalEntryType(models.TextChoices):
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"
    TRANSFER = "transfer", "Transfer"
    OPENING_BALANCE = "opening_balance", "Opening Balance"
    DEBT_DISBURSEMENT = "debt_disbursement", "Debt Disbursement"
    DEBT_REPAYMENT = "debt_repayment", "Debt Repayment"
    ADJUSTMENT = "adjustment", "Adjustment"
    REVERSAL = "reversal", "Reversal"


class JournalEntryStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    POSTED = "posted", "Posted"
    REVERSED = "reversed", "Reversed"
    CANCELLED = "cancelled", "Cancelled"


class ExchangeRateSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    PROVIDER = "provider", "Provider"
    TRANSFER = "transfer", "Transfer"


class LedgerAccount(WorkspaceScopedModel):
    kind = models.CharField(max_length=10, choices=LedgerAccountKind.choices)
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=120)
    currency = models.ForeignKey(
        "common.Currency",
        on_delete=models.PROTECT,
        db_column="currency_code",
        related_name="+",
    )
    is_system = models.BooleanField(default=False)
    owner_type = models.CharField(max_length=20, null=True, blank=True)
    owner_id = models.UUIDField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "ledger_account"
        constraints = [
            UniqueConstraint(
                fields=["workspace", "code"],
                name="ledger_account_workspace_code_uq",
            ),
            UniqueConstraint(
                fields=["owner_type", "owner_id"],
                condition=Q(owner_id__isnull=False),
                name="ledger_account_owner_uq",
            ),
            CheckConstraint(
                condition=Q(kind__in=LedgerAccountKind.values),
                name="ledger_account_kind_ck",
            ),
            CheckConstraint(
                condition=Q(is_system=False) | Q(owner_id__isnull=True),
                name="ledger_account_system_no_owner_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "kind", "is_active"],
                name="ledger_acc_ws_kind_active_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.currency_id})"


class JournalEntry(WorkspaceScopedModel):
    entry_type = models.CharField(max_length=24, choices=JournalEntryType.choices)
    status = models.CharField(max_length=12, choices=JournalEntryStatus.choices)
    effective_date = models.DateField()
    posted_at = models.DateTimeField(null=True, blank=True)
    source_type = models.CharField(max_length=24)
    source_id = models.UUIDField(null=True, blank=True)
    description = models.CharField(max_length=240, null=True, blank=True)
    fx_snapshot = models.JSONField(default=dict)
    reverses_entry = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reversals",
    )
    reversed_by_entry = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="reversed_entries",
    )
    ledger_seq = models.BigIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        db_table = "journal_entry"
        constraints = [
            UniqueConstraint(
                fields=["workspace", "ledger_seq"],
                name="journal_entry_ws_seq_uq",
            ),
            CheckConstraint(
                condition=Q(entry_type__in=JournalEntryType.values),
                name="journal_entry_type_ck",
            ),
            CheckConstraint(
                condition=Q(status__in=JournalEntryStatus.values),
                name="journal_entry_status_ck",
            ),
            CheckConstraint(
                condition=(
                    ~Q(status=JournalEntryStatus.REVERSED) | Q(reversed_by_entry__isnull=False)
                ),
                name="journal_entry_reversed_link_ck",
            ),
            CheckConstraint(
                condition=~Q(status=JournalEntryStatus.POSTED) | Q(posted_at__isnull=False),
                name="journal_entry_posted_at_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "status", "effective_date"],
                name="journal_entry_ws_stat_date_idx",
            ),
            models.Index(
                fields=["workspace", "source_type", "source_id"],
                name="journal_entry_ws_source_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.entry_type}:{self.status} #{self.ledger_seq} ({self.effective_date})"


class Posting(models.Model):
    id = models.BigAutoField(primary_key=True)
    journal_entry = models.ForeignKey(
        JournalEntry,
        on_delete=models.PROTECT,
        related_name="postings",
    )
    ledger_account = models.ForeignKey(
        LedgerAccount,
        on_delete=models.PROTECT,
        related_name="postings",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.PROTECT,
        related_name="postings",
    )
    currency = models.ForeignKey(
        "common.Currency",
        on_delete=models.PROTECT,
        db_column="currency_code",
        related_name="+",
    )
    amount_minor = models.BigIntegerField()
    memo = models.CharField(max_length=240, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "posting"
        constraints = [
            CheckConstraint(
                condition=~Q(amount_minor=0),
                name="posting_amount_non_zero_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["ledger_account", "journal_entry"],
                name="posting_acc_entry_idx",
            ),
            models.Index(
                fields=["workspace", "currency"],
                name="posting_ws_curr_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Posting {self.id}: {self.amount_minor} {self.currency_id}"


class ExchangeRate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="exchange_rates",
    )
    base_currency = models.ForeignKey(
        "common.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        db_column="base_code",
    )
    quote_currency = models.ForeignKey(
        "common.Currency",
        on_delete=models.PROTECT,
        related_name="+",
        db_column="quote_code",
    )
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    effective_date = models.DateField()
    source = models.CharField(max_length=16, choices=ExchangeRateSource.choices)
    set_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "exchange_rate"
        constraints = [
            UniqueConstraint(
                fields=["workspace", "base_currency", "quote_currency", "effective_date", "source"],
                name="exchange_rate_lookup_uq",
            ),
            CheckConstraint(
                condition=Q(rate__gt=0),
                name="exchange_rate_positive_ck",
            ),
            CheckConstraint(
                condition=~Q(base_currency=F("quote_currency")),
                name="exchange_rate_different_currencies_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["base_currency", "quote_currency", "effective_date"],
                name="exchange_rate_lookup_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.base_currency_id}/{self.quote_currency_id} = {self.rate}"
