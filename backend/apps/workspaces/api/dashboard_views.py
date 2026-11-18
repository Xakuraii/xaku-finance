"""API views for Dashboard assembly and layout customization."""

from __future__ import annotations

from datetime import datetime

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.workspaces.api.serializers import (
    DashboardLayoutSerializer,
    DashboardResponseSerializer,
)
from apps.workspaces.services import (
    assemble_dashboard,
    get_user_layout,
    reset_user_layout,
    update_user_layout,
)


class DashboardView(APIView):
    """Retrieve aggregated dashboard payload assembled for active layout and period."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: DashboardResponseSerializer},
        summary="Get assembled dashboard data",
    )
    def get(self, request: Request) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            return Response(
                {"detail": "No workspace associated with authenticated user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        period_type = request.query_params.get("period", "calendar_month")
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")
        currency_param = request.query_params.get("currency")
        as_of_param = request.query_params.get("as_of")

        start_date = None
        end_date = None
        as_of_date = None

        if start_param:
            try:
                start_date = datetime.strptime(start_param, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {"start": "Invalid date format. Expected YYYY-MM-DD."}
                ) from exc
        if end_param:
            try:
                end_date = datetime.strptime(end_param, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {"end": "Invalid date format. Expected YYYY-MM-DD."}
                ) from exc
        if as_of_param:
            try:
                as_of_date = datetime.strptime(as_of_param, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError(
                    {"as_of": "Invalid date format. Expected YYYY-MM-DD."}
                ) from exc

        if period_type == "custom" and (not start_date or not end_date):
            raise ValidationError(
                {"period": "Custom period requires both 'start' and 'end' parameters."}
            )

        data = assemble_dashboard(
            user=request.user,
            workspace=ws,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            currency_code=currency_param,
            as_of=as_of_date,
        )
        return Response(data)


class DashboardLayoutView(APIView):
    """Retrieve or replace user's customizable dashboard layout."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: DashboardLayoutSerializer},
        summary="Get dashboard widget layout",
    )
    def get(self, request: Request) -> Response:
        widgets = get_user_layout(request.user)
        return Response({"widgets": widgets})

    @extend_schema(
        request=DashboardLayoutSerializer,
        responses={200: DashboardLayoutSerializer},
        summary="Update dashboard widget layout",
    )
    def put(self, request: Request) -> Response:
        serializer = DashboardLayoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated = update_user_layout(request.user, serializer.validated_data["widgets"])
        return Response({"widgets": updated})


class DashboardLayoutResetView(APIView):
    """Reset user's dashboard layout to canonical defaults."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: DashboardLayoutSerializer},
        summary="Reset dashboard widget layout to default",
    )
    def post(self, request: Request) -> Response:
        resetted = reset_user_layout(request.user)
        return Response({"widgets": resetted})
