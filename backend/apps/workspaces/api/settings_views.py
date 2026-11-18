"""API views for user Profile, Workspace settings, and Workspace summary."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import Account
from apps.budgets.models import Budget
from apps.common.models import Currency
from apps.common.validators import validate_iana_timezone
from apps.debts.models import Liability, LiabilityStatus
from apps.identity.models import UserProfile
from apps.savings.models import SavingsGoal
from apps.transactions.models import Transaction
from apps.workspaces.api.serializers import (
    MeResponseSerializer,
    MeUpdateSerializer,
    WorkspaceDiagnosticSummarySerializer,
    WorkspaceSettingsSerializer,
    WorkspaceSettingsUpdateSerializer,
)


def _ensure_user_profile(user: Any) -> UserProfile:
    """Ensure user profile exists, falling back to workspace values if needed."""
    profile = getattr(user, "profile", None)
    if profile is not None:
        return profile

    ws = getattr(user, "workspace", None)
    default_curr = (
        getattr(ws, "reporting_currency", None)
        or Currency.objects.filter(code="USD").first()
    )
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            "display_name": user.email.split("@")[0],
            "reporting_currency": default_curr,
            "timezone": getattr(ws, "timezone", "UTC"),
            "week_start": getattr(ws, "week_start", 1),
            "locale": "en-US",
            "theme": "system",
        },
    )
    return profile


class MeView(APIView):
    """Retrieve and update current user identity and preferences."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: MeResponseSerializer},
        summary="Get current user profile and preferences",
    )
    def get(self, request: Request) -> Response:
        user = request.user
        profile = _ensure_user_profile(user)

        data = {
            "id": user.id,
            "email": user.email,
            "is_email_verified": user.is_email_verified,
            "display_name": profile.display_name,
            "avatar_url": profile.avatar_url,
            "timezone": profile.timezone,
            "locale": profile.locale,
            "reporting_currency": profile.reporting_currency_id,
            "week_start": profile.week_start,
            "theme": profile.theme,
            "created_at": user.created_at,
        }
        return Response(MeResponseSerializer(data).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=MeUpdateSerializer,
        responses={200: MeResponseSerializer},
        summary="Update current user profile and preferences",
    )
    def patch(self, request: Request) -> Response:
        user = request.user
        profile = _ensure_user_profile(user)

        serializer = MeUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        if "display_name" in vd:
            cleaned_name = vd["display_name"].strip()
            if not cleaned_name:
                raise ValidationError({"display_name": "Display name cannot be empty."})
            profile.display_name = cleaned_name

        if "avatar_url" in vd:
            profile.avatar_url = vd["avatar_url"].strip()

        if "timezone" in vd:
            tz_str = vd["timezone"].strip()
            try:
                validate_iana_timezone(tz_str)
            except DjangoValidationError as exc:
                raise ValidationError({"timezone": "Invalid IANA timezone identifier."}) from exc
            profile.timezone = tz_str

        if "locale" in vd:
            profile.locale = vd["locale"].strip()

        if "week_start" in vd:
            profile.week_start = int(vd["week_start"])

        if "theme" in vd:
            profile.theme = vd["theme"]

        if "reporting_currency" in vd:
            curr_code = vd["reporting_currency"].strip().upper()
            curr = Currency.objects.filter(code=curr_code, is_active=True).first()
            if not curr:
                msg = f"Currency '{curr_code}' not supported."
                raise ValidationError({"reporting_currency": msg})
            profile.reporting_currency = curr

        profile.save()

        data = {
            "id": user.id,
            "email": user.email,
            "is_email_verified": user.is_email_verified,
            "display_name": profile.display_name,
            "avatar_url": profile.avatar_url,
            "timezone": profile.timezone,
            "locale": profile.locale,
            "reporting_currency": profile.reporting_currency_id,
            "week_start": profile.week_start,
            "theme": profile.theme,
            "created_at": user.created_at,
        }
        return Response(MeResponseSerializer(data).data, status=status.HTTP_200_OK)


class WorkspaceSettingsView(APIView):
    """Retrieve and update current user's workspace settings."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: WorkspaceSettingsSerializer},
        summary="Get workspace settings",
    )
    def get(self, request: Request) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            return Response(
                {"detail": "No workspace associated with authenticated user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {
            "id": ws.id,
            "name": ws.name,
            "reporting_currency": ws.reporting_currency_id,
            "timezone": ws.timezone,
            "week_start": ws.week_start,
            "ledger_seq": ws.ledger_seq,
            "created_at": ws.created_at,
            "updated_at": ws.updated_at,
        }
        return Response(WorkspaceSettingsSerializer(data).data, status=status.HTTP_200_OK)

    @extend_schema(
        request=WorkspaceSettingsUpdateSerializer,
        responses={200: WorkspaceSettingsSerializer},
        summary="Update workspace settings",
    )
    def patch(self, request: Request) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            return Response(
                {"detail": "No workspace associated with authenticated user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = WorkspaceSettingsUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        if "name" in vd:
            cleaned_name = vd["name"].strip()
            if not cleaned_name:
                raise ValidationError({"name": "Workspace name cannot be empty."})
            ws.name = cleaned_name

        if "timezone" in vd:
            tz_str = vd["timezone"].strip()
            try:
                validate_iana_timezone(tz_str)
            except DjangoValidationError as exc:
                raise ValidationError({"timezone": "Invalid IANA timezone identifier."}) from exc
            ws.timezone = tz_str

        if "week_start" in vd:
            ws.week_start = int(vd["week_start"])

        if "reporting_currency" in vd:
            curr_code = vd["reporting_currency"].strip().upper()
            curr = Currency.objects.filter(code=curr_code, is_active=True).first()
            if not curr:
                msg = f"Currency '{curr_code}' not supported."
                raise ValidationError({"reporting_currency": msg})
            ws.reporting_currency = curr

        ws.save()

        data = {
            "id": ws.id,
            "name": ws.name,
            "reporting_currency": ws.reporting_currency_id,
            "timezone": ws.timezone,
            "week_start": ws.week_start,
            "ledger_seq": ws.ledger_seq,
            "created_at": ws.created_at,
            "updated_at": ws.updated_at,
        }
        return Response(WorkspaceSettingsSerializer(data).data, status=status.HTTP_200_OK)


class WorkspaceSummaryView(APIView):
    """Retrieve workspace diagnostic summary and record counts."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = WorkspaceDiagnosticSummarySerializer

    @extend_schema(
        responses={200: WorkspaceDiagnosticSummarySerializer},
        summary="Get workspace statistics and diagnostic summary",
    )
    def get(self, request: Request) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            return Response(
                {"detail": "No workspace associated with authenticated user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {
            "id": ws.id,
            "name": ws.name,
            "reporting_currency": ws.reporting_currency_id,
            "timezone": ws.timezone,
            "week_start": ws.week_start,
            "ledger_seq": ws.ledger_seq,
            "accounts_count": Account.objects.filter(workspace=ws, is_archived=False).count(),
            "transactions_count": (
                Transaction.objects.filter(workspace=ws, is_archived=False).count()
            ),
            "budgets_count": Budget.objects.filter(workspace=ws, is_archived=False).count(),
            "savings_goals_count": (
                SavingsGoal.objects.filter(workspace=ws, is_archived=False).count()
            ),
            "debts_count": (
                Liability.objects.filter(workspace=ws)
                .exclude(status=LiabilityStatus.ARCHIVED)
                .count()
            ),
            "created_at": ws.created_at,
        }
        return Response(WorkspaceDiagnosticSummarySerializer(data).data, status=status.HTTP_200_OK)
