"""Serializers for Tag resources and analytics."""

from __future__ import annotations

from rest_framework import serializers

from apps.tags.models import Tag


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "id",
            "name",
            "color",
            "is_system",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]


class TagItemAnalyticsSerializer(serializers.Serializer):
    tag = serializers.CharField()
    amount_minor = serializers.IntegerField()
    amount = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class NecessityItemAnalyticsSerializer(serializers.Serializer):
    necessity = serializers.CharField()
    amount_minor = serializers.IntegerField()
    amount = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()


class TagAnalyticsResponseSerializer(serializers.Serializer):
    currency = serializers.CharField()
    total_expense_minor = serializers.IntegerField()
    total_expense = serializers.CharField()
    by_tag = TagItemAnalyticsSerializer(many=True)
    by_necessity = NecessityItemAnalyticsSerializer(many=True)
