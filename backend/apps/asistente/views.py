"""
apps/asistente/views.py
F6-06 — Reportes por voz: transcribir (audio → texto), interpretar (texto → orden) y ejecutar (orden confirmada).
Solo administración y organización; cada uso queda en la bitácora; el asistente es de solo lectura.
"""
from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.views import APIView

from apps.asistente.serializers import EjecutarSerializer, InterpretarSerializer
from apps.asistente.services import llm
from apps.asistente.services.ejecutar import ejecutar
from apps.asistente.services.interprete import interpretar
from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.users.permissions import EsAdminUOrganizador

TIPOS_AUDIO = ("audio/", "video/webm", "application/octet-stream")


class AsistenteThrottle(UserRateThrottle):
    """El LLM y Whisper tienen costo o cupo: se limita el uso por persona."""
    scope = "asistente"

    def get_rate(self):
        return "30/min"


class Base(APIView):
    permission_classes = [EsAdminUOrganizador]
    throttle_classes = [AsistenteThrottle]


@extend_schema(tags=["asistente"])
class EstadoAsistenteView(Base):
    """Qué capacidades están activas (para que la interfaz sea honesta: voz, LLM o solo reglas)."""

    def get(self, request):
        return Response({"voz": llm.stt_configurado(), "llm": llm.llm_configurado(),
                         "proveedor_llm": settings.LLM_PROVIDER if llm.llm_configurado() else "reglas"})


@extend_schema(tags=["asistente"])
class TranscribirView(Base):
    parser_classes = [MultiPartParser]

    @extend_schema(summary="F6-06 — Transcribir una grabación de voz a texto")
    def post(self, request):
        audio = request.FILES.get("audio")
        if audio is None:
            return Response({"detail": "Falta el archivo de audio (campo «audio»)."}, status=status.HTTP_400_BAD_REQUEST)
        if audio.size == 0 or audio.size > settings.ASISTENTE_AUDIO_MAX_MB * 1024 * 1024:
            return Response({"detail": f"El audio debe pesar entre 1 byte y {settings.ASISTENTE_AUDIO_MAX_MB} MB."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not (audio.content_type or "").startswith(TIPOS_AUDIO):
            return Response({"detail": "El archivo debe ser un audio."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            texto = llm.transcribir_audio(audio.read(), audio.name or "orden.webm", audio.content_type or "audio/webm")
        except llm.SttNoConfigurado as e:
            return Response({"detail": str(e), "configurado": False}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except llm.SttFallo as e:
            return Response({"detail": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        if not texto:
            return Response({"detail": "No se escuchó nada. Intenta hablar más cerca del micrófono."},
                            status=status.HTTP_422_UNPROCESSABLE_ENTITY)
        registrar(Bitacora.Accion.ML_PRED, request=request, modulo="asistente", descripcion="Audio transcrito.",
                  detalle={"caracteres": len(texto), "proveedor": settings.STT_PROVIDER})
        return Response({"texto": texto, "proveedor": settings.STT_PROVIDER})


@extend_schema(tags=["asistente"])
class InterpretarView(Base):
    @extend_schema(summary="F6-06 — Interpretar una orden en texto (no ejecuta nada)", request=InterpretarSerializer)
    def post(self, request):
        s = InterpretarSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        r = interpretar(d["texto"], d.get("previo"), d.get("seleccion"))
        registrar(Bitacora.Accion.ML_PRED, request=request, modulo="asistente", descripcion="Orden interpretada.",
                  detalle={"texto": d["texto"][:200], "estado": r.estado, "intencion": r.intencion, "proveedor": r.proveedor},
                  resultado=Bitacora.Resultado.OK if r.estado != "no_entendido" else Bitacora.Resultado.ERROR)
        return Response(r.como_dict())


@extend_schema(tags=["asistente"])
class EjecutarView(Base):
    @extend_schema(summary="F6-06 — Ejecutar una orden confirmada (solo lectura)", request=EjecutarSerializer)
    def post(self, request):
        s = EjecutarSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        resultado = ejecutar(d["intencion"], formato=d.get("formato"), campeonato=d.get("campeonato"),
                             equipo=d.get("equipo"), jugador=d.get("jugador"))
        registrar(Bitacora.Accion.EXPORTAR if resultado["tipo"] == "descarga" else Bitacora.Accion.ML_PRED,
                  request=request, modulo="asistente", descripcion="Orden del asistente ejecutada.",
                  detalle={"intencion": d["intencion"], "formato": d.get("formato"), "resultado": resultado["tipo"]})
        return Response(resultado)
