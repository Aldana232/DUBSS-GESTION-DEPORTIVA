"""Pruebas de los eventos de auditoría generados por usuarios y sesión."""
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditoria.models import Bitacora
from apps.users.models import Usuario


pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def usuario(db):
    return Usuario.objects.create_user(
        email="usuario-auditoria@uagrm.edu.bo",
        password="TestPass123!",
        nombre="Usuario",
        apellido="Auditoria",
    )


@pytest.fixture
def admin(db):
    return Usuario.objects.create_user(
        email="admin-eventos@uagrm.edu.bo",
        password="AdminPass123!",
        nombre="Admin",
        apellido="Eventos",
        rol=Usuario.Rol.ADMIN_DUBSS,
    )


def iniciar_sesion(client, email, password="TestPass123!"):
    return client.post(
        reverse("auth-login"),
        {"email": email, "password": password},
        format="json",
    )


def test_login_correcto_registra_evento_sin_credenciales(client, usuario):
    respuesta = iniciar_sesion(client, usuario.email)

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.LOGIN)
    assert registro.usuario == usuario
    assert registro.entidad == "usuario"
    assert registro.entidad_id == usuario.pk
    assert registro.detalle == {}
    assert "TestPass123!" not in str(registro.detalle)
    assert respuesta.data["access"] not in str(registro.detalle)
    assert respuesta.data["refresh"] not in str(registro.detalle)


def test_login_fallido_registra_email_y_resultado_denegado(client):
    email = "no-registrado@uagrm.edu.bo"

    respuesta = iniciar_sesion(client, email, "Secreto123!")

    assert respuesta.status_code == 401
    registro = Bitacora.objects.get(accion=Bitacora.Accion.LOGIN_FALLIDO)
    assert registro.usuario is None
    assert registro.usuario_email == email
    assert registro.resultado == Bitacora.Resultado.DENEGADO
    assert registro.detalle == {}
    assert "Secreto123!" not in str(registro.detalle)


def test_quinto_fallo_registra_fallo_y_bloqueo(client, usuario):
    for _ in range(5):
        respuesta = iniciar_sesion(client, usuario.email, "Incorrecta123!")

    assert respuesta.status_code == 429
    assert Bitacora.objects.filter(accion=Bitacora.Accion.LOGIN_FALLIDO).count() == 5
    bloqueo = Bitacora.objects.get(accion=Bitacora.Accion.CUENTA_BLOQUEADA)
    assert bloqueo.usuario == usuario
    assert bloqueo.resultado == Bitacora.Resultado.DENEGADO
    assert bloqueo.detalle == {}
    assert "Disponible en" in respuesta.data["detail"]
    assert "Expected available" not in respuesta.data["detail"]


def test_intento_durante_bloqueo_registra_cuenta_bloqueada(client, usuario):
    usuario.bloqueado_hasta = timezone.now() + timedelta(minutes=15)
    usuario.save(update_fields=["bloqueado_hasta"])

    respuesta = iniciar_sesion(client, usuario.email)

    assert respuesta.status_code == 429
    assert Bitacora.objects.filter(
        accion=Bitacora.Accion.CUENTA_BLOQUEADA,
        usuario=usuario,
    ).count() == 1
    assert not Bitacora.objects.filter(
        accion=Bitacora.Accion.LOGIN_FALLIDO,
    ).exists()


def test_logout_registra_evento(client, usuario):
    client.force_authenticate(user=usuario)
    refresh = str(RefreshToken.for_user(usuario))

    respuesta = client.post(
        reverse("auth-logout"),
        {"refresh": refresh},
        format="json",
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.LOGOUT)
    assert registro.usuario == usuario
    assert registro.detalle == {}
    assert refresh not in str(registro.detalle)


def test_logout_no_devuelve_el_token_en_errores(client, usuario):
    client.force_authenticate(user=usuario)
    token_invalido = "secreto-de-refresh-no-valido"

    respuesta = client.post(
        reverse("auth-logout"),
        {"refresh": token_invalido},
        format="json",
    )

    assert respuesta.status_code == 400
    assert token_invalido not in str(respuesta.data)


def test_cambio_password_registra_evento_sin_guardar_password(client, usuario):
    client.force_authenticate(user=usuario)

    respuesta = client.post(
        reverse("auth-cambio-password"),
        {
            "password_actual": "TestPass123!",
            "password_nuevo": "NuevaSegura456!",
            "password_nuevo2": "NuevaSegura456!",
        },
        format="json",
    )

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.CAMBIO_PASSWORD)
    assert registro.usuario == usuario
    assert registro.entidad_id == usuario.pk
    assert registro.detalle == {}
    assert "TestPass123!" not in str(registro.detalle)
    assert "NuevaSegura456!" not in str(registro.detalle)


def test_alta_administrativa_registra_usuario_y_rol(client, admin):
    client.force_authenticate(user=admin)

    respuesta = client.post(
        reverse("auth-registro"),
        {
            "email": "nuevo@uagrm.edu.bo",
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "rol": Usuario.Rol.ARBITRO,
            "password": "NuevaSegura456!",
            "password2": "NuevaSegura456!",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    creado = Usuario.objects.get(email="nuevo@uagrm.edu.bo")
    registro = Bitacora.objects.get(accion=Bitacora.Accion.CREAR)
    assert registro.usuario == admin
    assert registro.entidad == "usuario"
    assert registro.entidad_id == creado.pk
    assert registro.detalle == {"rol": Usuario.Rol.ARBITRO}
    assert "NuevaSegura456!" not in str(registro.detalle)


def test_edicion_administrativa_registra_editar_y_cambio_rol(client, admin, usuario):
    client.force_authenticate(user=admin)

    respuesta = client.patch(
        reverse("usuario-detalle", kwargs={"pk": usuario.pk}),
        {"nombre": "Editado", "rol": Usuario.Rol.ARBITRO},
        format="json",
    )

    assert respuesta.status_code == 200
    edicion = Bitacora.objects.get(accion=Bitacora.Accion.EDITAR)
    cambio_rol = Bitacora.objects.get(accion=Bitacora.Accion.CAMBIO_ROL)
    assert edicion.usuario == admin
    assert edicion.entidad_id == usuario.pk
    assert cambio_rol.usuario == admin
    assert cambio_rol.entidad_id == usuario.pk
    assert cambio_rol.detalle == {
        "anterior": Usuario.Rol.DEPORTISTA,
        "nuevo": Usuario.Rol.ARBITRO,
    }


def test_baja_administrativa_registra_eliminar(client, admin, usuario):
    client.force_authenticate(user=admin)

    respuesta = client.delete(reverse("usuario-detalle", kwargs={"pk": usuario.pk}))

    assert respuesta.status_code == 200
    registro = Bitacora.objects.get(accion=Bitacora.Accion.ELIMINAR)
    assert registro.usuario == admin
    assert registro.entidad == "usuario"
    assert registro.entidad_id == usuario.pk
