"""ViewSet for Budget and BudgetPeriod resources."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.budgets.api.serializers import (
    BudgetCreateSerializer,
    BudgetOverviewSerializer,
    BudgetPeriodSerializer,
    BudgetSerializer,
)
from apps.budgets.models import Budget, BudgetPeriodStatus
from apps.budgets.services.create import create_budget
from apps.budgets.services.rollover import close_budget_period
from apps.budgets.services.spending import calculate_budget_period_spending
from apps.common.models import Currency
from apps.common.money import Money
from apps.common.permissions import IsWorkspaceMember


class BudgetViewSet(viewsets.ModelViewSet):
    """ViewSet for managing category budgets and tracking period spending."""

    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    serializer_class = BudgetSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Budget]:
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return Budget.objects.none()

        qs = (
            Budget.objects.filter(workspace=ws)
            .select_related("category", "currency")
            .prefetch_related("periods")
        )

        qp = self.request.query_params
        include_archived = qp.get("include_archived", "false").lower() == "true"
        if not include_archived and self.action not in ("retrieve", "archive"):
            qs = qs.filter(is_archived=False)

        if "category_id" in qp:
            qs = qs.filter(category_id=qp["category_id"])

        return qs.order_by("name")

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = BudgetCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        budget = create_budget(
            workspace=request.user.workspace,
            name=vd["name"],
            category_id=vd["category_id"],
            amount=vd["amount"],
            currency=vd["currency"],
            period_type=vd.get("period_type", "monthly"),
            rollover_enabled=vd.get("rollover_enabled", False),
            rollover_cap=vd.get("rollover_cap"),
            is_flexible=vd.get("is_flexible", True),
            warn_at_percent=vd.get("warn_at_percent", 80),
            alert_at_percent=vd.get("alert_at_percent", 100),
            starts_on=vd.get("starts_on"),
            ends_on=vd.get("ends_on"),
            custom_period_id=vd.get("custom_period_id"),
        )

        return Response(BudgetSerializer(budget).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: Any = None) -> Response:
        budget = self.get_object()
        budget.is_archived = True
        budget.save(update_fields=["is_archived", "updated_at"])
        return Response(BudgetSerializer(budget).data, status=status.HTTP_200_OK)

    @extend_schema(responses={200: BudgetPeriodSerializer(many=True)})
    @action(detail=True, methods=["get"])
    def periods(self, request: Request, pk: Any = None) -> Response:
        budget = self.get_object()
        periods = budget.periods.all().order_by("-period_start")
        return Response(BudgetPeriodSerializer(periods, many=True).data)

    @extend_schema(responses={200: BudgetPeriodSerializer})
    @action(detail=True, methods=["post"])
    def close_period(self, request: Request, pk: Any = None) -> Response:
        budget = self.get_object()
        active_period = (
            budget.periods.filter(status=BudgetPeriodStatus.OPEN).order_by("-period_start").first()
        )
        if not active_period:
            return Response(
                {"detail": "No open period to close for this budget."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        closed, next_p = close_budget_period(
            workspace=request.user.workspace,
            period_id=active_period.id,
        )
        return Response(
            {
                "closed_period": BudgetPeriodSerializer(closed).data,
                "next_period": BudgetPeriodSerializer(next_p).data if next_p else None,
            },
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses={200: BudgetOverviewSerializer})
    @action(detail=False, methods=["get"])
    def overview(self, request: Request) -> Response:
        ws = request.user.workspace
        currency = request.query_params.get("currency") or getattr(
            ws, "default_currency_code", "USD"
        )
        curr_obj = Currency.objects.filter(code=currency).first()
        minor_unit = curr_obj.minor_unit if curr_obj else 2

        active_budgets = (
            Budget.objects.filter(
                workspace=ws,
                is_archived=False,
                currency_id=currency,
            )
            .select_related("category", "currency")
            .prefetch_related("periods")
        )

        total_budgeted_minor = 0
        total_spent_minor = 0
        overview_items = []

        for b in active_budgets:
            active_p = (
                b.periods.filter(status=BudgetPeriodStatus.OPEN).order_by("-period_start").first()
            )
            if not active_p:
                continue

            spent = calculate_budget_period_spending(active_p)
            avail = active_p.total_available_minor
            rem = avail - spent

            total_budgeted_minor += avail
            total_spent_minor += spent

            pct = round((spent / avail * 100), 1) if avail > 0 else 0.0
            if spent > avail:
                health = "over_budget"
            elif pct >= float(b.alert_at_percent):
                health = "alert"
            elif pct >= float(b.warn_at_percent):
                health = "warning"
            else:
                health = "on_track"

            overview_items.append(
                {
                    "id": b.id,
                    "name": b.name,
                    "category": {
                        "id": b.category.id,
                        "name": b.category.name,
                        "kind": b.category.kind,
                        "icon": b.category.icon,
                        "color": b.category.color,
                    },
                    "spent": Money(spent, currency, minor_unit).serialize(),
                    "spent_minor": spent,
                    "total_available": Money(avail, currency, minor_unit).serialize(),
                    "total_available_minor": avail,
                    "remaining": Money(rem, currency, minor_unit).serialize(),
                    "remaining_minor": rem,
                    "spent_percentage": pct,
                    "health_status": health,
                    "is_flexible": b.is_flexible,
                }
            )

        total_remaining_minor = total_budgeted_minor - total_spent_minor

        payload = {
            "currency": currency,
            "total_budgeted_minor": total_budgeted_minor,
            "total_budgeted": Money(total_budgeted_minor, currency, minor_unit).serialize(),
            "total_spent_minor": total_spent_minor,
            "total_spent": Money(total_spent_minor, currency, minor_unit).serialize(),
            "total_remaining_minor": total_remaining_minor,
            "total_remaining": Money(total_remaining_minor, currency, minor_unit).serialize(),
            "budgets": overview_items,
        }

        return Response(payload, status=status.HTTP_200_OK)
