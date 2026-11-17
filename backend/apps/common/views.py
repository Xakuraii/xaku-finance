"""Health and readiness endpoints."""

from __future__ import annotations

from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


@extend_schema(
    responses={200: {"type": "object", "properties": {"status": {"type": "string"}}}},
    tags=["health"],
    auth=[],
)
@api_view(["GET"])
@permission_classes([AllowAny])
def health_live(request: Request) -> Response:
    return Response({"status": "ok"})


@extend_schema(responses={200: dict, 503: dict}, tags=["health"], auth=[])
@api_view(["GET"])
@permission_classes([AllowAny])
def health_ready(request: Request) -> Response:
    checks: dict[str, str] = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:  # pragma: no cover - only hit on infrastructure failure
        checks["database"] = "unavailable"
        return Response({"status": "degraded", "checks": checks}, status=503)
    return Response({"status": "ok", "checks": checks})
