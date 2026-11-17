"""
apps/users/views/user_views.py
Vistas CRUD de usuarios.
"""
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import PermissionDenied
from django.db import transaction

from apps.auditoria.mixins import AuditaCrudMixin
from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from ..models import Usuario
from ..serializers import (
    RestablecerPasswordAdminSerializer,
    UsuarioAdminCreateSerializer,
    UsuarioAdminSerializer,
    UsuarioSerializer,
)
from ..permissions import EsAdmin, EsCuentaConPanel, EsDelegado, EsUsuarioOperativo
from ..roles import es_superadmin
from ..services import invalidar_tokens_usuario
from apps.deportes.models import Equipo
from apps.deportes.serializers import EquipoSerializer


@extend_schema(tags=["usuarios"])
class MiPerfilView(generics.RetrieveUpdateAPIView):
    """CU02 — Ver y actualizar el perfil del usuario autenticado."""
    serializer_class   = UsuarioSerializer
    permission_classes = [EsCuentaConPanel]
    parser_classes     = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user


@extend_schema(tags=["usuarios"])
class ListaUsuariosView(AuditaCrudMixin, generics.ListCreateAPIView):
    """Lista y crea cuentas — solo Admin DUBSS."""
    auditoria_modulo = "usuario"
    auditoria_textos = {"crear": "Cuenta creada por un administrador."}
    permission_classes = [EsAdmin]
    queryset           = Usuario.objects.all().order_by("apellido", "nombre")
    filterset_fields   = ["rol", "facultad", "is_active"]
    search_fields      = ["email", "nombre", "apellido", "ci"]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UsuarioAdminCreateSerializer
        return UsuarioAdminSerializer


@extend_schema(tags=["usuarios"])
class DetalleUsuarioView(generics.RetrieveUpdateDestroyAPIView):
    """Detalle, edición y baja de un usuario — Admin DUBSS."""
    serializer_class   = UsuarioAdminSerializer
    permission_classes = [EsAdmin]
    queryset           = Usuario.objects.all()

    def destroy(self, request, *args, **kwargs):
        # Baja lógica, no eliminación física
        usuario = self.get_object()
        if usuario.pk == request.user.pk:
            return Response(
                {"error": "No puedes darte de baja a ti mismo."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if es_superadmin(usuario) and not es_superadmin(request.user):
            raise PermissionDenied(
                "Solo un superadministrador puede dar de baja una cuenta SUPERADMIN."
            )
        usuario.is_active = False
        usuario.save(update_fields=["is_active"])
        registrar(
            Bitacora.Accion.ELIMINAR,
            request=request,
            modulo="usuario",
            objeto_id=usuario.pk,
            descripcion="Usuario dado de baja por un administrador.",
        )
        registrar(
            Bitacora.Accion.CAMBIO_ESTADO,
            request=request,
            modulo="usuario",
            objeto_id=usuario.pk,
            descripcion="Cuenta desactivada por un administrador.",
            detalle={"is_active": False},
        )
        return Response(
            {"mensaje": f"Usuario {usuario.nombre_completo} dado de baja."},
            status=status.HTTP_200_OK,
        )

    def perform_update(self, serializer):
        usuario = serializer.instance
        rol_anterior = usuario.rol
        super().perform_update(serializer)
        registrar(
            Bitacora.Accion.EDITAR,
            request=self.request,
            modulo="usuario",
            objeto_id=usuario.pk,
            descripcion="Usuario editado por un administrador.",
            detalle={"campos": sorted(serializer.validated_data)},
        )
        if "is_active" in serializer.validated_data:
            registrar(
                Bitacora.Accion.CAMBIO_ESTADO,
                request=self.request,
                modulo="usuario",
                objeto_id=usuario.pk,
                descripcion="Estado de usuario cambiado por un administrador.",
                detalle={"is_active": usuario.is_active},
            )
        if rol_anterior != usuario.rol:
            registrar(
                Bitacora.Accion.CAMBIO_ROL,
                request=self.request,
                modulo="usuario",
                objeto_id=usuario.pk,
                descripcion="Rol de usuario cambiado por un administrador.",
                detalle={"anterior": rol_anterior, "nuevo": usuario.rol},
            )


@extend_schema(tags=["usuarios"])
class RestablecerPasswordUsuarioView(APIView):
    """Restablece la contraseña de una cuenta desde administración."""
    permission_classes = [EsAdmin]

    @extend_schema(
        summary="Restablecer contraseña de usuario",
        request=RestablecerPasswordAdminSerializer,
    )
    def post(self, request, pk):
        usuario = generics.get_object_or_404(Usuario, pk=pk)
        if es_superadmin(usuario) and not es_superadmin(request.user):
            raise PermissionDenied(
                "Solo un superadministrador puede restablecer la contraseña de una cuenta SUPERADMIN."
            )
        serializer = RestablecerPasswordAdminSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            usuario.set_password(serializer.validated_data["password_nuevo"])
            usuario.save(update_fields=["password"])
            invalidar_tokens_usuario(usuario)
        registrar(
            Bitacora.Accion.CAMBIO_PASSWORD,
            request=request,
            modulo="usuario",
            objeto_id=usuario.pk,
            descripcion="Contraseña restablecida por un administrador.",
        )
        return Response({"mensaje": "Contraseña restablecida correctamente."})


@extend_schema(tags=["usuarios"])
class MiUsuarioView(APIView):
    """Datos de sesión para resolver el rol y la facultad actuales."""
    permission_classes = [EsCuentaConPanel]

    @extend_schema(summary="Consultar mi cuenta, rol y facultad")
    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


@extend_schema(tags=["usuarios"])
class MiEquipoView(APIView):
    """Equipos administrados por el delegado autenticado."""
    permission_classes = [EsDelegado]

    @extend_schema(summary="Consultar mis equipos")
    def get(self, request):
        equipos = Equipo.objects.filter(
            delegado=request.user,
        ).select_related("facultad", "delegado").prefetch_related("jugadores__usuario")
        return Response(
            EquipoSerializer(equipos, many=True, context={"request": request}).data
        )


@extend_schema(tags=["usuarios"])
class ActualizarFCMTokenView(APIView):
    """
    Registra (POST) o quita (DELETE) el token de notificaciones push del celular del usuario.

    Un token identifica a UN dispositivo: si se registra para este usuario se retira de cualquier otra cuenta.
    Sin esto, quien inicia sesión en un celular que antes usó otra persona seguiría haciendo que los avisos de
    la otra persona le lleguen a este dispositivo.
    """
    permission_classes = [EsUsuarioOperativo]

    def post(self, request):
        token = str(request.data.get("fcm_token", "")).strip()
        if not token:
            return Response(
                {"error": "fcm_token es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(token) > 255:
            return Response({"error": "fcm_token no es válido."}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            Usuario.objects.filter(fcm_token=token).exclude(pk=request.user.pk).update(fcm_token="")
            request.user.fcm_token = token
            request.user.save(update_fields=["fcm_token"])
        return Response({"mensaje": "Token FCM actualizado."})

    def delete(self, request):
        request.user.fcm_token = ""
        request.user.save(update_fields=["fcm_token"])
        return Response(status=status.HTTP_204_NO_CONTENT)
