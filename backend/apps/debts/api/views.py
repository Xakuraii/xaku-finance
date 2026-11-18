"""Views for Liabilities, Repayments, and Projections API."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.permissions import IsWorkspaceMember
from apps.debts.api.serializers import (
    CreateDebtInterestRecordSerializer,
    CreateDebtRepaymentSerializer,
    CreateLiabilitySerializer,
    DebtInterestRecordSerializer,
    DebtProjectionSerializer,
    DebtRepaymentSerializer,
    LiabilitySerializer,
)
from apps.debts.models import DebtInterestRecord, DebtRepayment, Liability
from apps.debts.selectors import get_debt_payoff_projection
from apps.debts.services import (
    DebtError,
    LiabilityArchivedError,
    OverpaymentError,
    archive_liability,
    create_liability,
    record_accrued_interest,
    record_debt_repayment,
    restore_liability,
)


class LiabilityViewSet(viewsets.ModelViewSet):
    """ViewSet for managing liabilities, repayments, accrued interest, and payoff projections."""

    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    serializer_class = LiabilitySerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Liability]:
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return Liability.objects.none()

        qs = Liability.objects.filter(workspace=ws).select_related(
            "linked_account", "ledger_account"
        )

        qp = self.request.query_params
        include_archived = qp.get("include_archived", "false").lower() == "true"
        if not include_archived and self.action not in ("retrieve", "restore", "archive"):
            qs = qs.filter(is_archived=False)

        return qs

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = request.user.workspace
        serializer = CreateLiabilitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            liability = create_liability(
                workspace=ws,
                actor=request.user,
                name=data["name"],
                original_principal=data["original_principal"],
                currency=data["currency"],
                liability_type=data.get("liability_type", "personal_loan"),
                interest_rate=data.get("interest_rate"),
                interest_type=data.get("interest_type", "none"),
                lender=data.get("lender"),
                due_day=data.get("due_day"),
                next_due_date=data.get("next_due_date"),
                linked_account_id=str(data["linked_account_id"])
                if data.get("linked_account_id")
                else None,
                initial_disbursement_account_id=str(data["initial_disbursement_account_id"])
                if data.get("initial_disbursement_account_id")
                else None,
                disbursement_date=data.get("disbursement_date"),
                notes=data.get("notes"),
            )
        except DebtError as exc:
            raise ValidationError(str(exc)) from exc

        output = LiabilitySerializer(liability, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        liability = self.get_object()
        data = request.data

        if "name" in data:
            liability.name = str(data["name"]).strip()
        if "lender" in data:
            liability.lender = str(data["lender"]).strip() if data["lender"] else None
        if "due_day" in data:
            liability.due_day = int(data["due_day"]) if data["due_day"] is not None else None
        if "next_due_date" in data:
            liability.next_due_date = data["next_due_date"]
        if "notes" in data:
            liability.notes = data["notes"]
        if "status" in data:
            liability.status = data["status"]

        liability.save()
        output = LiabilitySerializer(liability, context={"request": request})
        return Response(output.data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        liability = self.get_object()
        if liability.repayments.exists() or liability.interest_records.exists():
            raise ValidationError(
                "Cannot delete liability with recorded repayments or interest. Archive it instead."
            )
        liability.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: str | None = None) -> Response:
        liability = self.get_object()
        archived = archive_liability(liability=liability, actor=request.user)
        output = LiabilitySerializer(archived, context={"request": request})
        return Response(output.data)

    @action(detail=True, methods=["post"])
    def restore(self, request: Request, pk: str | None = None) -> Response:
        liability = self.get_object()
        restored = restore_liability(liability=liability, actor=request.user)
        output = LiabilitySerializer(restored, context={"request": request})
        return Response(output.data)

    @action(detail=True, methods=["get", "post"])
    def repayments(self, request: Request, pk: str | None = None) -> Response:
        liability = self.get_object()
        ws = request.user.workspace

        if request.method == "GET":
            repayments = (
                DebtRepayment.objects.filter(liability=liability, workspace=ws)
                .select_related("liability", "transaction")
                .order_by("-paid_on", "-created_at")
            )
            serializer = DebtRepaymentSerializer(repayments, many=True)
            return Response(serializer.data)

        # POST: Record split repayment
        serializer = CreateDebtRepaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            repayment = record_debt_repayment(
                workspace=ws,
                actor=request.user,
                liability=liability,
                paying_account_id=str(data["paying_account_id"]),
                principal_amount=data.get("principal_amount", "0.00"),
                interest_amount=data.get("interest_amount", "0.00"),
                fee_amount=data.get("fee_amount", "0.00"),
                paid_on=data.get("paid_on"),
                note=data.get("note"),
            )
        except (OverpaymentError, LiabilityArchivedError, DebtError) as exc:
            raise ValidationError(str(exc)) from exc

        output = DebtRepaymentSerializer(repayment)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "post"])
    def interest(self, request: Request, pk: str | None = None) -> Response:
        liability = self.get_object()
        ws = request.user.workspace

        if request.method == "GET":
            records = (
                DebtInterestRecord.objects.filter(liability=liability, workspace=ws)
                .select_related("liability")
                .order_by("-period_end", "-created_at")
            )
            serializer = DebtInterestRecordSerializer(records, many=True)
            return Response(serializer.data)

        # POST: Record accrued interest
        serializer = CreateDebtInterestRecordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            record = record_accrued_interest(
                workspace=ws,
                actor=request.user,
                liability=liability,
                amount=data["amount"],
                period_start=data["period_start"],
                period_end=data["period_end"],
                rate_used=data.get("rate_used"),
                note=data.get("note"),
            )
        except (LiabilityArchivedError, DebtError) as exc:
            raise ValidationError(str(exc)) from exc

        output = DebtInterestRecordSerializer(record)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def projection(self, request: Request, pk: str | None = None) -> Response:
        liability = self.get_object()
        monthly_payment = request.query_params.get("monthly_payment")
        projection = get_debt_payoff_projection(liability, monthly_payment=monthly_payment)
        serializer = DebtProjectionSerializer(projection)
        return Response(serializer.data)
