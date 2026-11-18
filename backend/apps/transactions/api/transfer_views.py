"""Views and ViewSet for internal Transfer resources."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.idempotency import idempotent_mutation
from apps.common.pagination import XakuCursorPagination
from apps.common.permissions import IsWorkspaceMember
from apps.transactions.api.transfer_serializers import (
    ArchiveTransferSerializer,
    CreateTransferSerializer,
    TransferSerializer,
)
from apps.transactions.models import Transfer
from apps.transactions.services.transfer import archive_transfer, create_transfer


class TransferPagination(XakuCursorPagination):
    ordering = "-created_at"


class TransferViewSet(viewsets.ModelViewSet):
    """ViewSet for managing internal account transfers."""

    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    serializer_class = TransferSerializer
    pagination_class = TransferPagination
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self) -> QuerySet[Transfer]:
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return Transfer.objects.none()

        qs = Transfer.objects.filter(workspace=ws).select_related(
            "transaction",
            "source_account",
            "source_account__currency",
            "destination_account",
            "destination_account__currency",
            "transfer_fee_category",
            "conversion_fee_category",
        )

        include_archived = (
            self.request.query_params.get("include_archived", "false").lower() == "true"
        )
        if self.action != "retrieve" and not include_archived:
            qs = qs.filter(transaction__is_archived=False)

        return qs

    @idempotent_mutation
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = CreateTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        tx, transfer_obj = create_transfer(
            workspace=request.user.workspace,
            actor=request.user,
            source_account_id=vd["source_account_id"],
            destination_account_id=vd["destination_account_id"],
            amount=vd["amount"],
            destination_amount=vd.get("destination_amount"),
            rate=vd.get("rate"),
            reference_rate=vd.get("reference_rate"),
            transfer_fee=vd.get("transfer_fee", "0.00"),
            transfer_fee_category_id=vd.get("transfer_fee_category_id"),
            conversion_fee_category_id=vd.get("conversion_fee_category_id"),
            occurred_on=vd["occurred_on"],
            notes=vd.get("notes", ""),
        )

        return Response(TransferSerializer(transfer_obj).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: Any = None) -> Response:
        serializer = ArchiveTransferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        tx = archive_transfer(
            transfer_id=pk,
            actor=request.user,
            reason=reason,
        )

        return Response(
            {
                "id": str(tx.id),
                "is_archived": tx.is_archived,
                "archived_at": tx.archived_at,
            },
            status=status.HTTP_200_OK,
        )
