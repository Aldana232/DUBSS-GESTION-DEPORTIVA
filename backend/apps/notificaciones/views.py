"""
apps/notificaciones/views.py
CU17 / F6-04 — Envío manual de avisos a usuarios del sistema (correo + push).
"""
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.deportes.models import Facultad
from apps.notificaciones import fcm
from apps.notificaciones.services import email_configurado, notificar_usuarios
from apps.users.models import Usuario
from apps.users.permissions import EsAdminUOrganizador

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
                     "push": resumen["push"], "todos": d["todos"], "roles": d["roles"],
                     "facultad": d["facultad"].pk if d.get("facultad") else None},
        )
        return Response({"mensaje": "Aviso enviado.", **resumen})


@extend_schema(tags=["notificaciones"])
class CanalesView(APIView):
    """Qué canales están configurados (para que la interfaz sea honesta sobre lo que realmente se enviará)."""
    permission_classes = [EsAdminUOrganizador]

    def get(self, request):
        return Response({"push": fcm.configurado(), "email": email_configurado()})
