"""ViewSet for Category resources."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.categories.api.serializers import (
    CategoryArchiveSerializer,
    CategoryCreateSerializer,
    CategorySerializer,
)
from apps.categories.models import Category
from apps.categories.services import archive_category, create_category
from apps.common.permissions import IsWorkspaceMember


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for managing workspace income and expense categories."""

    permission_classes = [permissions.IsAuthenticated, IsWorkspaceMember]
    serializer_class = CategorySerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self) -> QuerySet[Category]:
        ws = getattr(self.request.user, "workspace", None)
        if not ws:
            return Category.objects.none()

        qs = Category.objects.filter(workspace=ws).prefetch_related("children")

        qp = self.request.query_params
        include_archived = qp.get("include_archived", "false").lower() == "true"
        if not include_archived and self.action != "retrieve":
            qs = qs.filter(is_archived=False)

        if "kind" in qp:
            qs = qs.filter(kind=qp["kind"])

        flat = qp.get("flat", "false").lower() == "true"
        if self.action == "list" and not flat:
            # Only top-level categories by default; children are nested
            qs = qs.filter(parent__isnull=True)

        return qs.order_by("sort_order", "name")

    def create(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        serializer = CategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data

        cat = create_category(
            workspace=request.user.workspace,
            name=vd["name"],
            kind=vd["kind"],
            parent_id=vd.get("parent_id"),
            icon=vd.get("icon"),
            color=vd.get("color"),
            sort_order=vd.get("sort_order", 0),
        )

        return Response(CategorySerializer(cat).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def archive(self, request: Request, pk: Any = None) -> Response:
        serializer = CategoryArchiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reassign_id = serializer.validated_data.get("reassign_to_category_id")

        cat = archive_category(
            workspace=request.user.workspace,
            category_id=pk,
            reassign_to_category_id=reassign_id,
        )

        return Response(CategorySerializer(cat).data, status=status.HTTP_200_OK)
