"""Refresh-cookie helpers. The only cookie the API sets."""

from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse

REFRESH_COOKIE = "refresh"
COOKIE_PATH = "/api/v1/auth/"


def set_refresh_cookie(response: HttpResponse, raw_refresh: str, max_age: int) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        raw_refresh,
        max_age=max_age,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=COOKIE_PATH,
    )


def clear_refresh_cookie(response: HttpResponse) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=COOKIE_PATH, samesite="Lax")
