"""Pruebas de cambio de contraseña e invalidación de refresh tokens."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.models import Usuario


pytestmark = pytest.mark.django_db


@pytest.fixture
def usuario(db):
    return Usuario.objects.create_user(
        email="cambio-password@uagrm.edu.bo",
        password="ClaveAnterior123!",
        nombre="Cambio",
        apellido="Password",
    )


def test_cambio_password_invalida_todos_los_refresh_previos_y_devuelve_tokens(usuario):
    refresh_anterior = RefreshToken.for_user(usuario)
    otro_refresh_anterior = RefreshToken.for_user(usuario)
    client = APIClient()
    client.force_authenticate(user=usuario)

    respuesta = client.post(
        reverse("auth-cambio-password"),
        {
            "password_actual": "ClaveAnterior123!",
            "password_nuevo": "ClaveNueva456!",
            "password_nuevo2": "ClaveNueva456!",
        },
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.data["mensaje"] == "Contraseña actualizada correctamente."
    assert "access" in respuesta.data
    assert "refresh" in respuesta.data
    assert str(refresh_anterior) != respuesta.data["refresh"]
    assert str(otro_refresh_anterior) != respuesta.data["refresh"]

    tokens_previos = OutstandingToken.objects.filter(
        user=usuario,
        jti__in=[refresh_anterior["jti"], otro_refresh_anterior["jti"]],
    )
    assert tokens_previos.count() == 2
    assert BlacklistedToken.objects.filter(token__in=tokens_previos).count() == 2

    refresh_anterior_response = client.post(
        reverse("auth-refresh"),
        {"refresh": str(refresh_anterior)},
        format="json",
    )
    otro_refresh_response = client.post(
        reverse("auth-refresh"),
        {"refresh": str(otro_refresh_anterior)},
        format="json",
    )
    refresh_nuevo_response = client.post(
        reverse("auth-refresh"),
        {"refresh": respuesta.data["refresh"]},
        format="json",
    )

    assert refresh_anterior_response.status_code == 401
    assert otro_refresh_response.status_code == 401
    assert refresh_nuevo_response.status_code == 200
    usuario.refresh_from_db()
    assert usuario.check_password("ClaveNueva456!")
    assert not usuario.check_password("ClaveAnterior123!")


def test_password_actual_incorrecta_no_cambia_password_ni_invalida_tokens(usuario):
    refresh_anterior = RefreshToken.for_user(usuario)
    client = APIClient()
    client.force_authenticate(user=usuario)

    respuesta = client.post(
        reverse("auth-cambio-password"),
        {
            "password_actual": "Incorrecta123!",
            "password_nuevo": "ClaveNueva456!",
            "password_nuevo2": "ClaveNueva456!",
        },
        format="json",
    )

    assert respuesta.status_code == 400
    assert not BlacklistedToken.objects.filter(
        token__jti=refresh_anterior["jti"]
    ).exists()
    usuario.refresh_from_db()
    assert usuario.check_password("ClaveAnterior123!")
