from rest_framework.pagination import PageNumberPagination


class PaginacionEstandar(PageNumberPagination):
    """20 por página; la interfaz puede pedir más con ?page_size= (máximo 200)."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200
