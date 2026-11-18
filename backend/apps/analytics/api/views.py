"""API views for Emergency Fund status, configuration, and projections."""

from __future__ import annotations

from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.api.serializers import (
    EmergencyFundConfigUpdateSerializer,
    EmergencyFundProjectionRequestSerializer,
    EmergencyFundProjectionSerializer,
    EmergencyFundStatusSerializer,
)
from apps.analytics.emergency_fund import (
    get_emergency_fund_projection,
    get_emergency_fund_status,
    update_emergency_fund_config,
)


class EmergencyFundView(APIView):
    """Retrieve and update emergency fund configuration and coverage status."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get emergency fund status",
        responses={200: EmergencyFundStatusSerializer},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")
        status_data = get_emergency_fund_status(ws)
        serializer = EmergencyFundStatusSerializer(status_data)
        return Response(serializer.data)

    @extend_schema(
        summary="Update emergency fund configuration",
        request=EmergencyFundConfigUpdateSerializer,
        responses={200: EmergencyFundStatusSerializer},
    )
    def patch(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        serializer = EmergencyFundConfigUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            update_emergency_fund_config(
                workspace=ws,
                target_months=data.get("target_months"),
                designated_account_id=data.get("designated_account_id"),
                designated_goal_id=data.get("designated_goal_id"),
                monthly_expense_override=data.get("monthly_expense_override"),
                clear_override=data.get("clear_override", False),
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        updated_status = get_emergency_fund_status(ws)
        return Response(EmergencyFundStatusSerializer(updated_status).data)


class EmergencyFundProjectionView(APIView):
    """Calculate timeline and completion date given regular monthly contributions."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Project emergency fund timeline",
        request=EmergencyFundProjectionRequestSerializer,
        responses={200: EmergencyFundProjectionSerializer},
    )
    def post(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        serializer = EmergencyFundProjectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        monthly_contrib = serializer.validated_data["monthly_contribution"]

        try:
            projection = get_emergency_fund_projection(
                workspace=ws,
                monthly_contribution=monthly_contrib,
            )
        except ValueError as exc:
            raise ValidationError({"detail": str(exc)}) from exc

        return Response(EmergencyFundProjectionSerializer(projection).data)
