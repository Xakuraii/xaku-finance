"""Serializers for Savings Goals, Contributions, and Projections."""

from __future__ import annotations

from rest_framework import serializers

from apps.common.money import Money
from apps.savings.models import (
    ContributionKind,
    GoalStrategy,
    SavingsAllocation,
    SavingsContribution,
    SavingsGoal,
)
from apps.savings.selectors import (
    GoalProgress,
    get_account_unallocated_balance,
    get_goal_progress,
)


class SavingsAllocationSerializer(serializers.ModelSerializer):
    account_name = serializers.CharField(source="account.name", read_only=True)
    allocated_amount = serializers.SerializerMethodField()

    class Meta:
        model = SavingsAllocation
        fields = [
            "id",
            "account_id",
            "account_name",
            "allocated_minor",
            "allocated_amount",
            "currency_code",
        ]

    def get_allocated_amount(self, obj: SavingsAllocation) -> str:
        return Money(obj.allocated_minor, obj.currency_code, 2).serialize()


class SavingsGoalSerializer(serializers.ModelSerializer):
    currency = serializers.CharField(source="currency_code", read_only=True)
    target_amount = serializers.SerializerMethodField()
    current_amount = serializers.SerializerMethodField()
    current_amount_minor = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()
    is_overfunded = serializers.SerializerMethodField()
    overfunded_amount_minor = serializers.SerializerMethodField()
    linked_account_name = serializers.CharField(
        source="linked_account.name", read_only=True, default=None
    )
    unallocated_capacity = serializers.SerializerMethodField()
    allocations = SavingsAllocationSerializer(many=True, read_only=True)

    class Meta:
        model = SavingsGoal
        fields = [
            "id",
            "name",
            "target_amount",
            "target_amount_minor",
            "currency",
            "target_date",
            "linked_account_id",
            "linked_account_name",
            "strategy",
            "status",
            "notes",
            "is_archived",
            "achieved_at",
            "current_amount",
            "current_amount_minor",
            "progress_percent",
            "is_overfunded",
            "overfunded_amount_minor",
            "unallocated_capacity",
            "allocations",
            "created_at",
            "updated_at",
        ]

    def _get_progress(self, obj: SavingsGoal) -> GoalProgress:
        if not hasattr(obj, "_cached_progress"):
            obj._cached_progress = get_goal_progress(obj)
        return obj._cached_progress

    def get_target_amount(self, obj: SavingsGoal) -> str:
        return Money(obj.target_amount_minor, obj.currency_code, 2).serialize()

    def get_current_amount(self, obj: SavingsGoal) -> str:
        return self._get_progress(obj).current_amount

    def get_current_amount_minor(self, obj: SavingsGoal) -> int:
        return self._get_progress(obj).current_amount_minor

    def get_progress_percent(self, obj: SavingsGoal) -> float:
        return self._get_progress(obj).progress_percent

    def get_is_overfunded(self, obj: SavingsGoal) -> bool:
        return self._get_progress(obj).is_overfunded

    def get_overfunded_amount_minor(self, obj: SavingsGoal) -> int:
        return self._get_progress(obj).overfunded_amount_minor

    def get_unallocated_capacity(self, obj: SavingsGoal) -> int:
        if obj.linked_account:
            return get_account_unallocated_balance(obj.linked_account)
        return 0


class CreateSavingsGoalSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    target_amount = serializers.CharField()
    currency = serializers.CharField(max_length=3)
    target_date = serializers.DateField(required=False, allow_null=True)
    linked_account_id = serializers.UUIDField(required=False, allow_null=True)
    strategy = serializers.ChoiceField(
        choices=GoalStrategy.choices, default=GoalStrategy.LINKED_ACCOUNT
    )
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_currency(self, value: str) -> str:
        return value.strip().upper()


class SavingsContributionSerializer(serializers.ModelSerializer):
    goal_name = serializers.CharField(source="goal.name", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    currency = serializers.CharField(source="currency_code", read_only=True)
    amount = serializers.SerializerMethodField()

    class Meta:
        model = SavingsContribution
        fields = [
            "id",
            "goal_id",
            "goal_name",
            "account_id",
            "account_name",
            "transfer_transaction_id",
            "kind",
            "amount",
            "amount_minor",
            "currency",
            "occurred_on",
            "note",
            "created_at",
        ]

    def get_amount(self, obj: SavingsContribution) -> str:
        return Money(obj.amount_minor, obj.currency_code, 2).serialize()


class RecordContributionSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=ContributionKind.choices)
    amount = serializers.CharField()
    account_id = serializers.UUIDField()
    transfer_transaction_id = serializers.UUIDField(required=False, allow_null=True)
    occurred_on = serializers.DateField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class SavingsProjectionSerializer(serializers.Serializer):
    goal_id = serializers.CharField()
    currency = serializers.CharField()
    target_amount_minor = serializers.IntegerField()
    current_amount_minor = serializers.IntegerField()
    remaining_amount_minor = serializers.IntegerField()
    target_date = serializers.CharField(allow_null=True)
    days_remaining = serializers.IntegerField(allow_null=True)
    months_remaining = serializers.FloatField(allow_null=True)
    required_monthly_contribution = serializers.CharField(allow_null=True)
    projected_completion_date = serializers.CharField(allow_null=True)
