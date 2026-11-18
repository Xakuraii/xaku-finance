"""Views and ViewSet for Account resources."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models import QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.api.serializers import (
    AccountArchiveSerializer,
    AccountCreateSerializer,
    AccountOpeningBalanceSerializer,
    AccountSerializer,
    AccountUpdateSerializer,
)
from apps.accounts.models import Account
from apps.accounts.services import (
    archive_account,
    change_currency,
    create_account,
    restore_account,
)
from apps.common.idempotency import idempotent_mutation
from apps.common.permissions import IsWorkspaceMember
from apps.transactions.services.opening import create_opening_balance


class AccountViewSet(viewsets.ModelViewSet):
    """ViewSet for managing user financial accounts."""

    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    serializer_class = AccountSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Account]:
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return Account.objects.none()

        qs = Account.objects.filter(workspace=ws)
        include_archived = (
            self.request.query_params.get("include_archived", "false").lower() == "true"
        )
        if self.action not in ("restore", "retrieve") and not include_archived:
            qs = qs.filter(is_archived=False)
        return qs.order_by("display_order", "name")

    @idempotent_mutation
    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = AccountCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        account = create_account(
            workspace=request.user.workspace,
            actor=request.user,
            name=vd["name"],
            account_type=vd["account_type"],
            currency=vd["currency"],
            opening_balance=vd.get("opening_balance"),
            opening_balance_date=vd.get("opening_balance_date"),
            is_spendable=vd.get("is_spendable"),
            description=vd.get("description", ""),
            allows_negative_balance=vd.get("allows_negative_balance", False),
            opened_on=vd.get("opened_on"),
        )

        return Response(AccountSerializer(account).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        account = self.get_object()
        serializer = AccountUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        if "currency" in vd and vd["currency"] != account.currency_id:
            account = change_currency(
                workspace=request.user.workspace,
                actor=request.user,
                account_id=account.id,
                currency=vd["currency"],
            )

        update_fields = []
        for field in (
            "name",
            "description",
            "is_spendable",
            "allows_negative_balance",
            "display_order",
        ):
            if field in vd:
                setattr(account, field, vd[field])
                update_fields.append(field)

        if update_fields:
            update_fields.append("updated_at")
            account.save(update_fields=update_fields)

        return Response(AccountSerializer(account).data)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: str | None = None) -> Response:
        account = self.get_object()
        serializer = AccountArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        archived = archive_account(
            workspace=request.user.workspace,
            actor=request.user,
            account_id=account.id,
            reason=vd["reason"],
            acknowledge_balance=vd.get("acknowledge_balance", False),
        )
        return Response(AccountSerializer(archived).data)

    @action(detail=True, methods=["post"])
    def restore(self, request: Request, pk: str | None = None) -> Response:
        account = self.get_object()
        restored = restore_account(
            workspace=request.user.workspace,
            actor=request.user,
            account_id=account.id,
        )
        return Response(AccountSerializer(restored).data)

    @action(detail=True, methods=["post"], url_path="opening-balance")
    @idempotent_mutation
    def opening_balance(self, request: Request, pk: str | None = None) -> Response:
        account = self.get_object()
        serializer = AccountOpeningBalanceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        tx = create_opening_balance(
            workspace=request.user.workspace,
            actor=request.user,
            account=account,
            amount=vd["amount"],
            as_of=vd.get("as_of") or date.today(),
        )

        return Response(
            {
                "id": str(tx.id),
                "account_id": str(account.id),
                "amount": vd["amount"],
                "amount_minor": tx.amount_minor,
                "currency": account.currency_id,
                "occurred_on": str(tx.occurred_on),
                "title": tx.title,
            },
            status=status.HTTP_201_CREATED,
        )
