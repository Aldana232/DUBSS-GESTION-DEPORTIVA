"""Tests del bloqueo temporal de cuentas tras intentos fallidos de login."""
from datetime import timedelta

import pytest
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import Usuario


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def usuario_login(db):
    return Usuario.objects.create_user(
        email="login@uagrm.edu.bo",
        password="TestPass123!",
        nombre="Login",
        apellido="Test",
    )


def iniciar_sesion(client, email, password):
    return client.post(
        reverse("auth-login"),
        {"email": email, "password": password},
        format="json",
    )


@pytest.mark.django_db
def test_cuatro_fallos_no_bloquean_cuenta(client, usuario_login):
    for _ in range(4):
        respuesta = iniciar_sesion(client, usuario_login.email, "incorrecta")
        assert respuesta.status_code == 401

    usuario_login.refresh_from_db()
    assert usuario_login.intentos_fallidos == 4
    assert usuario_login.bloqueado_hasta is None


@pytest.mark.django_db
def test_quinto_fallo_bloquea_cuenta_y_devuelve_retry_after(client, usuario_login):
    for _ in range(5):
        respuesta = iniciar_sesion(client, usuario_login.email, "incorrecta")

    usuario_login.refresh_from_db()
    assert respuesta.status_code == 429
    assert "Cuenta bloqueada temporalmente hasta las " in respuesta.data["detail"]
    assert "Disponible en" in respuesta.data["detail"]
    assert "Expected available" not in respuesta.data["detail"]
    assert usuario_login.bloqueado_hasta is not None
    restante = usuario_login.bloqueado_hasta - timezone.now()
    assert timedelta(minutes=14) < restante <= timedelta(minutes=15)
    assert usuario_login.intentos_fallidos == 0
    assert "Retry-After" in respuesta


@pytest.mark.django_db
def test_cuenta_bloqueada_no_permite_password_correcta_ni_incrementa_contador(
    client, usuario_login
):
    usuario_login.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
    usuario_login.intentos_fallidos = 2
    usuario_login.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])

    respuesta = iniciar_sesion(client, usuario_login.email, "TestPass123!")

    usuario_login.refresh_from_db()
    assert respuesta.status_code == 429
    assert "tokens" not in respuesta.data
    assert usuario_login.intentos_fallidos == 2


@pytest.mark.django_db
def test_bloqueo_vencido_se_limpia_al_iniciar_sesion_correctamente(client, usuario_login):
    usuario_login.bloqueado_hasta = timezone.now() - timedelta(minutes=1)
    usuario_login.intentos_fallidos = 4
    usuario_login.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])

    respuesta = iniciar_sesion(client, usuario_login.email, "TestPass123!")

    usuario_login.refresh_from_db()
    assert respuesta.status_code == 200
    assert usuario_login.intentos_fallidos == 0
    assert usuario_login.bloqueado_hasta is None


@pytest.mark.django_db
def test_acierto_reinicia_tres_intentos_fallidos(client, usuario_login):
    for _ in range(3):
        respuesta = iniciar_sesion(client, usuario_login.email, "incorrecta")
        assert respuesta.status_code == 401

    respuesta = iniciar_sesion(client, usuario_login.email, "TestPass123!")

    usuario_login.refresh_from_db()
    assert respuesta.status_code == 200
    assert usuario_login.intentos_fallidos == 0
    assert usuario_login.bloqueado_hasta is None


@pytest.mark.django_db
def test_password_incorrecta_tras_bloqueo_vencido_reinicia_conteo(client, usuario_login):
    usuario_login.bloqueado_hasta = timezone.now() - timedelta(minutes=1)
    usuario_login.intentos_fallidos = 4
    usuario_login.save(update_fields=["bloqueado_hasta", "intentos_fallidos"])

    respuesta = iniciar_sesion(client, usuario_login.email, "incorrecta")

    usuario_login.refresh_from_db()
    assert respuesta.status_code == 401
    assert usuario_login.intentos_fallidos == 1
    assert usuario_login.bloqueado_hasta is None


@pytest.mark.django_db
def test_email_inexistente_devuelve_mismo_error_sin_crear_usuario(client, usuario_login):
    respuesta_password_incorrecta = iniciar_sesion(
        client, usuario_login.email, "incorrecta"
    )
    respuesta_email_inexistente = iniciar_sesion(
        client, "noexiste@uagrm.edu.bo", "incorrecta"
    )

    assert respuesta_email_inexistente.status_code == 401
    assert (
        respuesta_email_inexistente.data["detail"]
        == respuesta_password_incorrecta.data["detail"]
    )
    assert Usuario.objects.count() == 1


@pytest.mark.django_db
def test_usuario_inactivo_no_incrementa_intentos_fallidos(client, usuario_login):
    usuario_login.is_active = False
    usuario_login.save(update_fields=["is_active"])

    for _ in range(5):
        respuesta = iniciar_sesion(client, usuario_login.email, "incorrecta")
        assert respuesta.status_code == 401

    usuario_login.refresh_from_db()
    assert usuario_login.intentos_fallidos == 0
    assert usuario_login.bloqueado_hasta is None


@pytest.mark.django_db
def test_bloqueo_de_usuario_no_impide_login_de_otro_usuario(client, usuario_login):
    otro_usuario = Usuario.objects.create_user(
        email="otro@uagrm.edu.bo",
        password="OtraPass123!",
        nombre="Otro",
        apellido="Usuario",
    )
    usuario_login.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
    usuario_login.save(update_fields=["bloqueado_hasta"])

    respuesta = iniciar_sesion(client, otro_usuario.email, "OtraPass123!")

    assert respuesta.status_code == 200
