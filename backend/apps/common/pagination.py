"""Cursor pagination for public galleries."""

from rest_framework.pagination import CursorPagination
from rest_framework.response import Response


class StandardCursorPagination(CursorPagination):
    """Cursor-paginated list responses: stable ordering, opaque cursor, page size 12."""

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 50
    ordering = "-created_at"
    cursor_query_param = "cursor"

    def get_paginated_response(self, data: list) -> Response:
        return Response(
            {
                "results": data,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            }
        )
