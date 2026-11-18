"""API views for Financial Reports with ledger reconciliation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.api.serializers import ReportResponseSerializer
from apps.analytics.reports import (
    get_category_report,
    get_cash_flow_statement,
    get_income_expense_report,
)


def parse_report_date_range(request: Request) -> tuple[Any, Any, str | None]:
    start_param = request.query_params.get("start")
    end_param = request.query_params.get("end")
    currency_param = request.query_params.get("currency")

    today = timezone.localdate()
    end_date = today
    if end_param:
        try:
            end_date = datetime.strptime(end_param, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError({"end": "Invalid date format. Expected YYYY-MM-DD."}) from exc

    start_date = end_date - timedelta(days=90)
    if start_param:
        try:
            start_date = datetime.strptime(start_param, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValidationError({"start": "Invalid date format. Expected YYYY-MM-DD."}) from exc

    if start_date > end_date:
        raise ValidationError({"start": "'start' date cannot be after 'end' date."})

    return start_date, end_date, currency_param


class IncomeReportView(APIView):
    """Retrieve Income statement report with periodic breakdown and ledger reconciliation."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Get income report", responses={200: ReportResponseSerializer})
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        start_date, end_date, curr = parse_report_date_range(request)
        report = get_income_expense_report(ws, start_date, end_date, curr)
        return Response(report)


class ExpenseReportView(APIView):
    """Retrieve Expense statement report with periodic breakdown and ledger reconciliation."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Get expense report", responses={200: ReportResponseSerializer})
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        start_date, end_date, curr = parse_report_date_range(request)
        report = get_income_expense_report(ws, start_date, end_date, curr)
        return Response(report)


class CategoryReportView(APIView):
    """Retrieve category spending shares and breakdown with ledger reconciliation."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Get category report", responses={200: ReportResponseSerializer})
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        start_date, end_date, curr = parse_report_date_range(request)
        report = get_category_report(ws, start_date, end_date, curr)
        return Response(report)


class CashFlowReportView(APIView):
    """Retrieve cash flow statement excluding internal transfers with ledger reconciliation."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Get cash flow report", responses={200: ReportResponseSerializer})
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        start_date, end_date, curr = parse_report_date_range(request)
        report = get_cash_flow_statement(ws, start_date, end_date, curr)
        return Response(report)


class TrendsReportView(APIView):
    """Retrieve periodic spending and income trends with ledger reconciliation."""

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(summary="Get trends report", responses={200: ReportResponseSerializer})
    def get(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = getattr(request.user, "workspace", None)
        if not ws:
            raise ValidationError("Authenticated user does not belong to a workspace.")

        start_date, end_date, curr = parse_report_date_range(request)
        report = get_income_expense_report(ws, start_date, end_date, curr)
        return Response(report)
