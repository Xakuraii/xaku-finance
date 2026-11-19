"""DRF serializers for privacy, export, and deletion endpoints."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.privacy.models import DataExportJob, ExportFormat, ExportScope


class DataExportCreateSerializer(serializers.Serializer[Any]):
    scope = serializers.ChoiceField(choices=ExportScope.choices, default=ExportScope.ALL)
    format = serializers.ChoiceField(choices=ExportFormat.choices, default=ExportFormat.JSON)


class DataExportJobSerializer(serializers.ModelSerializer[DataExportJob]):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = DataExportJob
        fields = [
            "id",
            "scope",
            "format",
            "status",
            "file_size_bytes",
            "download_url",
            "download_expires_at",
            "completed_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_download_url(self, obj: DataExportJob) -> str | None:
        if obj.status == "completed":
            return f"/api/v1/exports/{obj.id}/download/"
        return None


class DataMapItemSerializer(serializers.Serializer[Any]):
    category = serializers.CharField()
    description = serializers.CharField()
    purpose = serializers.CharField()
    lawful_basis = serializers.CharField()
    retention = serializers.CharField()
    shared_with_third_parties = serializers.BooleanField()


class AccountDeletionCreateSerializer(serializers.Serializer[Any]):
    password = serializers.CharField(write_only=True)
    code = serializers.CharField(required=False, allow_blank=True, write_only=True)
    confirm = serializers.CharField(write_only=True)


class AccountDeletionResponseSerializer(serializers.Serializer[Any]):
    status = serializers.CharField()
    execute_after = serializers.DateTimeField()
    backup_expiry_date = serializers.DateField()
    consequences = serializers.ListField(child=serializers.CharField())
