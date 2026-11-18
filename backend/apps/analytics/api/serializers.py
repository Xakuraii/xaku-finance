"""Serializers for Emergency Fund configuration, status, and projections."""

from __future__ import annotations

from decimal import Decimal

from rest_framework import serializers


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
