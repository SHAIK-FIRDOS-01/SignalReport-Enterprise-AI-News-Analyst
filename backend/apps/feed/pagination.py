"""
Custom PageNumberPagination conforming to Frontend and FastAPI JSON contracts.
Replaces: FastAPI FeedResponse pagination schemas
Ponytail: Extends DRF's PageNumberPagination with zero external dependencies.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardFeedPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        # Support 'limit' query parameter as alias for 'page_size'
        if "limit" in request.query_params and "page_size" not in request.query_params:
            try:
                limit_val = int(request.query_params["limit"])
                self.page_size = min(max(1, limit_val), self.max_page_size)
            except (ValueError, TypeError):
                pass

        # Support 'cursor' query parameter as alias for 'page'
        if "cursor" in request.query_params and "page" not in request.query_params:
            cursor_val = request.query_params.get("cursor")
            if cursor_val and cursor_val.isdigit():
                self.page_query_param = "cursor"
            else:
                self.page_query_param = "page"
        else:
            self.page_query_param = "page"

        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        total = self.page.paginator.count
        total_pages = self.page.paginator.num_pages
        page = self.page.number
        has_more = self.page.has_next()
        next_cursor = self.page.next_page_number() if has_more else None

        return Response({
            "items": data,
            "total": total,
            "page": page,
            "page_size": self.get_page_size(self.request),
            "total_pages": total_pages,
            "has_more": has_more,
            "next_cursor": next_cursor,
        })
