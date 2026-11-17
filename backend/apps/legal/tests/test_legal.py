"""Aceptación de los Términos y la Política de Privacidad: evidencia, versiones y privacidad."""
import pytest
from rest_framework.test import APIClient

from apps.auditoria.models import Bitacora
from apps.fixture.tests.helpers import cliente_de, crear_usuario
from apps.legal import servicios
from apps.legal.models import AceptacionLegal
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
R = Usuario.Rol
BASE = "/api/v1/legal/"


@pytest.fixture(autouse=True)
def version(settings):
    settings.LEGAL_VERSION = "2026-11-15"
    return settings


def aceptar(c, version="2026-11-15", **extra):
    return c.post(BASE + "aceptar/", {"version": version}, format="json", **extra)


# ─── Estado ───────────────────────────────────────────────────────────────────

def test_una_cuenta_nueva_tiene_la_aceptacion_pendiente():
    u = crear_usuario(R.DELEGADO)
    r = cliente_de(u).get(BASE + "estado/")
    assert r.status_code == 200
    d = r.json()
    assert d["pendiente"] is True and d["aceptado_en"] is None and d["version"] == "2026-11-15"
    assert [x["ruta"] for x in d["documentos"]] == ["/terminos", "/privacidad"]


def test_el_flag_viaja_en_la_sesion_para_que_el_frontend_decida():
    u = crear_usuario(R.ORGANIZADOR)
    c = cliente_de(u)
    assert c.get("/api/v1/me/").json()["legal_pendiente"] is True
    aceptar(c)
    assert c.get("/api/v1/me/").json()["legal_pendiente"] is False


def test_la_version_publica_no_pide_sesion():
    r = APIClient().get(BASE + "version/")
    assert r.status_code == 200 and r.json() == {"version": "2026-11-15"}


@pytest.mark.parametrize("ruta", ["estado/", "historial/"])
def test_sin_sesion_no_hay_estado_ni_historial(ruta):
    assert APIClient().get(BASE + ruta).status_code == 401
    assert APIClient().post(BASE + "aceptar/", {"version": "2026-11-15"}, format="json").status_code == 401


# ─── Aceptar ──────────────────────────────────────────────────────────────────

def test_aceptar_guarda_los_dos_documentos_con_ip_y_navegador_y_audita():
    u = crear_usuario(R.DELEGADO)
    r = aceptar(cliente_de(u), HTTP_USER_AGENT="DUBSSApp/1.0 Android", REMOTE_ADDR="10.1.2.3")
    assert r.status_code == 201
    assert r.json()["pendiente"] is False and r.json()["aceptado_en"]
    filas = AceptacionLegal.objects.filter(usuario=u)
    assert {f.documento for f in filas} == {"TERMINOS", "PRIVACIDAD"} and {f.version for f in filas} == {"2026-11-15"}
    assert all(f.ip_origen == "10.1.2.3" and f.agente == "DUBSSApp/1.0 Android" for f in filas)
    log = Bitacora.objects.get(accion="ACEPTAR_LEGAL")
    assert log.usuario == u and log.detalle == {"version": "2026-11-15"}


def test_aceptar_dos_veces_es_idempotente_y_no_duplica_la_evidencia():
    u = crear_usuario(R.DELEGADO)
    c = cliente_de(u)
    assert aceptar(c).status_code == 201
    assert aceptar(c).status_code == 200
    assert AceptacionLegal.objects.filter(usuario=u).count() == 2
    assert Bitacora.objects.filter(accion="ACEPTAR_LEGAL").count() == 1


def test_con_una_version_distinta_a_la_vigente_se_rechaza_con_409():
    u = crear_usuario(R.DELEGADO)
    r = aceptar(cliente_de(u), version="2026-01-01")
    assert r.status_code == 409 and r.json()["version"] == "2026-11-15"
    assert not AceptacionLegal.objects.filter(usuario=u).exists()


def test_sin_enviar_la_version_es_400():
    u = crear_usuario(R.DELEGADO)
    assert cliente_de(u).post(BASE + "aceptar/", {}, format="json").status_code == 400


def test_cada_cuenta_acepta_por_si_misma():
    a, b = crear_usuario(R.DELEGADO), crear_usuario(R.DELEGADO)
    aceptar(cliente_de(a))
    assert servicios.pendiente(b) is True and servicios.pendiente(a) is False


@pytest.mark.parametrize("rol", [R.SUPERADMIN, R.ADMIN_DUBSS, R.ORGANIZADOR, R.DELEGADO, R.JUGADOR])
def test_todo_rol_con_panel_puede_aceptar(rol):
    assert aceptar(cliente_de(crear_usuario(rol))).status_code == 201


# ─── Cambio de versión ────────────────────────────────────────────────────────

def test_al_cambiar_la_version_vuelve_a_quedar_pendiente_y_se_conserva_la_evidencia_anterior(settings):
    u = crear_usuario(R.DELEGADO)
    c = cliente_de(u)
    aceptar(c)
    assert servicios.pendiente(u) is False

    settings.LEGAL_VERSION = "2027-03-01"
    assert servicios.pendiente(u) is True
    assert c.get("/api/v1/me/").json()["legal_pendiente"] is True
    assert aceptar(c, version="2026-11-15").status_code == 409            # la pantalla vieja ya no vale
    assert aceptar(c, version="2027-03-01").status_code == 201
    assert servicios.pendiente(u) is False
    assert sorted(AceptacionLegal.objects.filter(usuario=u).values_list("version", flat=True)) == ["2026-11-15"] * 2 + ["2027-03-01"] * 2


def test_aceptar_solo_un_documento_no_basta(settings):
    u = crear_usuario(R.DELEGADO)
    AceptacionLegal.objects.create(usuario=u, documento="TERMINOS", version="2026-11-15")
    assert servicios.pendiente(u) is True
    ok, _ = servicios.aceptar(u, ip=None, agente="")
    assert ok is True and servicios.pendiente(u) is False
    assert AceptacionLegal.objects.filter(usuario=u).count() == 2           # completó el que faltaba sin duplicar


# ─── Historial ────────────────────────────────────────────────────────────────

def test_el_historial_solo_muestra_lo_mio():
    a, b = crear_usuario(R.DELEGADO), crear_usuario(R.DELEGADO)
    aceptar(cliente_de(a))
    aceptar(cliente_de(b))
    r = cliente_de(a).get(BASE + "historial/")
    assert r.status_code == 200 and len(r.json()) == 2
    assert {x["documento"] for x in r.json()} == {"TERMINOS", "PRIVACIDAD"}
    assert "ip_origen" not in r.json()[0]                                  # la IP es evidencia interna, no se devuelve


def test_la_evidencia_no_se_borra_desde_el_admin(rf, django_user_model):
    from django.contrib import admin as dj_admin
    ma = dj_admin.site._registry[AceptacionLegal]
    assert not ma.has_delete_permission(rf.get("/")) and not ma.has_change_permission(rf.get("/")) and not ma.has_add_permission(rf.get("/"))
