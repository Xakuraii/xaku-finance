"""Transaction models: Transaction, TransactionSplit, TransactionTag, TransactionAudit."""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import CheckConstraint, Q, UniqueConstraint

from apps.common.models import ArchivedModel, WorkspaceScopedModel


class TransactionType(models.TextChoices):
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"
    TRANSFER = "transfer", "Transfer"
    OPENING_BALANCE = "opening_balance", "Opening Balance"
    DEBT_DISBURSEMENT = "debt_disbursement", "Debt Disbursement"
    DEBT_REPAYMENT = "debt_repayment", "Debt Repayment"
    ADJUSTMENT = "adjustment", "Adjustment"


class TransactionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class NecessityClassification(models.TextChoices):
    ESSENTIAL = "essential", "Essential"
    IMPORTANT = "important", "Important"
    LIFESTYLE = "lifestyle", "Lifestyle"
    UNPLANNED = "unplanned", "Unplanned"


class Transaction(WorkspaceScopedModel, ArchivedModel):
    account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    currency = models.ForeignKey(
        "common.Currency",
        on_delete=models.PROTECT,
        db_column="currency_code",
        related_name="+",
    )
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    status = models.CharField(
        max_length=10,
        choices=TransactionStatus.choices,
        default=TransactionStatus.COMPLETED,
    )
    amount_minor = models.BigIntegerField()
    occurred_on = models.DateField()
    title = models.CharField(max_length=160)
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    merchant = models.CharField(max_length=120, null=True, blank=True)
    category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    necessity = models.CharField(
        max_length=12,
        choices=NecessityClassification.choices,
        null=True,
        blank=True,
    )
    is_split = models.BooleanField(default=False)
    version = models.IntegerField(default=1)
    current_journal_entry = models.ForeignKey(
        "ledger.JournalEntry",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    counterparty_transaction = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="paired_transactions",
    )

    class Meta:
        db_table = "txn_transaction"
        ordering = ["-occurred_on", "-created_at"]
        constraints = [
            CheckConstraint(
                condition=Q(amount_minor__gt=0),
                name="transaction_amount_minor_positive_ck",
            ),
            CheckConstraint(
                condition=Q(status__in=TransactionStatus.values),
                name="transaction_status_ck",
            ),
            CheckConstraint(
                condition=Q(transaction_type__in=TransactionType.values),
                name="transaction_type_ck",
            ),
            CheckConstraint(
                condition=(
                    Q(necessity__isnull=True) | Q(necessity__in=NecessityClassification.values)
                ),
                name="transaction_necessity_ck",
            ),
            CheckConstraint(
                condition=(
                    ~Q(transaction_type__in=[TransactionType.INCOME, TransactionType.EXPENSE])
                    | Q(category__isnull=False)
                    | Q(is_split=True)
                ),
                name="transaction_income_expense_has_category_or_split_ck",
            ),
            CheckConstraint(
                condition=Q(is_split=False) | Q(category__isnull=True),
                name="transaction_split_has_no_single_category_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "-occurred_on", "id"],
                name="txn_ws_date_id_idx",
            ),
            models.Index(
                fields=["workspace", "account", "-occurred_on"],
                name="txn_ws_acc_date_idx",
            ),
            models.Index(
                fields=["workspace", "category", "occurred_on"],
                name="txn_ws_cat_date_idx",
            ),
            models.Index(
                fields=["workspace", "status", "is_archived"],
                name="txn_ws_stat_arch_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title}: {self.amount_minor} {self.currency_id} ({self.occurred_on})"


class TransactionSplit(WorkspaceScopedModel):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="splits",
    )
    category = models.ForeignKey(
        "categories.Category",
        on_delete=models.PROTECT,
        related_name="splits",
    )
    amount_minor = models.BigIntegerField()
    memo = models.CharField(max_length=240, null=True, blank=True)

    class Meta:
        db_table = "txn_transaction_split"
        constraints = [
            CheckConstraint(
                condition=Q(amount_minor__gt=0),
                name="txn_split_amount_positive_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["transaction", "category"],
                name="txn_split_tx_cat_idx",
            ),
            models.Index(
                fields=["workspace", "category"],
                name="txn_split_ws_cat_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Split {self.id}: {self.amount_minor} on {self.category_id}"


class TransactionTag(models.Model):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="tagged_items",
    )
    tag = models.ForeignKey(
        "tags.Tag",
        on_delete=models.PROTECT,
        related_name="transaction_tags",
    )
    workspace = models.ForeignKey(
        "workspaces.Workspace",
        on_delete=models.PROTECT,
        related_name="+",
    )

    class Meta:
        db_table = "txn_transaction_tag"
        constraints = [
            UniqueConstraint(
                fields=["transaction", "tag"],
                name="txn_transaction_tag_pk",
            ),
        ]
        indexes = [
            models.Index(
                fields=["tag", "transaction"],
                name="txn_tag_tag_tx_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_id} tagged with {self.tag_id}"


class TransactionAudit(WorkspaceScopedModel):
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    revision = models.IntegerField()
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    reason = models.CharField(max_length=240)
    changed_fields = models.JSONField(default=list)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)

    class Meta:
        db_table = "txn_transaction_audit"
        ordering = ["revision"]
        constraints = [
            UniqueConstraint(
                fields=["transaction", "revision"],
                name="txn_audit_tx_revision_uq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "transaction", "revision"],
                name="txn_audit_ws_tx_rev_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Audit {self.transaction_id} rev {self.revision}: {self.reason}"


class OpeningBalance(WorkspaceScopedModel):
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name="opening_balance_detail",
    )
    account = models.OneToOneField(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="opening_balance",
    )
    as_of = models.DateField()

    class Meta:
        db_table = "opening_balance"

    def __str__(self) -> str:
        return f"OpeningBalance for {self.account_id} as of {self.as_of}"


class Transfer(WorkspaceScopedModel):
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.CASCADE,
        related_name="transfer_detail",
    )
    source_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="transfers_out",
    )
    destination_account = models.ForeignKey(
        "accounts.Account",
        on_delete=models.PROTECT,
        related_name="transfers_in",
    )
    source_amount_minor = models.BigIntegerField()
    destination_amount_minor = models.BigIntegerField()
    rate = models.DecimalField(max_digits=20, decimal_places=10)
    reference_rate = models.DecimalField(max_digits=20, decimal_places=10, null=True, blank=True)
    conversion_fee_minor = models.BigIntegerField(default=0)
    conversion_fee_category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    transfer_fee_minor = models.BigIntegerField(default=0)
    transfer_fee_category = models.ForeignKey(
        "categories.Category",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    notes = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "transfer"
        constraints = [
            CheckConstraint(
                condition=~Q(source_account=models.F("destination_account")),
                name="transfer_diff_accounts",
            ),
            CheckConstraint(
                condition=Q(source_amount_minor__gt=0)
                & Q(destination_amount_minor__gt=0)
                & Q(rate__gt=0),
                name="transfer_positive_amounts",
            ),
            CheckConstraint(
                condition=Q(conversion_fee_minor__gte=0) & Q(transfer_fee_minor__gte=0),
                name="transfer_non_negative_fees",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Transfer {self.transaction_id}: "
            f"{self.source_account_id} -> {self.destination_account_id}"
        )
