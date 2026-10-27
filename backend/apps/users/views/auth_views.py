"""
apps/users/views/auth_views.py
Vistas de autenticación: registro, login JWT, refresh, logout.
"""
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from drf_spectacular.utils import extend_schema
from django.db import transaction

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from ..serializers import (
    UsuarioAdminCreateSerializer,
    TokenPersonalizadoSerializer,
    CambioPasswordSerializer,
)
from ..permissions import EsAdminDUBSS
from ..throttles import LoginRateThrottle
from ..exceptions import ThrottledES


@extend_schema(
    tags=["auth"],
    description="Alta de cuenta por el administrador (RF2). El registro público está cerrado.",
)
class RegistroView(generics.CreateAPIView):
    """Alta de cuenta por el administrador (RF2). El registro público está cerrado."""
    serializer_class = UsuarioAdminCreateSerializer
    permission_classes = [EsAdminDUBSS]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        registrar(
            Bitacora.Accion.CREAR,
            request=request,
            entidad="usuario",
            entidad_id=usuario.pk,
            descripcion="Usuario creado por un administrador.",
            detalle={"rol": usuario.rol},
        )
        return Response(
            {
                "mensaje":  "Usuario registrado exitosamente.",
                "usuario":  serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


@extend_schema(tags=["auth"])
class LoginView(TokenObtainPairView):
    """
    CU01 — Login. Devuelve access + refresh token con datos del usuario.
    """
    serializer_class = TokenPersonalizadoSerializer
    throttle_classes = [LoginRateThrottle]

    def throttled(self, request, wait):
        raise ThrottledES(
            wait=wait,
            detail=(
                "Demasiados intentos de inicio de sesión desde esta red. "
                "Intenta de nuevo en unos minutos."
            ),
        )


@extend_schema(tags=["auth"])
class RefreshTokenView(TokenRefreshView):
    """Renueva el access token usando el refresh token."""


@extend_schema(tags=["auth"])
class LogoutView(APIView):
    """
    Cierre de sesión: invalida el refresh token (blacklist JWT).
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            registrar(
                Bitacora.Accion.LOGOUT,
                request=request,
                descripcion="Cierre de sesión correcto.",
            )
            return Response(
                {"mensaje": "Sesión cerrada correctamente."},
                status=status.HTTP_200_OK,
            )
        except KeyError:
            return Response(
                {"error": "Se requiere el refresh token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return Response(
                {"error": "El token de actualización no es válido o ya expiró."},
                status=status.HTTP_400_BAD_REQUEST,
            )


@extend_schema(tags=["auth"])
class CambioPasswordView(APIView):
    """
    CU02 — Cambio de contraseña del usuario autenticado.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CambioPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["password_actual"]):
            return Response(
                {"error": "La contraseña actual es incorrecta."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            user.set_password(serializer.validated_data["password_nuevo"])
            user.save(update_fields=["password"])

            tokens_previos = OutstandingToken.objects.filter(user=user)
            for token in tokens_previos:
                BlacklistedToken.objects.get_or_create(token=token)

            refresh = TokenPersonalizadoSerializer.get_token(user)
            access = refresh.access_token

        registrar(
            Bitacora.Accion.CAMBIO_PASSWORD,
            request=request,
            entidad="usuario",
            entidad_id=user.pk,
            descripcion="Contraseña actualizada.",
        )

        return Response(
            {
                "mensaje": "Contraseña actualizada correctamente.",
                "refresh": str(refresh),
                "access": str(access),
            },
            status=status.HTTP_200_OK,
        )
