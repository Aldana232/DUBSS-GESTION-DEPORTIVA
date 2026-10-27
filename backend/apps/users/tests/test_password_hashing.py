"""Pruebas de Argon2 y actualización gradual de hashes PBKDF2."""
import pytest
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import Usuario


pytestmark = pytest.mark.django_db


HASHERS_ARGON2_Y_PBKDF2 = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]


def test_password_nueva_se_guarda_con_argon2(settings):
    settings.PASSWORD_HASHERS = HASHERS_ARGON2_Y_PBKDF2

    usuario = Usuario.objects.create_user(
        email="argon2-nuevo@uagrm.edu.bo",
        password="ClaveSegura123!",
        nombre="Usuario",
        apellido="Argon2",
    )

    assert usuario.password.startswith("argon2$")
    assert usuario.check_password("ClaveSegura123!")


def test_login_actualiza_hash_pbkdf2_existente_a_argon2(settings):
    settings.PASSWORD_HASHERS = HASHERS_ARGON2_Y_PBKDF2
    usuario = Usuario.objects.create_user(
        email="pbkdf2-antiguo@uagrm.edu.bo",
        password="ClaveTemporal123!",
        nombre="Usuario",
        apellido="PBKDF2",
    )
    usuario.password = make_password(
        "ClaveAnterior123!",
        hasher="pbkdf2_sha256",
    )
    usuario.save(update_fields=["password"])
    assert usuario.password.startswith("pbkdf2_sha256$")

    respuesta = APIClient().post(
        reverse("auth-login"),
        {
            "email": usuario.email,
            "password": "ClaveAnterior123!",
        },
        format="json",
    )

    assert respuesta.status_code == 200
    usuario.refresh_from_db()
    assert usuario.password.startswith("argon2$")
    assert usuario.check_password("ClaveAnterior123!")
