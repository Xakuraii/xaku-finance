"""Serializers for Notifications and User Preferences."""

from __future__ import annotations

from rest_framework import serializers

from apps.notifications.models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id",
            "category",
            "severity",
            "title",
            "body",
            "data",
            "dedupe_key",
            "read_at",
            "created_at",
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id",
            "category",
            "in_app",
            "email",
            "threshold_percent",
            "quiet_hours_start",
            "quiet_hours_end",
            "digest",
            "locked",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]


class BulkNotificationPreferenceSerializer(serializers.Serializer):
    preferences = NotificationPreferenceSerializer(many=True)


class UnreadCountResponseSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()


class ReadActionResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()


class ReadAllResponseSerializer(serializers.Serializer):
    updated_count = serializers.IntegerField()


class EvaluateResponseSerializer(serializers.Serializer):
    evaluated = serializers.BooleanField()
    created_count = serializers.IntegerField()
