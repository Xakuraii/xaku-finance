"""Serializers for Category resources."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.categories.models import Category, CategoryKind


class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "kind",
            "parent_id",
            "icon",
            "color",
            "is_system",
            "sort_order",
            "is_archived",
        ]


class CategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    transaction_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "kind",
            "parent_id",
            "icon",
            "color",
            "is_system",
            "sort_order",
            "is_archived",
            "children",
            "transaction_count",
        ]

    def get_children(self, obj: Category) -> list[dict[str, Any]]:
        # If prefetched, use cached items
        if hasattr(obj, "_prefetched_children"):
            active_children = [c for c in obj._prefetched_children if not c.is_archived]
        else:
            active_children = list(
                obj.children.filter(is_archived=False).order_by("sort_order", "name")
            )
        return SubcategorySerializer(active_children, many=True).data

    def get_transaction_count(self, obj: Category) -> int:
        if hasattr(obj, "tx_count"):
            return obj.tx_count
        return obj.transactions.filter(is_archived=False).count()


class CategoryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80, required=True)
    kind = serializers.ChoiceField(choices=CategoryKind.choices, required=True)
    parent_id = serializers.UUIDField(required=False, allow_null=True)
    icon = serializers.CharField(max_length=40, required=False, allow_null=True, allow_blank=True)
    color = serializers.CharField(max_length=7, required=False, allow_null=True, allow_blank=True)
    sort_order = serializers.IntegerField(required=False, default=0)


class CategoryArchiveSerializer(serializers.Serializer):
    reassign_to_category_id = serializers.UUIDField(required=False, allow_null=True)
