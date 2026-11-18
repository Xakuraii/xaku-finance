"""Serializers for Budget resources and period lifecycle endpoints."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from rest_framework import serializers

from apps.budgets.models import (
    Budget,
    BudgetPeriod,
    BudgetPeriodStatus,
    BudgetPeriodType,
)
from apps.budgets.services.spending import calculate_budget_period_spending
from apps.categories.models import Category
from apps.common.money import Money


class BudgetCategoryBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "kind", "icon", "color"]


class BudgetPeriodSerializer(serializers.ModelSerializer):
    base_amount = serializers.SerializerMethodField()
    rollover_in = serializers.SerializerMethodField()
    spent = serializers.SerializerMethodField()
    rollover_out = serializers.SerializerMethodField()
    total_available_minor = serializers.ReadOnlyField()
    total_available = serializers.SerializerMethodField()
    remaining_minor = serializers.ReadOnlyField()
    remaining = serializers.SerializerMethodField()
    spent_percentage = serializers.SerializerMethodField()
    health_status = serializers.SerializerMethodField()

    class Meta:
        model = BudgetPeriod
        fields = [
            "id",
            "period_start",
            "period_end",
            "base_amount_minor",
            "base_amount",
            "rollover_in_minor",
            "rollover_in",
            "spent_minor",
            "spent",
            "rollover_out_minor",
            "rollover_out",
            "total_available_minor",
            "total_available",
            "remaining_minor",
            "remaining",
            "spent_percentage",
            "status",
            "health_status",
            "computed_at",
        ]

    def _get_currency(self, obj: BudgetPeriod) -> str:
        return obj.budget.currency_id

    def _get_minor_unit(self, obj: BudgetPeriod) -> int:
        return getattr(obj.budget.currency, "minor_unit", 2)

    def get_base_amount(self, obj: BudgetPeriod) -> str:
        return Money(
            obj.base_amount_minor, self._get_currency(obj), self._get_minor_unit(obj)
        ).serialize()

    def get_rollover_in(self, obj: BudgetPeriod) -> str:
        return Money(
            obj.rollover_in_minor, self._get_currency(obj), self._get_minor_unit(obj)
        ).serialize()

    def get_spent(self, obj: BudgetPeriod) -> str:
        # If open, recalculate dynamically to ensure live spending accuracy
        if obj.status == BudgetPeriodStatus.OPEN:
            spent = calculate_budget_period_spending(obj)
        else:
            spent = obj.spent_minor
        return Money(spent, self._get_currency(obj), self._get_minor_unit(obj)).serialize()

    def get_rollover_out(self, obj: BudgetPeriod) -> str:
        return Money(
            obj.rollover_out_minor, self._get_currency(obj), self._get_minor_unit(obj)
        ).serialize()

    def get_total_available(self, obj: BudgetPeriod) -> str:
        return Money(
            obj.total_available_minor, self._get_currency(obj), self._get_minor_unit(obj)
        ).serialize()

    def get_remaining(self, obj: BudgetPeriod) -> str:
        # Calculate with fresh spending
        spent = (
            calculate_budget_period_spending(obj)
            if obj.status == BudgetPeriodStatus.OPEN
            else obj.spent_minor
        )
        rem = obj.total_available_minor - spent
        return Money(rem, self._get_currency(obj), self._get_minor_unit(obj)).serialize()

    def get_spent_percentage(self, obj: BudgetPeriod) -> float:
        total = obj.total_available_minor
        if total <= 0:
            return 0.0
        spent = (
            calculate_budget_period_spending(obj)
            if obj.status == BudgetPeriodStatus.OPEN
            else obj.spent_minor
        )
        return round((spent / total) * 100, 1)

    def get_health_status(self, obj: BudgetPeriod) -> str:
        spent = (
            calculate_budget_period_spending(obj)
            if obj.status == BudgetPeriodStatus.OPEN
            else obj.spent_minor
        )
        total = obj.total_available_minor
        if spent > total:
            return "over_budget"
        pct = (spent / total * 100) if total > 0 else 0
        if pct >= float(obj.budget.alert_at_percent):
            return "alert"
        if pct >= float(obj.budget.warn_at_percent):
            return "warning"
        return "on_track"


class BudgetSerializer(serializers.ModelSerializer):
    category = BudgetCategoryBriefSerializer(read_only=True)
    currency = serializers.CharField(source="currency_id", read_only=True)
    base_amount = serializers.SerializerMethodField()
    rollover_cap = serializers.SerializerMethodField()
    current_period = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id",
            "name",
            "category",
            "currency",
            "period_type",
            "base_amount_minor",
            "base_amount",
            "rollover_enabled",
            "rollover_cap_minor",
            "rollover_cap",
            "is_flexible",
            "warn_at_percent",
            "alert_at_percent",
            "is_archived",
            "starts_on",
            "ends_on",
            "current_period",
            "created_at",
            "updated_at",
        ]

    def get_base_amount(self, obj: Budget) -> str:
        unit = getattr(obj.currency, "minor_unit", 2)
        return Money(obj.base_amount_minor, obj.currency_id, unit).serialize()

    def get_rollover_cap(self, obj: Budget) -> str | None:
        if obj.rollover_cap_minor is None:
            return None
        unit = getattr(obj.currency, "minor_unit", 2)
        return Money(obj.rollover_cap_minor, obj.currency_id, unit).serialize()

    def get_current_period(self, obj: Budget) -> dict[str, Any] | None:
        # Active open period
        active_period = (
            obj.periods.filter(status=BudgetPeriodStatus.OPEN).order_by("-period_start").first()
        )
        if not active_period:
            active_period = obj.periods.order_by("-period_start").first()
        if active_period:
            return BudgetPeriodSerializer(active_period).data
        return None


class BudgetCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, required=True)
    category_id = serializers.UUIDField(required=True)
    amount = serializers.CharField(required=True)
    currency = serializers.CharField(max_length=3, required=True)
    period_type = serializers.ChoiceField(
        choices=BudgetPeriodType.choices,
        default=BudgetPeriodType.MONTHLY,
    )
    rollover_enabled = serializers.BooleanField(default=False)
    rollover_cap = serializers.CharField(required=False, allow_null=True, default=None)
    is_flexible = serializers.BooleanField(default=True)
    warn_at_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("80.00"),
    )
    alert_at_percent = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
    )
    starts_on = serializers.DateField(required=False, allow_null=True)
    ends_on = serializers.DateField(required=False, allow_null=True)
    custom_period_id = serializers.UUIDField(required=False, allow_null=True)


class BudgetOverviewItemSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    category = BudgetCategoryBriefSerializer()
    spent = serializers.CharField()
    spent_minor = serializers.IntegerField()
    total_available = serializers.CharField()
    total_available_minor = serializers.IntegerField()
    remaining = serializers.CharField()
    remaining_minor = serializers.IntegerField()
    spent_percentage = serializers.FloatField()
    health_status = serializers.CharField()
    is_flexible = serializers.BooleanField()


class BudgetOverviewSerializer(serializers.Serializer):
    currency = serializers.CharField()
    total_budgeted_minor = serializers.IntegerField()
    total_budgeted = serializers.CharField()
    total_spent_minor = serializers.IntegerField()
    total_spent = serializers.CharField()
    total_remaining_minor = serializers.IntegerField()
    total_remaining = serializers.CharField()
    budgets = BudgetOverviewItemSerializer(many=True)
