from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import BaseThrottle
from rest_framework.views import APIView

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.users.permissions import EsCuentaConPanel

from . import servicios
from .models import AceptacionLegal


def _estado(usuario) -> dict:
    ac = servicios.aceptacion_vigente(usuario)
    return {
        "version": servicios.version_vigente(),
        "pendiente": ac is None,
        "aceptado_en": ac.aceptado_en if ac else None,
        "documentos": [{"id": d.value, "titulo": d.label, "ruta": servicios.RUTAS[d]} for d in servicios.DOCUMENTOS],
    }


@extend_schema(tags=["legal"], auth=[])
class VersionView(APIView):
    """Versión vigente de los documentos legales (pública: la leen las páginas y el cuadro de aceptación)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({"version": servicios.version_vigente()})


@extend_schema(tags=["legal"])
class EstadoView(APIView):
    """Si la persona ya aceptó la versión vigente y cuándo."""
    permission_classes = [EsCuentaConPanel]

    def get(self, request):
        return Response(_estado(request.user))


class AceptarSerializer(serializers.Serializer):
    version = serializers.CharField(max_length=20)


@extend_schema(tags=["legal"], request=AceptarSerializer)
class AceptarView(APIView):
    """
    Registra que la persona aceptó los Términos y la Política de Privacidad. Debe enviar la versión que tenía
    en pantalla: si los documentos cambiaron mientras tanto (409), tiene que volver a leerlos.
    """
    permission_classes = [EsCuentaConPanel]

    def post(self, request):
        s = AceptarSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        if s.validated_data["version"] != servicios.version_vigente():
            return Response({"detail": "Los documentos cambiaron. Recarga la página y léelos de nuevo antes de aceptar.",
                             "version": servicios.version_vigente()}, status=status.HTTP_409_CONFLICT)
        ip = BaseThrottle().get_ident(request)
        creada, _ = servicios.aceptar(request.user, ip=ip, agente=request.META.get("HTTP_USER_AGENT", ""))
        if creada:
            registrar(Bitacora.Accion.ACEPTAR_LEGAL, request=request, modulo="legal", objeto_id=request.user.pk,
                      descripcion="Aceptó los Términos y la Política de Privacidad.",
                      detalle={"version": servicios.version_vigente()})
        return Response(_estado(request.user), status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK)


class HistorialSerializer(serializers.ModelSerializer):
    documento_nombre = serializers.CharField(source="get_documento_display", read_only=True)

    class Meta:
        model = AceptacionLegal
        fields = ["documento", "documento_nombre", "version", "aceptado_en"]


@extend_schema(tags=["legal"], responses=HistorialSerializer(many=True))
class HistorialView(APIView):
    """Mis aceptaciones (transparencia: la persona puede ver qué aceptó y cuándo)."""
    permission_classes = [EsCuentaConPanel]

    def get(self, request):
        filas = AceptacionLegal.objects.filter(usuario=request.user)
        return Response(HistorialSerializer(filas, many=True).data)
