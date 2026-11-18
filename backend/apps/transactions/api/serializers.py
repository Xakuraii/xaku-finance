"""Serializers for transactions, splits, and audit history."""

from __future__ import annotations

from rest_framework import serializers

from apps.common.money import Money
from apps.transactions.models import (
    NecessityClassification,
    Transaction,
    TransactionAudit,
    TransactionSplit,
    TransactionStatus,
    TransactionType,
)


class SplitInputSerializer(serializers.Serializer):
    """Input serializer for a single split line."""

    category_id = serializers.UUIDField()
    amount = serializers.CharField()
    memo = serializers.CharField(required=False, allow_blank=True, default="")


class SplitOutputSerializer(serializers.ModelSerializer):
    """Output serializer for transaction splits."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    amount = serializers.SerializerMethodField()
    amount_display = serializers.SerializerMethodField()

    class Meta:
        model = TransactionSplit
        fields = [
            "id",
            "category_id",
            "category_name",
            "amount",
            "amount_minor",
            "amount_display",
            "memo",
        ]

    def get_amount(self, obj: TransactionSplit) -> str:
        curr = obj.transaction.currency_id
        minor_unit = obj.transaction.currency.minor_unit if obj.transaction.currency else 2
        money = Money(amount_minor=obj.amount_minor, currency=curr, minor_unit=minor_unit)
        return money.serialize()

    def get_amount_display(self, obj: TransactionSplit) -> str:
        curr = obj.transaction.currency_id
        minor_unit = obj.transaction.currency.minor_unit if obj.transaction.currency else 2
        money = Money(amount_minor=obj.amount_minor, currency=curr, minor_unit=minor_unit)
        return f"{money.serialize()} {curr}"


class TransactionCreateSerializer(serializers.Serializer):
    """Input serializer for creating a transaction."""

    type = serializers.ChoiceField(
        choices=TransactionType.choices,
        default=TransactionType.EXPENSE,
        required=False,
    )
    account_id = serializers.UUIDField()
    amount = serializers.CharField()
    currency = serializers.CharField(max_length=3)
    occurred_on = serializers.DateField()
    title = serializers.CharField(max_length=160)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    splits = SplitInputSerializer(many=True, required=False)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False)
    necessity = serializers.ChoiceField(
        choices=NecessityClassification.choices,
        required=False,
        allow_null=True,
    )
    status = serializers.ChoiceField(
        choices=TransactionStatus.choices,
        default=TransactionStatus.COMPLETED,
        required=False,
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    merchant = serializers.CharField(required=False, allow_blank=True, default="")


class TransactionUpdateSerializer(serializers.Serializer):
    """Input serializer for audited transaction update."""

    expected_version = serializers.IntegerField(required=True)
    reason = serializers.CharField(max_length=240, required=True)
    amount = serializers.CharField(required=False)
    category_id = serializers.UUIDField(required=False, allow_null=True)
    splits = SplitInputSerializer(many=True, required=False)
    title = serializers.CharField(max_length=160, required=False)
    occurred_on = serializers.DateField(required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    merchant = serializers.CharField(required=False, allow_blank=True)
    tags = serializers.ListField(child=serializers.CharField(max_length=50), required=False)
    necessity = serializers.ChoiceField(
        choices=NecessityClassification.choices,
        required=False,
        allow_null=True,
    )


class TransactionArchiveSerializer(serializers.Serializer):
    """Input serializer for archiving a transaction."""

    reason = serializers.CharField(max_length=240, required=True)


class TransactionAuditSerializer(serializers.ModelSerializer):
    """Output serializer for transaction audit revisions."""

    actor_email = serializers.CharField(source="actor.email", default=None, read_only=True)
    action = serializers.SerializerMethodField()
    snapshot = serializers.JSONField(source="after", read_only=True)

    class Meta:
        model = TransactionAudit
        fields = [
            "id",
            "revision",
            "action",
            "reason",
            "changed_fields",
            "before",
            "after",
            "snapshot",
            "actor_email",
            "created_at",
        ]

    def get_action(self, obj: TransactionAudit) -> str:
        if obj.revision == 1:
            return "create"
        if "is_archived" in obj.changed_fields:
            return "archive" if obj.after.get("is_archived") else "restore"
        return "update"


class TransactionSerializer(serializers.ModelSerializer):
    """Full transaction output serializer."""

    account_name = serializers.CharField(source="account.name", read_only=True)
    category_name = serializers.CharField(source="category.name", default=None, read_only=True)
    currency = serializers.CharField(source="currency_id")
    type = serializers.CharField(source="transaction_type")
    amount = serializers.SerializerMethodField()
    amount_display = serializers.SerializerMethodField()
    splits = SplitOutputSerializer(many=True, read_only=True)
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "account_id",
            "account_name",
            "type",
            "status",
            "amount",
            "amount_minor",
            "amount_display",
            "currency",
            "occurred_on",
            "title",
            "description",
            "notes",
            "merchant",
            "category_id",
            "category_name",
            "is_split",
            "splits",
            "tags",
            "necessity",
            "version",
            "is_archived",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_amount(self, obj: Transaction) -> str:
        minor_unit = obj.currency.minor_unit if obj.currency else 2
        money = Money(
            amount_minor=obj.amount_minor, currency=obj.currency_id, minor_unit=minor_unit
        )
        return money.serialize()

    def get_amount_display(self, obj: Transaction) -> str:
        minor_unit = obj.currency.minor_unit if obj.currency else 2
        money = Money(
            amount_minor=obj.amount_minor, currency=obj.currency_id, minor_unit=minor_unit
        )
        return f"{money.serialize()} {obj.currency_id}"

    def get_tags(self, obj: Transaction) -> list[str]:
        if hasattr(obj, "_prefetched_tags"):
            return obj._prefetched_tags
        return [item.tag.name for item in obj.tagged_items.all()]
