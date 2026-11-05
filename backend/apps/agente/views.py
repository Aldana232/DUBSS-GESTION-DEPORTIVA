"""
apps/agente/views.py
F7-01/F7-02 — API del agente: estado, conversaciones, mensajes y confirmación/cancelación de acciones pendientes.
Solo administración y organización; cada uso queda en la bitácora.
"""
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.agente.models import AccionPendiente, ConversacionAgente
from apps.agente.serializers import AccionSerializer, ConversacionSerializer, EntradaMensajeSerializer, MensajeSerializer
from apps.agente.services import acciones, herramientas, llm
from apps.agente.services.agente import LimiteExcedido, responder
from apps.agente.services.llm import AgenteNoDisponible
from apps.users.permissions import EsAdminUOrganizador

NO_EXISTE = {"detail": "No existe esa conversación."}


class AgenteThrottle(UserRateThrottle):
    """El LLM tiene costo y cupo: se limita el ritmo por persona (además del tope por hora)."""
    scope = "agente"

    def get_rate(self):
        return "20/min"


class Base(APIView):
    permission_classes = [EsAdminUOrganizador]
    throttle_classes = [AgenteThrottle]


@extend_schema(tags=["agente"])
class EstadoAgenteView(Base):
    @extend_schema(summary="F7-01 — Estado y herramientas del agente")
    def get(self, request):
        return Response({
            "disponible": llm.disponible(), "modelo": settings.AGENTE_MODEL if llm.disponible() else None,
            "limite_por_hora": settings.AGENTE_MENSAJES_HORA, "vigencia_minutos": settings.AGENTE_ACCION_MINUTOS,
            "herramientas": [{"nombre": h.nombre, "tipo": h.tipo, "etiqueta": h.etiqueta} for h in herramientas.REGISTRO.values()],
        })


@extend_schema(tags=["agente"])
class ConversacionesView(Base):
    @extend_schema(summary="Mis conversaciones con el agente (las 20 más recientes)")
    def get(self, request):
        qs = ConversacionAgente.objects.filter(usuario=request.user)[:20]
        return Response(ConversacionSerializer(qs, many=True).data)


@extend_schema(tags=["agente"])
class ConversacionDetalleView(Base):
    def _propia(self, request, pk):
        return ConversacionAgente.objects.filter(pk=pk, usuario=request.user).first()

    @extend_schema(summary="Mensajes de una conversación")
    def get(self, request, pk):
        c = self._propia(request, pk)
        if c is None:
            return Response(NO_EXISTE, status=status.HTTP_404_NOT_FOUND)
        return Response({**ConversacionSerializer(c).data,
                         "mensajes": MensajeSerializer(c.mensajes.prefetch_related("acciones"), many=True).data})

    @extend_schema(summary="Eliminar una conversación propia")
    def delete(self, request, pk):
        c = self._propia(request, pk)
        if c is None:
            return Response(NO_EXISTE, status=status.HTTP_404_NOT_FOUND)
        c.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["agente"])
class MensajeView(Base):
    @extend_schema(summary="F7-01 — Enviar un mensaje al agente", request=EntradaMensajeSerializer)
    def post(self, request):
        s = EntradaMensajeSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if s.validated_data.get("conversacion"):
            conversacion = ConversacionAgente.objects.filter(pk=s.validated_data["conversacion"], usuario=request.user).first()
            if conversacion is None:
                return Response(NO_EXISTE, status=status.HTTP_404_NOT_FOUND)
            nueva = False
        else:
            conversacion, nueva = ConversacionAgente.objects.create(usuario=request.user), True
        try:
            respuesta = responder(request.user, conversacion, s.validated_data["texto"])
        except (LimiteExcedido, AgenteNoDisponible) as e:
            if nueva:
                conversacion.delete()       # no deja conversaciones vacías si el primer mensaje falla
            codigo = status.HTTP_429_TOO_MANY_REQUESTS if isinstance(e, LimiteExcedido) else status.HTTP_503_SERVICE_UNAVAILABLE
            return Response({"detail": str(e)}, status=codigo)
        return Response({"conversacion": conversacion.pk, "respuesta": MensajeSerializer(respuesta).data})


def _resolver(request, pk, funcion):
    try:
        accion = funcion(pk, request.user)
    except acciones.AccionNoEjecutable as e:
        return Response({"detail": e.mensaje, **e.extra}, status=e.codigo)
    return Response(AccionSerializer(accion).data)


@extend_schema(tags=["agente"])
class ConfirmarAccionView(Base):
    @extend_schema(summary="F7-02 — Confirmar y ejecutar una acción pendiente")
    def post(self, request, pk):
        return _resolver(request, pk, acciones.confirmar)


@extend_schema(tags=["agente"])
class CancelarAccionView(Base):
    @extend_schema(summary="F7-02 — Cancelar una acción pendiente")
    def post(self, request, pk):
        return _resolver(request, pk, acciones.cancelar)


@extend_schema(tags=["agente"])
class AccionDetalleView(Base):
    @extend_schema(summary="Estado de una acción propia")
    def get(self, request, pk):
        a = AccionPendiente.objects.filter(pk=pk, usuario=request.user).first()
        if a is None:
            return Response({"detail": "No existe esa acción."}, status=status.HTTP_404_NOT_FOUND)
        return Response(AccionSerializer(a).data)
