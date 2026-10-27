"""Tests del límite de frecuencia por IP del endpoint de login."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import Usuario
from apps.users.throttles import LoginRateThrottle


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def usuario_login(db):
    return Usuario.objects.create_user(
        email="login-throttle@uagrm.edu.bo",
        password="TestPass123!",
        nombre="Login",
        apellido="Throttle",
    )


def iniciar_sesion(client, email, password):
    return client.post(
        reverse("auth-login"),
        {"email": email, "password": password},
        format="json",
    )


@pytest.mark.django_db
def test_limita_por_ip_entre_emails_inexistentes(client, monkeypatch):
    monkeypatch.setattr(LoginRateThrottle, "THROTTLE_RATES", {"login": "3/min"})

    for numero in range(3):
        respuesta = iniciar_sesion(
            client,
            f"inexistente{numero}@uagrm.edu.bo",
            "Incorrecta123!",
        )
        assert respuesta.status_code == 401

    respuesta = iniciar_sesion(client, "cuarto@uagrm.edu.bo", "Incorrecta123!")

    assert respuesta.status_code == 429
    assert "Retry-After" in respuesta
    assert str(respuesta.data["detail"]).startswith(
        "Demasiados intentos de inicio de sesión desde esta red. "
        "Intenta de nuevo en unos minutos."
    )
    assert "Disponible en" in respuesta.data["detail"]
    assert "Expected available" not in respuesta.data["detail"]


@pytest.mark.django_db
def test_logins_correctos_tambien_consumen_limite(client, usuario_login, monkeypatch):
    monkeypatch.setattr(LoginRateThrottle, "THROTTLE_RATES", {"login": "3/min"})

    for _ in range(3):
        respuesta = iniciar_sesion(client, usuario_login.email, "TestPass123!")
        assert respuesta.status_code == 200

    respuesta = iniciar_sesion(client, usuario_login.email, "TestPass123!")

    assert respuesta.status_code == 429
    assert "Retry-After" in respuesta


@pytest.mark.django_db
def test_limite_de_login_no_afecta_otros_endpoints(client, usuario_login):
    client.force_authenticate(user=usuario_login)

    for _ in range(15):
        respuesta = client.get(reverse("usuario-perfil"))
        assert respuesta.status_code == 200


@pytest.mark.django_db
def test_01_agota_el_limite_de_login(client, monkeypatch):
    monkeypatch.setattr(LoginRateThrottle, "THROTTLE_RATES", {"login": "3/min"})

    for numero in range(3):
        respuesta = iniciar_sesion(client, f"agotado{numero}@uagrm.edu.bo", "incorrecta")
        assert respuesta.status_code == 401

    respuesta = iniciar_sesion(client, "agotado-final@uagrm.edu.bo", "incorrecta")
    assert respuesta.status_code == 429


@pytest.mark.django_db
def test_02_el_login_se_aisla_del_limite_agotado_en_el_test_anterior(
    client, usuario_login, monkeypatch
):
    monkeypatch.setattr(LoginRateThrottle, "THROTTLE_RATES", {"login": "3/min"})

    respuesta = iniciar_sesion(client, usuario_login.email, "TestPass123!")

    assert respuesta.status_code == 200
