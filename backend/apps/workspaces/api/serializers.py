"""Serializers for Dashboard assembly and layout management."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers


class WidgetLayoutItemSerializer(serializers.Serializer[Any]):
    key = serializers.CharField(max_length=64)
    title = serializers.CharField(max_length=120, required=False)
    enabled = serializers.BooleanField(default=True)

    def validate_key(self, value: str) -> str:
        # Preserve unknown keys for forward-compatibility, but strip whitespace
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Widget key cannot be empty.")
        return cleaned


class DashboardLayoutSerializer(serializers.Serializer[Any]):
    widgets = serializers.ListField(
        child=WidgetLayoutItemSerializer(),
        allow_empty=True,
    )

    def validate_widgets(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        for item in value:
            k = item["key"]
            if k in seen:
                raise serializers.ValidationError(f"Duplicate widget key '{k}'.")
            seen.add(k)
        return value


class PeriodInfoSerializer(serializers.Serializer[Any]):
    start = serializers.DateField()
    end = serializers.DateField()
    timezone = serializers.CharField()


class ConvertedTotalSerializer(serializers.Serializer[Any]):
    amount = serializers.CharField()
    currency = serializers.CharField()
    rate_policy = serializers.CharField()
    rates_used = serializers.ListField(child=serializers.DictField())


class DashboardResponseSerializer(serializers.Serializer[Any]):
    period = PeriodInfoSerializer()
    widget_order = serializers.ListField(child=serializers.CharField())
    currency = serializers.CharField()
    balances = serializers.ListField(child=serializers.DictField(), required=False)
    converted_total = ConvertedTotalSerializer(required=False)
    net_worth = serializers.DictField(required=False)
    safe_to_spend = serializers.DictField(required=False)
    daily_allowance = serializers.DictField(required=False)
    cash_flow = serializers.DictField(required=False)
    budget_overview = serializers.DictField(required=False)
    savings_progress = serializers.DictField(required=False)
    recent_transactions = serializers.DictField(required=False)
    spending_by_category = serializers.DictField(required=False)
