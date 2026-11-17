"""Shared domain errors mapped to stable API codes."""

from __future__ import annotations

from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    """Base class for business-rule failures that are not programmer errors."""

    code = "domain_error"
    status_code = 422

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.field = field
        self.details = details or {}


def exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    request = context.get("request")
    request_id = getattr(request, "request_id", "") if request else ""

    if isinstance(exc, DomainError):
        return Response(
            {
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "field": exc.field,
                    "details": exc.details,
                },
                "request_id": request_id,
            },
            status=exc.status_code,
        )

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    data = response.data
    code = "validation_error" if response.status_code == 400 else "request_failed"
    message = "The request could not be completed."
    field = None
    details: dict[str, Any] = {}

    if isinstance(data, dict):
        if "detail" in data:
            message = str(data["detail"])
            code = getattr(data["detail"], "code", code)
        elif data:
            code = "validation_error"
            field = next(iter(data))
            first = data[field]
            if isinstance(first, list) and first:
                message = str(first[0])
            else:
                message = str(first)
            details = {k: v for k, v in data.items() if k != "detail"}
    elif isinstance(data, list):
        details = {"errors": data}

    response.data = {
        "error": {"code": code, "message": message, "field": field, "details": details},
        "request_id": request_id,
    }
    return response
