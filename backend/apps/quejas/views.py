from django.utils import timezone
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.users.permissions import (
    EsAdmin,
    EsAdminUOrganizador,
    EsAdminUOrganizadorODelegado,
    EsDelegado,
)
from apps.users.roles import es_delegado
from .models import Queja
from .serializers import QuejaSerializer


@extend_schema(tags=["quejas"])
class MisQuejasView(generics.ListAPIView):
    """Quejas presentadas por el delegado autenticado."""
    serializer_class = QuejaSerializer
    permission_classes = [EsDelegado]
    queryset = Queja.objects.select_related(
        "delegado", "admin_resuelve", "encuentro__equipo_local", "encuentro__equipo_visitante", "encuentro__campeonato"
    )

    def get_queryset(self):
        return super().get_queryset().filter(delegado=self.request.user)


@extend_schema(tags=["quejas"])
class QuejaViewSet(viewsets.ModelViewSet):
    queryset = Queja.objects.select_related(
        "delegado", "admin_resuelve", "encuentro__equipo_local", "encuentro__equipo_visitante", "encuentro__campeonato"
    )
    serializer_class = QuejaSerializer
    filterset_fields = ["tipo", "estado", "encuentro"]
    search_fields = ["descripcion", "resolucion"]

    def get_permissions(self):
        if self.action == "create":
            return [EsDelegado()]
        if self.action in ("update", "partial_update", "destroy"):
            return [EsAdmin()]
        if self.action == "resolver":
            return [EsAdminUOrganizador()]
        return [EsAdminUOrganizadorODelegado()]

    def get_queryset(self):
        queryset = super().get_queryset()
        if es_delegado(self.request.user):
            return queryset.filter(delegado=self.request.user)
        return queryset

    def perform_create(self, serializer):
        queja = serializer.save()
        registrar(
            Bitacora.Accion.CREAR,
            request=self.request,
            modulo="queja",
            objeto_id=queja.pk,
            descripcion="Queja o apelación presentada.",
        )

    def perform_update(self, serializer):
        queja = serializer.save()
        if queja.estado in (Queja.Estado.RESUELTA, Queja.Estado.RECHAZADA):
            queja.admin_resuelve = self.request.user
            queja.resuelta_en = timezone.now()
            queja.save(update_fields=["admin_resuelve", "resuelta_en"])
        registrar(
            Bitacora.Accion.EDITAR,
            request=self.request,
            modulo="queja",
            objeto_id=queja.pk,
            descripcion="Queja o apelación actualizada.",
        )

    def perform_destroy(self, instance):
        registrar(
            Bitacora.Accion.ELIMINAR,
            request=self.request,
            modulo="queja",
            objeto_id=instance.pk,
            descripcion="Queja o apelación eliminada.",
        )
        instance.delete()

    @action(detail=True, methods=["post"])
    def resolver(self, request, pk=None):
        queja = self.get_object()
        estado = request.data.get("estado")
        resolucion = request.data.get("resolucion", "").strip()
        if estado not in (
            Queja.Estado.EN_REVISION,
            Queja.Estado.RESUELTA,
            Queja.Estado.RECHAZADA,
        ):
            raise ValidationError(
                {"estado": "El estado debe ser EN_REVISION, RESUELTA o RECHAZADA."}
            )
        if estado in (Queja.Estado.RESUELTA, Queja.Estado.RECHAZADA) and not resolucion:
            raise ValidationError(
                {"resolucion": "La resolución es obligatoria para cerrar una queja."}
            )
        queja.estado = estado
        queja.resolucion = resolucion or None
        if estado in (Queja.Estado.RESUELTA, Queja.Estado.RECHAZADA):
            queja.admin_resuelve = request.user
            queja.resuelta_en = timezone.now()
        queja.save(
            update_fields=[
                "estado",
                "resolucion",
                "admin_resuelve",
                "resuelta_en",
            ]
        )
        registrar(
            Bitacora.Accion.EDITAR,
            request=request,
            modulo="queja",
            objeto_id=queja.pk,
            descripcion="Queja o apelación resuelta.",
            detalle={"estado": estado},
        )
        return Response(QuejaSerializer(queja).data)
