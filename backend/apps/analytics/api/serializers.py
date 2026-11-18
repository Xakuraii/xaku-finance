"""Serializers for Analytics API: Emergency Fund, Net Worth, Safe-to-Spend, Allowance, Reports."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.analytics.models import (
    ObligationCadence,
    ObligationKind,
    RecurringObligation,
)
from apps.common.money import Money


# ==========================================
# Emergency Fund Serializers
# ==========================================


class EmergencyFundStatusSerializer(serializers.Serializer):
    target_months = serializers.IntegerField()
    designated_account_id = serializers.CharField(allow_null=True)
    designated_account_name = serializers.CharField(allow_null=True)
    designated_goal_id = serializers.CharField(allow_null=True)
    designated_goal_name = serializers.CharField(allow_null=True)
    is_override = serializers.BooleanField()
    monthly_essential_expense = serializers.CharField()
    monthly_essential_expense_minor = serializers.IntegerField()
    computed_monthly_expense = serializers.CharField()
    computed_monthly_expense_minor = serializers.IntegerField()
    override_monthly_expense = serializers.CharField(allow_null=True)
    target_amount = serializers.CharField()
    target_amount_minor = serializers.IntegerField()
    current_savings = serializers.CharField()
    current_savings_minor = serializers.IntegerField()
    remaining_target = serializers.CharField()
    remaining_target_minor = serializers.IntegerField()
    progress_percent = serializers.FloatField()
    currency = serializers.CharField()
    has_earmark_conflict = serializers.BooleanField()
    conflict_details = serializers.CharField(allow_null=True)
    lookback_days = serializers.IntegerField()


class EmergencyFundConfigUpdateSerializer(serializers.Serializer):
    target_months = serializers.IntegerField(required=False, min_value=1)
    designated_account_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    designated_goal_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    monthly_expense_override = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    clear_override = serializers.BooleanField(required=False, default=False)


class EmergencyFundProjectionRequestSerializer(serializers.Serializer):
    monthly_contribution = serializers.CharField(required=True)

    def validate_monthly_contribution(self, value: str) -> str:
        try:
            val = Decimal(value)
            if val <= 0:
                raise serializers.ValidationError("Monthly contribution must be strictly positive.")
        except Exception as exc:
            raise serializers.ValidationError("Invalid monthly contribution amount.") from exc
        return value


class EmergencyFundProjectionSerializer(serializers.Serializer):
    target_amount_minor = serializers.IntegerField()
    current_savings_minor = serializers.IntegerField()
    remaining_target_minor = serializers.IntegerField()
    monthly_contribution_minor = serializers.IntegerField()
    currency = serializers.CharField()
    months_to_target = serializers.FloatField(allow_null=True)
    days_to_target = serializers.IntegerField(allow_null=True)
    projected_completion_date = serializers.CharField(allow_null=True)


# ==========================================
# Net Worth Serializers
# ==========================================


class NetWorthRateUsedSerializer(serializers.Serializer):
    pair = serializers.CharField()
    rate = serializers.CharField()
    date = serializers.CharField()


class NetWorthChangeSerializer(serializers.Serializer):
    amount = serializers.CharField()
    since = serializers.CharField()
    direction = serializers.CharField()


class NetWorthBreakdownItemSerializer(serializers.Serializer):
    account_id = serializers.CharField(allow_null=True, required=False)
    liability_id = serializers.CharField(allow_null=True, required=False)
    name = serializers.CharField()
    kind = serializers.CharField()
    currency = serializers.CharField()
    native_amount = serializers.CharField()
    amount = serializers.CharField()
    outstanding = serializers.CharField(allow_null=True, required=False)


class NetWorthBreakdownSerializer(serializers.Serializer):
    assets = NetWorthBreakdownItemSerializer(many=True)
    liabilities = NetWorthBreakdownItemSerializer(many=True)


class NetWorthResponseSerializer(serializers.Serializer):
    as_of = serializers.CharField()
    currency = serializers.CharField()
    assets = serializers.CharField()
    liabilities = serializers.CharField()
    net_worth = serializers.CharField()
    change = NetWorthChangeSerializer(allow_null=True)
    breakdown = NetWorthBreakdownSerializer()
    fx_effect = serializers.CharField()
    rate_policy = serializers.CharField()
    rates_used = NetWorthRateUsedSerializer(many=True)
    ledger_seq = serializers.IntegerField()
    computed_from = serializers.CharField()
    conversion_unavailable = serializers.BooleanField()


class NetWorthHistoryPointSerializer(serializers.Serializer):
    date = serializers.CharField()
    assets = serializers.CharField()
    liabilities = serializers.CharField()
    net_worth = serializers.CharField()
    stale = serializers.BooleanField()


class NetWorthHistoryResponseSerializer(serializers.Serializer):
    currency = serializers.CharField()
    from_date = serializers.CharField(source="from")
    to_date = serializers.CharField(source="to")
    granularity = serializers.CharField()
    series = NetWorthHistoryPointSerializer(many=True)
    table = serializers.ListField(child=serializers.DictField())


# ==========================================
# Safe-to-Spend Serializers
# ==========================================


class SafeToSpendHorizonSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()
    label = serializers.CharField()


class SafeToSpendComponentsSerializer(serializers.Serializer):
    spendable_balance = serializers.CharField()
    pending_outflows = serializers.CharField()
    reserved_bills = serializers.CharField()
    planned_savings = serializers.CharField()


class SafeToSpendAccountItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    included = serializers.BooleanField()
    balance = serializers.CharField()
    reason = serializers.CharField()


class SafeToSpendExcludedAccountSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    reason = serializers.CharField()


class SafeToSpendResponseSerializer(serializers.Serializer):
    currency = serializers.CharField()
    display = serializers.CharField()
    raw = serializers.CharField()
    is_negative = serializers.BooleanField()
    horizon = SafeToSpendHorizonSerializer()
    components = SafeToSpendComponentsSerializer()
    accounts = SafeToSpendAccountItemSerializer(many=True)
    excluded_accounts = SafeToSpendExcludedAccountSerializer(many=True)
    notes = serializers.ListField(child=serializers.CharField())


# ==========================================
# Daily Allowance Serializers
# ==========================================


class DailyAllowancePeriodSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()
    timezone = serializers.CharField()


class DailyAllowanceBudgetItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    remaining = serializers.CharField()
    flexible = serializers.BooleanField(required=False)
    reason = serializers.CharField(required=False)


class DailyAllowanceResponseSerializer(serializers.Serializer):
    currency = serializers.CharField()
    period = DailyAllowancePeriodSerializer()
    remaining_days = serializers.IntegerField()
    flexible_remaining = serializers.CharField()
    allowance = serializers.CharField()
    state = serializers.CharField()
    explanation = serializers.CharField()
    budgets = DailyAllowanceBudgetItemSerializer(many=True)
    excluded = DailyAllowanceBudgetItemSerializer(many=True)


# ==========================================
# Recurring Obligation Serializer
# ==========================================


class RecurringObligationSerializer(serializers.ModelSerializer):
    amount = serializers.SerializerMethodField()

    class Meta:
        model = RecurringObligation
        fields = [
            "id",
            "name",
            "kind",
            "amount_minor",
            "amount",
            "currency_code",
            "account",
            "category",
            "cadence",
            "next_due_date",
            "is_reserved",
            "auto_post",
            "is_active",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "amount_minor", "created_at", "updated_at"]

    def get_amount(self, obj: RecurringObligation) -> str:
        return Money(obj.amount_minor, obj.currency_code, 2).serialize()

    def create(self, validated_data: dict[str, Any]) -> RecurringObligation:
        amount_input = self.initial_data.get("amount")
        curr = validated_data.get("currency_code", "USD")
        if amount_input:
            money = Money.parse(str(amount_input), curr)
            validated_data["amount_minor"] = money.amount_minor
        elif "amount_minor" not in validated_data:
            raise serializers.ValidationError({"amount": "This field is required."})

        validated_data["workspace"] = self.context["request"].user.workspace
        return super().create(validated_data)

    def update(
        self,
        instance: RecurringObligation,
        validated_data: dict[str, Any],
    ) -> RecurringObligation:
        amount_input = self.initial_data.get("amount")
        if amount_input:
            curr = validated_data.get("currency_code", instance.currency_code)
            money = Money.parse(str(amount_input), curr)
            validated_data["amount_minor"] = money.amount_minor

        return super().update(instance, validated_data)


# ==========================================
# Report Serializers
# ==========================================


class ReportPeriodSerializer(serializers.Serializer):
    start = serializers.CharField()
    end = serializers.CharField()


class ReportReconciliationSerializer(serializers.Serializer):
    ledger_income = serializers.CharField()
    reported_income = serializers.CharField()
    difference = serializers.CharField()
    ledger_expense = serializers.CharField()
    reported_expense = serializers.CharField()
    checked_at = serializers.CharField()


class ReportResponseSerializer(serializers.Serializer):
    period = ReportPeriodSerializer()
    currency = serializers.CharField()
    totals = serializers.DictField()
    series = serializers.ListField(child=serializers.DictField())
    table = serializers.ListField(child=serializers.DictField())
    rate_policy = serializers.CharField()
    rates_used = serializers.ListField(child=serializers.DictField())
    generated_from = serializers.CharField()
    reconciliation = ReportReconciliationSerializer()
