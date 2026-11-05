from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.filters import SearchFilter

from apps.users.permissions import EsAdmin

from .models import Bitacora
from .serializers import BitacoraSerializer


@extend_schema(tags=["auditoria"])
class BitacoraListView(generics.ListAPIView):
    serializer_class = BitacoraSerializer
    permission_classes = [EsAdmin]
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = {
        "usuario": ["exact"],
        "accion": ["exact"],
        "modulo": ["exact"],
        "resultado": ["exact"],
        "fecha_hora": ["gte", "lte"],
    }
    search_fields = ["descripcion", "usuario_email"]

    def get_queryset(self):
        return Bitacora.objects.select_related("usuario").order_by("-fecha_hora")
