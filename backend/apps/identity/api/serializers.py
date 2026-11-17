"""Registration API shapes. Validation only; policy lives in the service."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.common.validators import validate_iana_timezone
from apps.identity.models import User, UserSession
from apps.workspaces.models import Workspace


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(
        write_only=True,
        max_length=128,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    access_expires_in = serializers.IntegerField(read_only=True)
    refresh_expires_in = serializers.IntegerField(read_only=True)


def _device_label(user_agent: str) -> str:
    ua = user_agent or ""
    browser = "Unknown browser"
    for token, label in (
        ("Edg/", "Edge"),
        ("Firefox/", "Firefox"),
        ("Chrome/", "Chrome"),
        ("Safari/", "Safari"),
    ):
        if token in ua:
            browser = label
            break
    operating_system = "Unknown OS"
    for token, label in (
        ("Windows", "Windows"),
        ("Android", "Android"),
        ("iPhone", "iOS"),
        ("iPad", "iPadOS"),
        ("Mac OS X", "macOS"),
        ("Linux", "Linux"),
    ):
        if token in ua:
            operating_system = label
            break
    if not ua:
        return "Unknown device"
    return f"{browser} on {operating_system}"


class SessionSerializer(serializers.ModelSerializer[UserSession]):
    device = serializers.SerializerMethodField()
    current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = ["id", "device", "approx_location", "created_at", "last_used_at", "current"]
        read_only_fields = fields

    def get_device(self, obj: UserSession) -> str:
        return _device_label(obj.user_agent)

    def get_current(self, obj: UserSession) -> bool:
        current_id = self.context.get("current_session_id")
        return current_id is not None and str(obj.id) == str(current_id)


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
    access = serializers.CharField(read_only=True)
    access_expires_in = serializers.IntegerField(read_only=True)
    refresh_expires_in = serializers.IntegerField(read_only=True)
