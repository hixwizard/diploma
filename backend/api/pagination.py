from rest_framework.pagination import PageNumberPagination

from core.constans import PAGE_SIZE


class CustomPagination(PageNumberPagination):
    """
    Пагинация с параметром.
    """
    page_size = PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = PAGE_SIZE
