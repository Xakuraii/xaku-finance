"""Cursor pagination with opaque cursor tokens for XakuFinance API."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class XakuCursorPagination(CursorPagination):
    """Cursor-based pagination producing {results, next_cursor, has_more}."""

    page_size = 25
    page_size_query_param = "limit"
    max_page_size = 200
    cursor_query_param = "cursor"
    ordering = "-created_at"

    def get_paginated_response(self, data: list) -> Response:
        next_link = self.get_next_link()
        next_token: str | None = None
        if next_link:
            parsed = parse_qs(urlparse(next_link).query)
            token_list = parsed.get("cursor", [])
            if token_list:
                next_token = token_list[0]

        return Response(
            {
                "results": data,
                "next_cursor": next_token,
                "has_more": bool(next_token),
            }
        )
