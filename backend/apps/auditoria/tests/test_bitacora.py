"""Tests de servicios y consulta de la bitácora de auditoría."""
from datetime import timedelta

import pytest
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory

from apps.auditoria.models import Bitacora
from apps.auditoria.services import registrar
from apps.users.models import Usuario


pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def usuario(db):
    return Usuario.objects.create_user(
        email="usuario@uagrm.edu.bo",
        password="TestPass123!",
        nombre="Usuario",
        apellido="Prueba",
        rol=Usuario.Rol.DEPORTISTA,
    )


@pytest.fixture
def admin(db):
    return Usuario.objects.create_user(
        email="admin-auditoria@uagrm.edu.bo",
        password="AdminPass123!",
        nombre="Admin",
        apellido="Auditoria",
        rol=Usuario.Rol.ADMIN_DUBSS,
    )


def test_registrar_guarda_datos_y_direccion_ip(usuario):
    request = APIRequestFactory().post("/accion/", REMOTE_ADDR="192.0.2.10")
    request.user = usuario

    registro = registrar(
        Bitacora.Accion.CREAR,
        request=request,
        entidad="usuario",
        entidad_id=42,
        descripcion="Cuenta creada",
    )

    assert registro.usuario == usuario
    assert registro.accion == Bitacora.Accion.CREAR
    assert registro.entidad == "usuario"
    assert registro.entidad_id == 42
    assert registro.descripcion == "Cuenta creada"
    assert registro.ip_address == "192.0.2.10"


def test_registrar_toma_usuario_autenticado_del_request(usuario):
    request = APIRequestFactory().post("/accion/")
    request.user = usuario

    registro = registrar(Bitacora.Accion.LOGIN, request=request)

    assert registro.usuario == usuario
    assert registro.usuario_email == usuario.email


def test_registrar_email_sin_usuario(usuario):
    registro = registrar(
        Bitacora.Accion.LOGIN_FALLIDO,
        email=usuario.email,
    )

    assert registro.usuario is None
    assert registro.usuario_email == usuario.email


def test_registrar_sanea_claves_sensibles_en_detalle():
    registro = registrar(
        Bitacora.Accion.EDITAR,
        detalle={
            "password": "x",
            "datos": {"refresh_token": "y", "ok": 1},
        },
    )

    assert registro.detalle == {
        "password": "***",
        "datos": {"refresh_token": "***", "ok": 1},
    }


def test_registrar_no_propaga_error_de_guardado(monkeypatch):
    def crear_con_error(**kwargs):
        raise RuntimeError("fallo simulado")

    monkeypatch.setattr(Bitacora.objects, "create", crear_con_error)

    assert registrar(Bitacora.Accion.EDITAR) is None


@pytest.mark.django_db
def test_endpoint_bitacora_requiere_admin(client):
    url = reverse("auditoria-bitacora")

    assert client.get(url).status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize("rol", [Usuario.Rol.DEPORTISTA, Usuario.Rol.COORDINADOR])
def test_endpoint_bitacora_deniega_roles_no_admin(client, rol):
    solicitante = Usuario.objects.create_user(
        email=f"{rol.lower()}@uagrm.edu.bo",
        password="RolePass123!",
        nombre="Usuario",
        apellido="Rol",
        rol=rol,
    )
    client.force_authenticate(user=solicitante)

    assert client.get(reverse("auditoria-bitacora")).status_code == 403


@pytest.mark.django_db
def test_admin_consulta_bitacora_paginada(client, admin):
    client.force_authenticate(user=admin)
    registrar(Bitacora.Accion.CREAR, usuario=admin, entidad="usuario")

    respuesta = client.get(reverse("auditoria-bitacora"))

    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1
    assert len(respuesta.data["results"]) == 1
    assert respuesta.data["results"][0]["usuario"]["email"] == admin.email


@pytest.mark.django_db
def test_admin_filtra_bitacora_por_accion_resultado_y_fecha(client, admin):
    client.force_authenticate(user=admin)
    registro_ok = registrar(
        Bitacora.Accion.CREAR,
        usuario=admin,
        entidad="usuario",
        resultado=Bitacora.Resultado.OK,
    )
    registro_denegado = registrar(
        Bitacora.Accion.EDITAR,
        usuario=admin,
        entidad="usuario",
        resultado=Bitacora.Resultado.DENEGADO,
    )
    Bitacora.objects.filter(pk=registro_ok.pk).update(
        fecha=timezone.now() - timedelta(days=2)
    )
    fecha_inicio = (timezone.now() - timedelta(days=1)).isoformat()
    fecha_fin = (timezone.now() + timedelta(minutes=1)).isoformat()
    url = reverse("auditoria-bitacora")

    por_accion = client.get(url, {"accion": Bitacora.Accion.EDITAR})
    por_resultado = client.get(url, {"resultado": Bitacora.Resultado.DENEGADO})
    por_rango = client.get(
        url,
        {"fecha__gte": fecha_inicio, "fecha__lte": fecha_fin},
    )

    assert por_accion.data["count"] == 1
    assert por_resultado.data["count"] == 1
    assert por_rango.data["count"] == 1
    assert por_rango.data["results"][0]["id"] == registro_denegado.pk


@pytest.mark.django_db
def test_admin_busca_bitacora_por_usuario_email(client, admin):
    client.force_authenticate(user=admin)
    registrar(
        Bitacora.Accion.LOGIN_FALLIDO,
        email="persona-no-registrada@uagrm.edu.bo",
    )

    respuesta = client.get(
        reverse("auditoria-bitacora"),
        {"search": "persona-no-registrada@uagrm.edu.bo"},
    )

    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "metodo",
    ["post", "put", "delete"],
)
def test_endpoint_bitacora_es_solo_lectura(client, admin, metodo):
    client.force_authenticate(user=admin)
    respuesta = getattr(client, metodo)(reverse("auditoria-bitacora"), {}, format="json")

    assert respuesta.status_code == 405
