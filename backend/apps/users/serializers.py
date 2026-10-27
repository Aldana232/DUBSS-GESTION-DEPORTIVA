"""
apps/users/serializers.py
Serializers para registro, login y gestión de usuarios.
"""
from datetime import timedelta

from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.password_validation import validate_password
from django.conf import settings
from django.db.models import F
from django.utils import timezone
from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from .exceptions import ThrottledES
from .models import Usuario


class UsuarioAdminCreateSerializer(serializers.ModelSerializer):
    """Alta administrativa de usuario con validación de contraseña."""
    password  = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True, label="Confirmar contraseña")

    class Meta:
        model  = Usuario
        fields = [
            "email", "nombre", "apellido", "ci",
            "telefono", "rol", "facultad",
            "password", "password2",
        ]
        extra_kwargs = {"rol": {"required": True}}

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password2"):
            raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})
        return attrs

    def create(self, validated_data):
        return Usuario.objects.create_user(**validated_data)


class UsuarioSerializer(serializers.ModelSerializer):
    """Datos del perfil propio; los campos de rol y estado son solo lectura."""
    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model  = Usuario
        fields = [
            "id", "email", "nombre", "apellido", "nombre_completo",
            "ci", "telefono", "foto_perfil",
            "rol", "facultad",
            "is_active", "fecha_registro", "ultimo_acceso",
        ]
        read_only_fields = [
            "id", "email", "rol", "facultad", "is_active",
            "fecha_registro", "ultimo_acceso",
        ]


class UsuarioAdminSerializer(serializers.ModelSerializer):
    """Serializer administrativo para consultar y editar cuentas de usuario."""
    nombre_completo = serializers.CharField(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "email", "nombre", "apellido", "nombre_completo",
            "ci", "telefono", "foto_perfil",
            "rol", "facultad",
            "is_active", "fecha_registro", "ultimo_acceso",
        ]
        read_only_fields = ["id", "email", "fecha_registro", "ultimo_acceso"]

    def validate(self, attrs):
        request = self.context.get("request")
        usuario_solicitante = getattr(request, "user", None)
        if self.instance is not None and usuario_solicitante is not None:
            es_propio = self.instance.pk == usuario_solicitante.pk
            if es_propio and attrs.get("rol", self.instance.rol) != self.instance.rol:
                raise serializers.ValidationError(
                    {"rol": "No puedes cambiar tu propio rol."}
                )
            if es_propio and attrs.get("is_active", self.instance.is_active) != self.instance.is_active:
                raise serializers.ValidationError(
                    {"is_active": "No puedes desactivarte a ti mismo."}
                )
        return attrs


class UsuarioResumenSerializer(serializers.ModelSerializer):
    """Serializer compacto para listas y relaciones."""
    class Meta:
        model  = Usuario
        fields = ["id", "nombre_completo", "email", "rol", "facultad"]


class CambioPasswordSerializer(serializers.Serializer):
    """Cambio de contraseña autenticado."""
    password_actual = serializers.CharField(required=True)
    password_nuevo  = serializers.CharField(required=True, validators=[validate_password])
    password_nuevo2 = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs["password_nuevo"] != attrs["password_nuevo2"]:
            raise serializers.ValidationError({"password_nuevo": "Las contraseñas no coinciden."})
        return attrs


class TokenPersonalizadoSerializer(TokenObtainPairSerializer):
    """JWT con datos extra del usuario en el payload."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Claims personalizados incluidos en el token
        token["nombre_completo"] = user.nombre_completo
        token["email"]           = user.email
        token["rol"]             = user.rol
        return token

    def validate(self, attrs):
        email = attrs.get(self.username_field)
        usuario = Usuario.objects.filter(email__iexact=email).first()
        ahora = timezone.now()

        if usuario is not None and usuario.bloqueado_hasta is not None:
            if usuario.bloqueado_hasta > ahora:
                raise self._cuenta_bloqueada(
                    usuario.bloqueado_hasta, ahora, usuario
                )
            usuario.bloqueado_hasta = None
            usuario.intentos_fallidos = 0
            usuario.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])

        try:
            data = super().validate(attrs)
        except AuthenticationFailed:
            registrar(
                Bitacora.Accion.LOGIN_FALLIDO,
                request=self.context.get("request"),
                usuario=usuario,
                email=email or "",
                entidad="usuario",
                entidad_id=usuario.pk if usuario is not None else None,
                descripcion="Intento de inicio de sesión fallido.",
                resultado=Bitacora.Resultado.DENEGADO,
            )
            if usuario is not None and usuario.is_active:
                Usuario.objects.filter(pk=usuario.pk).update(
                    intentos_fallidos=F("intentos_fallidos") + 1
                )
                usuario.refresh_from_db(fields=["intentos_fallidos"])
                if usuario.intentos_fallidos >= settings.LOGIN_MAX_INTENTOS:
                    ahora = timezone.now()
                    usuario.bloqueado_hasta = ahora + timedelta(
                        minutes=settings.LOGIN_BLOQUEO_MINUTOS
                    )
                    usuario.intentos_fallidos = 0
                    usuario.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])
                    raise self._cuenta_bloqueada(
                        usuario.bloqueado_hasta, ahora, usuario
                    )
            raise

        self.user.intentos_fallidos = 0
        self.user.bloqueado_hasta = None
        self.user.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        registrar(
            Bitacora.Accion.LOGIN,
            request=self.context.get("request"),
            usuario=self.user,
            entidad="usuario",
            entidad_id=self.user.pk,
            descripcion="Inicio de sesión correcto.",
        )
        # También retorna info del usuario en el cuerpo de la respuesta
        data["usuario"] = UsuarioSerializer(self.user).data
        return data

    def _cuenta_bloqueada(self, bloqueado_hasta, ahora, usuario):
        hora_local = timezone.localtime(bloqueado_hasta).strftime("%H:%M")
        segundos_restantes = max(1, int((bloqueado_hasta - ahora).total_seconds()))
        registrar(
            Bitacora.Accion.CUENTA_BLOQUEADA,
            request=self.context.get("request"),
            usuario=usuario,
            email=usuario.email,
            entidad="usuario",
            entidad_id=usuario.pk,
            descripcion="Intento de inicio de sesión en una cuenta bloqueada.",
            resultado=Bitacora.Resultado.DENEGADO,
        )
        return ThrottledES(
            wait=segundos_restantes,
            detail=(
                f"Cuenta bloqueada temporalmente hasta las {hora_local}. "
                "Intenta de nuevo más tarde."
            ),
        )
