"""Views for Tag resources and spending analytics."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.permissions import IsWorkspaceMember
from apps.tags.api.serializers import (
    TagAnalyticsResponseSerializer,
    TagSerializer,
)
from apps.tags.models import Tag
from apps.tags.services.analytics import get_spending_analytics


class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for managing workspace tags and viewing spending analytics."""

    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    serializer_class = TagSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Tag]:
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return Tag.objects.none()
        return Tag.objects.filter(workspace=ws).order_by("name")

    def perform_create(self, serializer: Any) -> None:
        serializer.save(workspace=self.request.user.workspace)

    @extend_schema(
        responses={200: TagAnalyticsResponseSerializer},
        description="Get spending analytics broken down by tags and necessity classification.",
    )
    @action(detail=False, methods=["get"])
    def analytics(self, request: Request) -> Response:
        ws = request.user.workspace
        qp = request.query_params

        start_date = qp.get("from")
        end_date = qp.get("to")
        currency = qp.get("currency")

        data = get_spending_analytics(
            workspace=ws,
            start_date=start_date,
            end_date=end_date,
            currency_code=currency,
        )

        serializer = TagAnalyticsResponseSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)
