"""Serializers for Liabilities, Debt Repayments, Interest Records, and Projections."""

from __future__ import annotations

from rest_framework import serializers

from apps.common.money import Money
from apps.debts.models import (
    DebtInterestRecord,
    DebtRepayment,
    InterestType,
    Liability,
    LiabilityType,
)
from apps.debts.selectors import LiabilityProgress, get_liability_progress


class LiabilitySerializer(serializers.ModelSerializer):
    currency = serializers.CharField(source="currency_code", read_only=True)
    original_principal = serializers.SerializerMethodField()
    outstanding_principal = serializers.SerializerMethodField()
    outstanding_principal_minor = serializers.SerializerMethodField()
    paid_principal = serializers.SerializerMethodField()
    paid_principal_minor = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    linked_account_name = serializers.CharField(
        source="linked_account.name", read_only=True, default=None
    )

    class Meta:
        model = Liability
        fields = [
            "id",
            "name",
            "liability_type",
            "currency",
            "original_principal",
            "original_principal_minor",
            "outstanding_principal",
            "outstanding_principal_minor",
            "paid_principal",
            "paid_principal_minor",
            "progress_percent",
            "interest_rate",
            "interest_type",
            "lender",
            "due_day",
            "next_due_date",
            "linked_account_id",
            "linked_account_name",
            "ledger_account_id",
            "status",
            "is_archived",
            "notes",
            "created_at",
            "updated_at",
        ]

    def _get_progress(self, obj: Liability) -> LiabilityProgress:
        if not hasattr(obj, "_cached_progress"):
            obj._cached_progress = get_liability_progress(obj)
        return obj._cached_progress

    def get_original_principal(self, obj: Liability) -> str:
        return Money(obj.original_principal_minor, obj.currency_code, 2).serialize()

    def get_outstanding_principal(self, obj: Liability) -> str:
        return self._get_progress(obj).outstanding_principal

    def get_outstanding_principal_minor(self, obj: Liability) -> int:
        return self._get_progress(obj).outstanding_principal_minor

    def get_paid_principal(self, obj: Liability) -> str:
        return self._get_progress(obj).paid_principal

    def get_paid_principal_minor(self, obj: Liability) -> int:
        return self._get_progress(obj).paid_principal_minor

    def get_progress_percent(self, obj: Liability) -> float:
        return self._get_progress(obj).progress_percent


class CreateLiabilitySerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    original_principal = serializers.CharField()
    currency = serializers.CharField(max_length=3)
    liability_type = serializers.ChoiceField(
        choices=LiabilityType.choices, default=LiabilityType.PERSONAL_LOAN
    )
    interest_rate = serializers.DecimalField(
        max_digits=7, decimal_places=4, required=False, allow_null=True
    )
    interest_type = serializers.ChoiceField(choices=InterestType.choices, default=InterestType.NONE)
    lender = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    due_day = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=31)
    next_due_date = serializers.DateField(required=False, allow_null=True)
    linked_account_id = serializers.UUIDField(required=False, allow_null=True)
    initial_disbursement_account_id = serializers.UUIDField(required=False, allow_null=True)
    disbursement_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_currency(self, value: str) -> str:
        return value.strip().upper()


class DebtRepaymentSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(source="currency_code", read_only=True)
    principal_amount = serializers.SerializerMethodField()
    interest_amount = serializers.SerializerMethodField()
    fee_amount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = DebtRepayment
        fields = [
            "id",
            "liability_id",
            "transaction_id",
            "principal_amount",
            "principal_minor",
            "interest_amount",
            "interest_minor",
            "fee_amount",
            "fee_minor",
            "total_amount",
            "total_amount_minor",
            "currency",
            "paid_on",
            "note",
            "created_at",
        ]

    def get_principal_amount(self, obj: DebtRepayment) -> str:
        return Money(obj.principal_minor, obj.currency_code, 2).serialize()

    def get_interest_amount(self, obj: DebtRepayment) -> str:
        return Money(obj.interest_minor, obj.currency_code, 2).serialize()

    def get_fee_amount(self, obj: DebtRepayment) -> str:
        return Money(obj.fee_minor, obj.currency_code, 2).serialize()

    def get_total_amount(self, obj: DebtRepayment) -> str:
        return Money(obj.total_amount_minor, obj.currency_code, 2).serialize()


class CreateDebtRepaymentSerializer(serializers.Serializer):
    paying_account_id = serializers.UUIDField()
    principal_amount = serializers.CharField(default="0.00")
    interest_amount = serializers.CharField(default="0.00")
    fee_amount = serializers.CharField(default="0.00")
    paid_on = serializers.DateField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class DebtInterestRecordSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(source="liability.currency_code", read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = DebtInterestRecord
        fields = [
            "id",
            "liability_id",
            "period_start",
            "period_end",
            "amount",
            "amount_minor",
            "currency",
            "rate_used",
            "interest_type",
            "note",
            "created_at",
        ]

    def get_amount(self, obj: DebtInterestRecord) -> str:
        return Money(obj.amount_minor, obj.liability.currency_code, 2).serialize()


class CreateDebtInterestRecordSerializer(serializers.Serializer):
    amount = serializers.CharField()
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    rate_used = serializers.DecimalField(
        max_digits=7, decimal_places=4, required=False, allow_null=True
    )
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class DebtProjectionSerializer(serializers.Serializer):
    liability_id = serializers.CharField()
    currency = serializers.CharField()
    outstanding_principal_minor = serializers.IntegerField()
    interest_rate = serializers.FloatField(allow_null=True)
    monthly_payment_minor = serializers.IntegerField(allow_null=True)
    estimated_months_to_payoff = serializers.FloatField(allow_null=True)
    total_interest_minor = serializers.IntegerField(allow_null=True)
    projected_payoff_date = serializers.CharField(allow_null=True)
