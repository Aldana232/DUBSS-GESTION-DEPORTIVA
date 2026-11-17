from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.users.permissions import EsAdmin

from . import entrante, servicios
from .firma import verificar
from .models import EventoSaliente
from .telefono import normalizar_whatsapp

MAX_CUERPO = 4096
LIMITE_MENSAJES_MIN = 20


@extend_schema(tags=["integraciones"])
class EstadoView(APIView):
    """Estado de la integración con n8n/WhatsApp, para que la interfaz sea honesta sobre lo que realmente ocurre."""
    permission_classes = [EsAdmin]

    def get(self, request):
        ahora = timezone.now()
        E = EventoSaliente
        ultimos = E.objects.order_by("-creado")[:8]
        return Response({
            "configurado": servicios.configurado(),
            "destino": servicios.host_destino(),
            "pendientes": E.objects.filter(estado=E.Estado.PENDIENTE).count(),
            "entregados_24h": E.objects.filter(estado=E.Estado.ENTREGADO, creado__gte=ahora - timedelta(hours=24)).count(),
            "fallidos": E.objects.filter(estado=E.Estado.FALLIDO).count(),
            "usuarios_con_whatsapp": _contar_con_whatsapp(),
            "ultimos": [{"id": str(e.id), "tipo": e.tipo, "estado": e.estado, "intentos": e.intentos,
                         "error": e.ultimo_error, "creado": e.creado} for e in ultimos],
        })


def _contar_con_whatsapp() -> int:
    from apps.users.models import Usuario
    return Usuario.objects.filter(is_active=True, acepta_whatsapp=True).exclude(whatsapp="").count()


class PruebaSerializer(serializers.Serializer):
    mensaje = serializers.CharField(max_length=300, default="Mensaje de prueba de la DUBSS.")


@extend_schema(tags=["integraciones"], request=PruebaSerializer)
class PruebaView(APIView):
    """Envía un evento de prueba a n8n. Si quien lo pide activó WhatsApp, recibe también el mensaje."""
    permission_classes = [EsAdmin]

    def post(self, request):
        if not servicios.configurado():
            return Response({"detail": "La integración no está configurada (faltan N8N_URL_EVENTOS y N8N_SECRETO)."},
                            status=status.HTTP_400_BAD_REQUEST)
        s = PruebaSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        evento = servicios.enviar_prueba(s.validated_data["mensaje"], request.user)
        entregado = evento.estado == EventoSaliente.Estado.ENTREGADO
        registrar(Bitacora.Accion.CREAR, request=request, modulo="integraciones",
                  descripcion="Evento de prueba enviado a n8n.",
                  detalle={"entregado": entregado, "error": evento.ultimo_error},
                  resultado="OK" if entregado else "ERROR")
        return Response({"entregado": entregado, "error": evento.ultimo_error,
                         "recibira_whatsapp": bool(evento.payload["destinatarios"])},
                        status=status.HTTP_200_OK if entregado else status.HTTP_502_BAD_GATEWAY)


class MensajeEntranteSerializer(serializers.Serializer):
    whatsapp = serializers.CharField(max_length=30)
    texto = serializers.CharField(max_length=1000, allow_blank=True, default="")


@extend_schema(tags=["integraciones"], request=MensajeEntranteSerializer, auth=[])
class MensajeEntranteView(APIView):
    """
    n8n reenvía aquí lo que alguien escribe por WhatsApp. No usa JWT: se autentica con la firma HMAC del
    cuerpo (mismo secreto que los avisos de salida) y rechaza mensajes viejos o alterados.
    """
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []

    def post(self, request):
        cuerpo = request.body
        if len(cuerpo) > MAX_CUERPO or not verificar(
            settings.N8N_SECRETO, request.headers.get("X-DUBSS-Timestamp"),
            request.headers.get("X-DUBSS-Signature"), cuerpo,
        ):
            return Response({"detail": "Firma inválida."}, status=status.HTTP_401_UNAUTHORIZED)
        s = MensajeEntranteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            numero = normalizar_whatsapp(s.validated_data["whatsapp"])
        except ValueError:
            return Response({"detail": "Número inválido."}, status=status.HTTP_400_BAD_REQUEST)

        clave = f"wa-entrante:{numero}"
        cache.add(clave, 0, timeout=60)
        if cache.incr(clave) > LIMITE_MENSAJES_MIN:
            return Response({"detail": "Demasiados mensajes. Intenta en un minuto."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        usuario = entrante.usuario_por_whatsapp(numero)
        respuesta, intencion = entrante.responder(numero, s.validated_data["texto"])
        if intencion == "baja":
            registrar(Bitacora.Accion.EDITAR, usuario=usuario, modulo="integraciones", objeto_id=usuario.pk,
                      descripcion="El usuario se dio de baja de WhatsApp (mensaje «BAJA»).", detalle={"canal": "whatsapp"})
        return Response({"respuesta": respuesta, "intencion": intencion})
