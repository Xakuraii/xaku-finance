"""Serializers for Account models and API endpoints."""

from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Account, AccountType
from apps.accounts.selectors import account_balance
from apps.common.money import Money


class AccountSerializer(serializers.ModelSerializer):
    """Full account representation including dynamic ledger balance."""

    currency = serializers.CharField(source="currency_id")
    balance = serializers.SerializerMethodField()
    balance_minor = serializers.SerializerMethodField()
    balance_display = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = [
            "id",
            "name",
            "account_type",
            "currency",
            "nature",
            "description",
            "is_spendable",
            "allows_negative_balance",
            "display_order",
            "opened_on",
            "is_archived",
            "archived_at",
            "archive_reason",
            "balance",
            "balance_minor",
            "balance_display",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def _get_balance(self, obj: Account) -> Money:
        if not hasattr(obj, "_cached_balance"):
            obj._cached_balance = account_balance(account=obj)
        return obj._cached_balance

    def get_balance(self, obj: Account) -> str:
        return self._get_balance(obj).serialize()

    def get_balance_minor(self, obj: Account) -> int:
        return self._get_balance(obj).amount_minor

    def get_balance_display(self, obj: Account) -> str:
        bal = self._get_balance(obj)
        return f"{bal.serialize()} {bal.currency}"


class AccountCreateSerializer(serializers.Serializer):
    """Input validation for creating a new account."""

    name = serializers.CharField(max_length=80)
    account_type = serializers.ChoiceField(choices=AccountType.choices)
    currency = serializers.CharField(max_length=3)
    opening_balance = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    opening_balance_date = serializers.DateField(required=False, allow_null=True)
    is_spendable = serializers.BooleanField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    allows_negative_balance = serializers.BooleanField(required=False, default=False)
    opened_on = serializers.DateField(required=False, allow_null=True)


class AccountUpdateSerializer(serializers.Serializer):
    """Input validation for updating account metadata."""

    name = serializers.CharField(max_length=80, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    is_spendable = serializers.BooleanField(required=False)
    allows_negative_balance = serializers.BooleanField(required=False)
    display_order = serializers.IntegerField(required=False)
    currency = serializers.CharField(max_length=3, required=False)


class AccountArchiveSerializer(serializers.Serializer):
    """Input validation for archiving an account."""

    reason = serializers.CharField(max_length=240, required=True)
    acknowledge_balance = serializers.BooleanField(required=False, default=False)


class AccountOpeningBalanceSerializer(serializers.Serializer):
    """Input validation for creating an opening balance on an existing account."""

    amount = serializers.CharField(required=True)
    as_of = serializers.DateField(required=False)
