"""Views and ViewSet for Transaction resources."""

from __future__ import annotations

from typing import Any

from django.db.models import Q, QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.idempotency import idempotent_mutation
from apps.common.pagination import XakuCursorPagination
from apps.common.permissions import IsWorkspaceMember
from apps.transactions.api.serializers import (
    TransactionArchiveSerializer,
    TransactionAuditSerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
    TransactionUpdateSerializer,
)
from apps.transactions.models import Transaction, TransactionAudit
from apps.transactions.services.archive import archive_transaction, restore_transaction
from apps.transactions.services.create import SplitInput, create_transaction
from apps.transactions.services.update import update_transaction


class TransactionPagination(XakuCursorPagination):
    ordering = "-occurred_on"


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user financial transactions, splits, and audit history."""

    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    serializer_class = TransactionSerializer
    pagination_class = TransactionPagination
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Transaction]:
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return Transaction.objects.none()

        qs = (
            Transaction.objects.filter(workspace=ws)
            .select_related("account", "category", "currency")
            .prefetch_related("splits__category", "tagged_items__tag")
        )

        qp = self.request.query_params
        include_archived = qp.get("include_archived", "false").lower() == "true"
        if self.action not in ("restore", "retrieve") and not include_archived:
            qs = qs.filter(is_archived=False)

        if "account_id" in qp:
            qs = qs.filter(account_id=qp["account_id"])
        if "category_id" in qp:
            qs = qs.filter(
                Q(category_id=qp["category_id"]) | Q(splits__category_id=qp["category_id"])
            ).distinct()
        if "status" in qp:
            qs = qs.filter(status=qp["status"])
        if "necessity" in qp:
            qs = qs.filter(necessity=qp["necessity"])
        if "from" in qp:
            qs = qs.filter(occurred_on__gte=qp["from"])
        if "to" in qp:
            qs = qs.filter(occurred_on__lte=qp["to"])
        if "tag" in qp:
            qs = qs.filter(tagged_items__tag__name__iexact=qp["tag"])
        if "q" in qp:
            term = qp["q"].strip()
            qs = qs.filter(
                Q(title__icontains=term)
                | Q(merchant__icontains=term)
                | Q(description__icontains=term)
                | Q(notes__icontains=term)
            )

        return qs.order_by("-occurred_on", "-created_at")

    @idempotent_mutation
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = TransactionCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        splits_input = None
        if "splits" in vd:
            splits_input = [
                SplitInput(
                    category_id=sp["category_id"],
                    amount=sp["amount"],
                    memo=sp.get("memo", ""),
                )
                for sp in vd["splits"]
            ]

        tx = create_transaction(
            workspace=request.user.workspace,
            actor=request.user,
            kind=vd.get("type", "expense"),
            account_id=vd["account_id"],
            amount=vd["amount"],
            currency=vd["currency"],
            occurred_on=vd["occurred_on"],
            title=vd["title"],
            category_id=vd.get("category_id"),
            splits=splits_input,
            tags=vd.get("tags"),
            necessity=vd.get("necessity"),
            status=vd.get("status", "completed"),
            description=vd.get("description", ""),
            notes=vd.get("notes", ""),
            merchant=vd.get("merchant", ""),
        )

        return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        tx = self.get_object()
        serializer = TransactionUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        splits_input = None
        if "splits" in vd:
            splits_input = [
                SplitInput(
                    category_id=sp["category_id"],
                    amount=sp["amount"],
                    memo=sp.get("memo", ""),
                )
                for sp in vd["splits"]
            ]

        updated = update_transaction(
            workspace=request.user.workspace,
            actor=request.user,
            transaction_id=tx.id,
            expected_version=vd["expected_version"],
            reason=vd["reason"],
            amount=vd.get("amount"),
            title=vd.get("title"),
            occurred_on=vd.get("occurred_on"),
            category_id=vd.get("category_id"),
            splits=splits_input,
            necessity=vd.get("necessity"),
            description=vd.get("description"),
            notes=vd.get("notes"),
            merchant=vd.get("merchant"),
        )

        return Response(TransactionSerializer(updated).data)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: str | None = None) -> Response:
        tx = self.get_object()
        serializer = TransactionArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        archived = archive_transaction(
            workspace=request.user.workspace,
            actor=request.user,
            transaction_id=tx.id,
            reason=vd["reason"],
        )
        return Response(TransactionSerializer(archived).data)

    @action(detail=True, methods=["post"])
    def restore(self, request: Request, pk: str | None = None) -> Response:
        tx = self.get_object()
        restored = restore_transaction(
            workspace=request.user.workspace,
            actor=request.user,
            transaction_id=tx.id,
        )
        return Response(TransactionSerializer(restored).data)

    @action(detail=True, methods=["get"])
    def audit(self, request: Request, pk: str | None = None) -> Response:
        tx = self.get_object()
        audits = (
            TransactionAudit.objects.filter(transaction=tx)
            .select_related("actor")
            .order_by("revision")
        )
        return Response(TransactionAuditSerializer(audits, many=True).data)
