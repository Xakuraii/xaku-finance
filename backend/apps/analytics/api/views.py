"""API views for Emergency Fund, Net Worth, Safe-to-Spend, Daily Allowance, and Reports."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.api.serializers import (
    DailyAllowanceResponseSerializer,
    EmergencyFundConfigUpdateSerializer,
    EmergencyFundProjectionRequestSerializer,
    EmergencyFundProjectionSerializer,
    EmergencyFundStatusSerializer,
    NetWorthHistoryResponseSerializer,
    NetWorthResponseSerializer,
    RecurringObligationSerializer,
    SafeToSpendResponseSerializer,
)
from apps.analytics.daily_allowance import calculate_daily_allowance
from apps.analytics.emergency_fund import (
    get_emergency_fund_projection,
    get_emergency_fund_status,
    update_emergency_fund_config,
)
from apps.analytics.models import RecurringObligation
from apps.analytics.net_worth import (
    get_net_worth_history,
    get_or_create_snapshot,
)
from apps.analytics.safe_to_spend import calculate_safe_to_spend


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


class NetWorthView(APIView):
    """Retrieve net worth headline, change, breakdown, and FX effect as of a given date."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get net worth as of date",
        responses={200: NetWorthResponseSerializer},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        as_of_param = request.query_params.get("as_of")
        currency_param = request.query_params.get("currency")

        as_of_date = None
        if as_of_param:
            try:
                as_of_date = datetime.strptime(as_of_param, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError({"as_of": "Invalid date format. Expected YYYY-MM-DD."}) from exc

        calc = get_or_create_snapshot(ws, as_of=as_of_date, currency_code=currency_param)
        return Response(calc.to_dict())


class NetWorthHistoryView(APIView):
    """Retrieve historical net worth time-series and accessible data table."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get net worth history",
        responses={200: NetWorthHistoryResponseSerializer},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        from_param = request.query_params.get("from")
        to_param = request.query_params.get("to")
        granularity = request.query_params.get("granularity", "month")
        currency_param = request.query_params.get("currency")

        today = timezone.localdate()
        to_date = today
        if to_param:
            try:
                to_date = datetime.strptime(to_param, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError({"to": "Invalid date format. Expected YYYY-MM-DD."}) from exc

        from_date = to_date - timedelta(days=180)
        if from_param:
            try:
                from_date = datetime.strptime(from_param, "%Y-%m-%d").date()
            except ValueError as exc:
                raise ValidationError({"from": "Invalid date format. Expected YYYY-MM-DD."}) from exc

        if from_date > to_date:
            raise ValidationError({"from": "'from' date cannot be after 'to' date."})

        history = get_net_worth_history(
            ws,
            from_date=from_date,
            to_date=to_date,
            granularity=granularity,
            currency_code=currency_param,
        )
        return Response(history)


class SafeToSpendView(APIView):
    """Calculate liquid Safe-to-Spend allowance and component breakdown."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get Safe-to-Spend",
        responses={200: SafeToSpendResponseSerializer},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        horizon_type = request.query_params.get("horizon", "period_end")
        horizon_days_param = request.query_params.get("horizon_days")
        horizon_days = (
            int(horizon_days_param)
            if horizon_days_param and horizon_days_param.isdigit()
            else None
        )
        currency_param = request.query_params.get("currency")

        res = calculate_safe_to_spend(
            workspace=ws,
            horizon_type=horizon_type,
            horizon_days=horizon_days,
            currency_code=currency_param,
        )
        return Response(res.to_dict())


class DailyAllowanceView(APIView):
    """Calculate daily spending allowance across flexible budget categories."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get daily spending allowance",
        responses={200: DailyAllowanceResponseSerializer},
    )
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        period_kind = request.query_params.get("period", "calendar_month")
        currency_param = request.query_params.get("currency")

        res = calculate_daily_allowance(
            workspace=ws,
            period_kind=period_kind,
            currency_code=currency_param,
        )
        return Response(res.to_dict())


class RecurringObligationViewSet(viewsets.ModelViewSet):
    """CRUD for user recurring obligations, bills, and subscriptions."""

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = RecurringObligationSerializer

    def get_queryset(self):
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return RecurringObligation.objects.none()
        qs = RecurringObligation.objects.filter(workspace=ws)
        include_inactive = (
            self.request.query_params.get("include_inactive", "false").lower() == "true"
        )
        if not include_inactive:
            qs = qs.filter(is_active=True)
        return qs.order_by("next_due_date", "name")
