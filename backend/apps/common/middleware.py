"""Request id middleware and shared request context."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"


class RequestIdMiddleware:
    """Attach a request id to every request and echo it in the response."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = request.META.get(REQUEST_ID_HEADER, "")
        request.request_id = incoming[:64] if incoming else f"req_{uuid.uuid4().hex}"
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        response["X-API-Version"] = "1"
        return response
