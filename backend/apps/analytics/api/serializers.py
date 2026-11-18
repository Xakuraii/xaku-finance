"""Serializers for Analytics API: Emergency Fund, Net Worth, Safe-to-Spend, Allowance, Reports."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers


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
