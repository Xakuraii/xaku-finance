"""Serializers for internal account transfers."""

from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Account
from apps.categories.models import Category
from apps.common.money import Money
from apps.transactions.models import Transfer


class AccountBriefSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(source="currency_id")

    class Meta:
        model = Account
        fields = ["id", "name", "currency", "account_type"]


class CategoryBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "kind"]


class TransferSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="transaction_id")
    transaction_id = serializers.UUIDField()
    source_account = AccountBriefSerializer(read_only=True)
    destination_account = AccountBriefSerializer(read_only=True)
    amount = serializers.SerializerMethodField()
    amount_minor = serializers.IntegerField(source="source_amount_minor")
    currency = serializers.CharField(source="source_account.currency_id")
    destination_amount = serializers.SerializerMethodField()
    destination_amount_minor = serializers.IntegerField()
    destination_currency = serializers.CharField(source="destination_account.currency_id")
    rate = serializers.CharField()
    reference_rate = serializers.CharField(allow_null=True)
    transfer_fee = serializers.SerializerMethodField()
    transfer_fee_minor = serializers.IntegerField()
    transfer_fee_category = CategoryBriefSerializer(read_only=True)
    conversion_fee = serializers.SerializerMethodField()
    conversion_fee_minor = serializers.IntegerField()
    conversion_fee_category = CategoryBriefSerializer(read_only=True)
    conversion = serializers.SerializerMethodField()
    occurred_on = serializers.DateField(source="transaction.occurred_on")
    status = serializers.CharField(source="transaction.status")
    is_archived = serializers.BooleanField(source="transaction.is_archived")
    created_at = serializers.DateTimeField(source="transaction.created_at")

    class Meta:
        model = Transfer
        fields = [
            "id",
            "transaction_id",
            "source_account",
            "destination_account",
            "amount",
            "amount_minor",
            "currency",
            "destination_amount",
            "destination_amount_minor",
            "destination_currency",
            "rate",
            "reference_rate",
            "transfer_fee",
            "transfer_fee_minor",
            "transfer_fee_category",
            "conversion_fee",
            "conversion_fee_minor",
            "conversion_fee_category",
            "conversion",
            "occurred_on",
            "notes",
            "status",
            "is_archived",
            "created_at",
        ]

    def get_amount(self, obj: Transfer) -> str:
        curr = obj.source_account.currency_id
        return Money(
            obj.source_amount_minor,
            curr,
            obj.source_account.currency.minor_unit if obj.source_account.currency else 2,
        ).serialize()

    def get_destination_amount(self, obj: Transfer) -> str:
        curr = obj.destination_account.currency_id
        return Money(
            obj.destination_amount_minor,
            curr,
            obj.destination_account.currency.minor_unit if obj.destination_account.currency else 2,
        ).serialize()

    def get_transfer_fee(self, obj: Transfer) -> str:
        curr = obj.source_account.currency_id
        return Money(
            obj.transfer_fee_minor,
            curr,
            obj.source_account.currency.minor_unit if obj.source_account.currency else 2,
        ).serialize()

    def get_conversion_fee(self, obj: Transfer) -> str:
        curr = obj.destination_account.currency_id
        return Money(
            obj.conversion_fee_minor,
            curr,
            obj.destination_account.currency.minor_unit if obj.destination_account.currency else 2,
        ).serialize()

    def get_conversion(self, obj: Transfer) -> dict | None:
        if obj.source_account.currency_id == obj.destination_account.currency_id:
            return None
        dest_curr = obj.destination_account.currency_id
        conv_money = Money(
            obj.conversion_fee_minor,
            dest_curr,
            obj.destination_account.currency.minor_unit if obj.destination_account.currency else 2,
        )
        return {
            "rate": str(obj.rate),
            "reference_rate": str(obj.reference_rate) if obj.reference_rate else None,
            "spread_amount": conv_money.serialize(),
            "spread_currency": dest_curr,
            "spread_amount_minor": obj.conversion_fee_minor,
            "policy_note": "Conversion spread recorded as explicit conversion fee",
        }


class CreateTransferSerializer(serializers.Serializer):
    source_account_id = serializers.UUIDField(required=True)
    destination_account_id = serializers.UUIDField(required=True)
    amount = serializers.CharField(required=True)
    destination_amount = serializers.CharField(required=False, allow_null=True)
    rate = serializers.DecimalField(
        max_digits=20, decimal_places=10, required=False, allow_null=True
    )
    reference_rate = serializers.DecimalField(
        max_digits=20, decimal_places=10, required=False, allow_null=True
    )
    transfer_fee = serializers.CharField(required=False, default="0.00")
    transfer_fee_category_id = serializers.UUIDField(required=False, allow_null=True)
    conversion_fee_category_id = serializers.UUIDField(required=False, allow_null=True)
    occurred_on = serializers.DateField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ArchiveTransferSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, min_length=1, max_length=240)
