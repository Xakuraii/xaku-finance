"""Idempotency-Key support for financial mutation endpoints."""

from __future__ import annotations

import functools
import hashlib
from collections.abc import Callable
from typing import Any

from django.core.cache import cache
from rest_framework.request import Request
from rest_framework.response import Response


class IdempotencyConflict(ValueError):
    """Raised when an Idempotency-Key is reused with a different request payload."""


def get_idempotency_key(request: Request) -> str | None:
    """Extract Idempotency-Key header from request."""
    return request.headers.get("Idempotency-Key") or request.META.get("HTTP_IDEMPOTENCY_KEY")


def idempotent_mutation(view_func: Callable[..., Response]) -> Callable[..., Response]:
    """Decorator for DRF API views to enforce idempotent POST requests."""

    @functools.wraps(view_func)
    def wrapper(view_instance: Any, request: Request, *args: Any, **kwargs: Any) -> Response:
        key = get_idempotency_key(request)
        if not key:
            return view_func(view_instance, request, *args, **kwargs)

        key = key.strip()
        user_id = str(getattr(request.user, "id", "anon"))
        cache_key = f"idempotency:{user_id}:{key}"

        body_bytes = getattr(request, "_body", None)
        if body_bytes is None:
            try:
                body_bytes = request.body
            except Exception:
                body_bytes = str(request.data).encode()

        body_hash = hashlib.sha256(body_bytes).hexdigest()

        cached_entry = cache.get(cache_key)
        if cached_entry is not None:
            if cached_entry["hash"] != body_hash:
                raise IdempotencyConflict(
                    "Idempotency key was previously used with a different request payload."
                )

            replay_response = Response(
                data=cached_entry["data"],
                status=cached_entry["status"],
            )
            replay_response["Idempotent-Replay"] = "true"
            return replay_response

        response = view_func(view_instance, request, *args, **kwargs)

        if 200 <= response.status_code < 300:
            cache.set(
                cache_key,
                {
                    "hash": body_hash,
                    "status": response.status_code,
                    "data": response.data,
                },
                timeout=86400,
            )

        return response

    return wrapper
