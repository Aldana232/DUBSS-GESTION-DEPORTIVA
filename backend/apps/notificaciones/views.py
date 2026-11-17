"""
apps/notificaciones/views.py
CU17 / F6-04 — Envío manual de avisos a usuarios del sistema (correo + push).
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.deportes.models import Facultad
from apps.notificaciones import fcm
from apps.integraciones import servicios as integraciones
from apps.notificaciones.services import email_configurado, notificar_usuarios
from apps.users.models import Usuario
from apps.notificaciones.models import Notificacion
from apps.users.permissions import EsAdminUOrganizador, EsCuentaConPanel

ROLES_DESTINO = [Usuario.Rol.ADMIN_DUBSS, Usuario.Rol.ORGANIZADOR, Usuario.Rol.DELEGADO]


class EnvioSerializer(serializers.Serializer):
    titulo = serializers.CharField(max_length=100, default="DUBSS", allow_blank=False)
    mensaje = serializers.CharField(max_length=500)
    todos = serializers.BooleanField(default=False)
    roles = serializers.ListField(child=serializers.ChoiceField(choices=ROLES_DESTINO), required=False, default=list)
    facultad = serializers.PrimaryKeyRelatedField(queryset=Facultad.objects.all(), required=False, allow_null=True)
    usuarios = serializers.ListField(child=serializers.IntegerField(), required=False, default=list, max_length=200)

    def validate_mensaje(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Escribe el mensaje.")
        return valor

    def validate(self, datos):
        if not (datos["todos"] or datos["roles"] or datos.get("facultad") or datos["usuarios"]):
            raise serializers.ValidationError(
                {"destinatarios": "Elige a quién enviar: todos, un rol, una facultad o usuarios concretos."})
        return datos


@extend_schema(tags=["notificaciones"])
class EnviarNotificacionView(APIView):
    """CU17 — Envía un aviso por correo y push. Solo administración y organización."""
    permission_classes = [EsAdminUOrganizador]

    @extend_schema(summary="CU17 — Enviar notificación a usuarios", request=EnvioSerializer)
    def post(self, request):
        s = EnvioSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data

        destinatarios = Usuario.objects.filter(is_active=True, rol__in=ROLES_DESTINO)
        if not d["todos"]:
            if d["roles"]:
                destinatarios = destinatarios.filter(rol__in=d["roles"])
            if d.get("facultad"):
                destinatarios = destinatarios.filter(facultad=d["facultad"])
            if d["usuarios"]:
                destinatarios = destinatarios.filter(pk__in=d["usuarios"])
        destinatarios = list(destinatarios)
        if not destinatarios:
            return Response({"detail": "Ningún usuario activo coincide con los destinatarios elegidos."},
                            status=status.HTTP_400_BAD_REQUEST)

        resumen = notificar_usuarios(destinatarios, d["titulo"], d["mensaje"])
        registrar(
            Bitacora.Accion.CREAR, request=request, modulo="notificacion",
            descripcion="Aviso enviado a usuarios.",
            detalle={"titulo": d["titulo"], "destinatarios": resumen["usuarios"], "email": resumen["email"],
                     "push": resumen["push"], "whatsapp": resumen["whatsapp"], "todos": d["todos"], "roles": d["roles"],
                     "facultad": d["facultad"].pk if d.get("facultad") else None},
        )
        return Response({"mensaje": "Aviso enviado.", **resumen})


@extend_schema(tags=["notificaciones"])
class CanalesView(APIView):
    """Qué canales están configurados (para que la interfaz sea honesta sobre lo que realmente se enviará)."""
    permission_classes = [EsAdminUOrganizador]

    def get(self, request):
        return Response({"push": fcm.configurado(), "email": email_configurado(),
                         "whatsapp": integraciones.configurado()})


# ─── Bandeja personal (dentro de la app) ──────────────────────────────────────

class NotificacionSerializer(serializers.ModelSerializer):
    leida = serializers.SerializerMethodField()

    class Meta:
        model = Notificacion
        fields = ["id", "titulo", "mensaje", "datos", "creada", "leida"]

    def get_leida(self, obj) -> bool:
        return obj.leida_en is not None


@extend_schema(tags=["notificaciones"], responses=NotificacionSerializer(many=True))
class MisNotificacionesView(generics.ListAPIView):
    """Las notificaciones del usuario autenticado (nunca las de otro). `?no_leidas=1` filtra las pendientes."""
    permission_classes = [EsCuentaConPanel]
    serializer_class = NotificacionSerializer

    def get_queryset(self):
        qs = Notificacion.objects.filter(usuario=self.request.user)
        if self.request.query_params.get("no_leidas") in ("1", "true"):
            qs = qs.filter(leida_en__isnull=True)
        return qs


@extend_schema(tags=["notificaciones"])
class ResumenNotificacionesView(APIView):
    """Cantidad de notificaciones sin leer (para la insignia de la campana; se consulta seguido, por eso es liviana)."""
    permission_classes = [EsCuentaConPanel]

    def get(self, request):
        return Response({"no_leidas": Notificacion.objects.filter(usuario=request.user, leida_en__isnull=True).count()})


@extend_schema(tags=["notificaciones"], request=None)
class LeerNotificacionView(APIView):
    permission_classes = [EsCuentaConPanel]

    def post(self, request, pk):
        n = get_object_or_404(Notificacion, pk=pk, usuario=request.user)      # la de otro usuario da 404, no 403
        if n.leida_en is None:
            n.leida_en = timezone.now()
            n.save(update_fields=["leida_en"])
        return Response(NotificacionSerializer(n).data)


@extend_schema(tags=["notificaciones"], request=None)
class LeerTodasView(APIView):
    permission_classes = [EsCuentaConPanel]

    def post(self, request):
        n = Notificacion.objects.filter(usuario=request.user, leida_en__isnull=True).update(leida_en=timezone.now())
        return Response({"marcadas": n})
