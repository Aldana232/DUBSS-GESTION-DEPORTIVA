from rest_framework.exceptions import Throttled


class ThrottledES(Throttled):
    extra_detail_singular = "Disponible en {wait} segundo."
    extra_detail_plural = "Disponible en {wait} segundos."
