"""Views for Savings Goals and Contributions API."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.permissions import IsWorkspaceMember
from apps.savings.api.serializers import (
    CreateSavingsGoalSerializer,
    RecordContributionSerializer,
    SavingsContributionSerializer,
    SavingsGoalSerializer,
    SavingsProjectionSerializer,
)
from apps.savings.models import SavingsContribution, SavingsGoal
from apps.savings.selectors import get_goal_projection
from apps.savings.services import (
    AllocationCapacityError,
    GoalArchivedError,
    SavingsError,
    archive_savings_goal,
    create_savings_goal,
    record_savings_contribution,
    restore_savings_goal,
    update_savings_goal,
)
from apps.transactions.models import Transaction


class SavingsGoalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing savings goals, earmarks, contributions, and projections."""

    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    serializer_class = SavingsGoalSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[SavingsGoal]:
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return SavingsGoal.objects.none()

        qs = (
            SavingsGoal.objects.filter(workspace=ws)
            .select_related("linked_account")
            .prefetch_related("allocations__account")
        )

        qp = self.request.query_params
        include_archived = qp.get("include_archived", "false").lower() == "true"
        if not include_archived and self.action not in ("retrieve", "restore", "archive"):
            qs = qs.filter(is_archived=False)

        return qs

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        ws = request.user.workspace
        serializer = CreateSavingsGoalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            goal = create_savings_goal(
                workspace=ws,
                actor=request.user,
                name=data["name"],
                target_amount=data["target_amount"],
                currency=data["currency"],
                target_date=data.get("target_date"),
                linked_account_id=str(data["linked_account_id"])
                if data.get("linked_account_id")
                else None,
                strategy=data.get("strategy", "linked_account"),
                notes=data.get("notes"),
            )
        except SavingsError as exc:
            raise ValidationError(str(exc)) from exc

        output = SavingsGoalSerializer(goal, context={"request": request})
        return Response(output.data, status=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        goal = self.get_object()
        data = request.data
        try:
            updated = update_savings_goal(
                goal=goal,
                actor=request.user,
                name=data.get("name"),
                target_amount=data.get("target_amount"),
                target_date=data.get("target_date"),
                notes=data.get("notes"),
                status=data.get("status"),
            )
        except SavingsError as exc:
            raise ValidationError(str(exc)) from exc

        output = SavingsGoalSerializer(updated, context={"request": request})
        return Response(output.data)

    def destroy(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        goal = self.get_object()
        if goal.contributions.exists():
            raise ValidationError(
                "Cannot delete goal with existing contributions. Archive it instead."
            )
        goal.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: str | None = None) -> Response:
        goal = self.get_object()
        archived = archive_savings_goal(goal=goal, actor=request.user)
        output = SavingsGoalSerializer(archived, context={"request": request})
        return Response(output.data)

    @action(detail=True, methods=["post"])
    def restore(self, request: Request, pk: str | None = None) -> Response:
        goal = self.get_object()
        restored = restore_savings_goal(goal=goal, actor=request.user)
        output = SavingsGoalSerializer(restored, context={"request": request})
        return Response(output.data)

    @action(detail=True, methods=["get", "post"])
    def contributions(self, request: Request, pk: str | None = None) -> Response:
        goal = self.get_object()
        ws = request.user.workspace

        if request.method == "GET":
            contributions = (
                SavingsContribution.objects.filter(goal=goal, workspace=ws)
                .select_related("account", "goal")
                .order_by("-occurred_on", "-created_at")
            )
            serializer = SavingsContributionSerializer(contributions, many=True)
            return Response(serializer.data)

        # POST: Record contribution
        serializer = RecordContributionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        transfer_tx = None
        if data.get("transfer_transaction_id"):
            try:
                transfer_tx = Transaction.objects.get(
                    id=data["transfer_transaction_id"],
                    workspace=ws,
                )
            except Transaction.DoesNotExist as exc:
                raise ValidationError("Transfer transaction not found.") from exc

        try:
            contrib = record_savings_contribution(
                workspace=ws,
                actor=request.user,
                goal=goal,
                kind=data["kind"],
                amount=data["amount"],
                account_id=str(data["account_id"]),
                transfer_transaction=transfer_tx,
                occurred_on=data.get("occurred_on"),
                note=data.get("note"),
            )
        except (AllocationCapacityError, GoalArchivedError, SavingsError) as exc:
            raise ValidationError(str(exc)) from exc

        output = SavingsContributionSerializer(contrib)
        return Response(output.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"])
    def projection(self, request: Request, pk: str | None = None) -> Response:
        goal = self.get_object()
        projection = get_goal_projection(goal)
        serializer = SavingsProjectionSerializer(projection)
        return Response(serializer.data)
