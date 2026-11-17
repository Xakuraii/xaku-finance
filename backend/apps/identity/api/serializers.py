"""Registration API shapes. Validation only; policy lives in the service."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.common.validators import validate_iana_timezone
from apps.identity.models import User
from apps.workspaces.models import Workspace


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        write_only=True,
        min_length=12,
        max_length=128,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    display_name = serializers.CharField(max_length=80)
    timezone = serializers.CharField(max_length=64, default="UTC")
    reporting_currency = serializers.CharField(max_length=3, default="USD")

    def validate_timezone(self, value: str) -> str:
        try:
            validate_iana_timezone(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError("Unknown timezone.") from exc
        return value

    def validate_reporting_currency(self, value: str) -> str:
        return value.strip().upper()


class UserSummarySerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "email", "is_email_verified", "created_at"]
        read_only_fields = fields


class WorkspaceSummarySerializer(serializers.ModelSerializer[Workspace]):
    reporting_currency = serializers.CharField(source="reporting_currency.code", read_only=True)

    class Meta:
        model = Workspace
        fields = ["id", "name", "reporting_currency", "timezone", "week_start"]
        read_only_fields = fields


class RegisterResponseSerializer(serializers.Serializer):
    user = UserSummarySerializer(read_only=True)
    workspace = WorkspaceSummarySerializer(read_only=True)
