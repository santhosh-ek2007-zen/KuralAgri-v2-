from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardPagination(PageNumberPagination):
    """
    Standard pagination for KuralAgri APIs.
    Default 20 items per page, capped at 100.
    Includes metadata: count, total_pages, current_page, next, previous.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
