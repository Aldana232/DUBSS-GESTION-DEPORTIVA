"""Comandos del primer inicio en producción: catálogos base y primer superadministrador."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.deportes.models import Categoria, Deporte, Equipo, Facultad
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
CLAVE = "UnaClaveMuyLarga2026!"


def crear_admin(email="primer@uagrm.edu.bo", **extra):
    out = StringIO()
    call_command("crear_superadmin", email=email, nombre=extra.get("nombre", "Ana"), apellido=extra.get("apellido", "Pérez"), stdout=out)
    return out.getvalue()


# ─── crear_superadmin ─────────────────────────────────────────────────────────

def test_crea_el_superadministrador_con_rol_y_permisos(monkeypatch):
    monkeypatch.setenv("DUBSS_ADMIN_PASSWORD", CLAVE)
    salida = crear_admin()
    u = Usuario.objects.get(email="primer@uagrm.edu.bo")
    assert "creado" in salida
    assert u.rol == "SUPERADMIN" and u.is_staff and u.is_superuser and u.is_active
    assert u.check_password(CLAVE) and u.nombre == "Ana" and u.apellido == "Pérez"


def test_es_idempotente_y_no_toca_una_cuenta_existente(monkeypatch):
    monkeypatch.setenv("DUBSS_ADMIN_PASSWORD", CLAVE)
    crear_admin()
    monkeypatch.setenv("DUBSS_ADMIN_PASSWORD", "OtraClaveDistinta2026!")
    salida = crear_admin("PRIMER@uagrm.edu.bo")             # mayúsculas: es el mismo correo
    assert "no se cambió nada" in salida
    assert Usuario.objects.count() == 1 and Usuario.objects.get().check_password(CLAVE)


@pytest.mark.parametrize("clave", ["corta1!", "12345678", "password", "qwertyuiop"])
def test_rechaza_contrasenas_inseguras(monkeypatch, clave):
    monkeypatch.setenv("DUBSS_ADMIN_PASSWORD", clave)
    with pytest.raises(CommandError, match="no es segura"):
        crear_admin()
    assert not Usuario.objects.exists()


def test_rechaza_un_correo_invalido(monkeypatch):
    monkeypatch.setenv("DUBSS_ADMIN_PASSWORD", CLAVE)
    with pytest.raises(CommandError, match="no es un correo válido"):
        crear_admin("no-es-un-correo")


def test_sin_variable_pide_la_contrasena_por_teclado(monkeypatch):
    monkeypatch.delenv("DUBSS_ADMIN_PASSWORD", raising=False)
    respuestas = iter([CLAVE, CLAVE])
    monkeypatch.setattr("getpass.getpass", lambda *_: next(respuestas))
    crear_admin()
    assert Usuario.objects.get().check_password(CLAVE)


def test_si_las_dos_contrasenas_no_coinciden_no_crea_nada(monkeypatch):
    monkeypatch.delenv("DUBSS_ADMIN_PASSWORD", raising=False)
    respuestas = iter([CLAVE, "OtraDistinta2026!"])
    monkeypatch.setattr("getpass.getpass", lambda *_: next(respuestas))
    with pytest.raises(CommandError, match="no coinciden"):
        crear_admin()
    assert not Usuario.objects.exists()


# ─── cargar_catalogos ─────────────────────────────────────────────────────────

def test_carga_las_12_facultades_los_deportes_y_sus_categorias():
    call_command("cargar_catalogos", stdout=StringIO())
    assert Facultad.objects.count() == 12 and Facultad.objects.filter(sigla="FICCT").exists()
    assert set(Deporte.objects.values_list("nombre", flat=True)) == {"Fútbol", "Futsal", "Voleibol", "Baloncesto"}
    assert Categoria.objects.count() == 8
    futbol = Categoria.objects.get(nombre="Fútbol Damas")
    assert futbol.genero == "DAMAS" and futbol.deporte.cantidad_jugadores == 11


def test_no_crea_datos_de_ejemplo_ni_usuarios():
    call_command("cargar_catalogos", stdout=StringIO())
    assert not Usuario.objects.exists() and not Equipo.objects.exists()


def test_cargar_catalogos_es_idempotente_y_respeta_lo_que_ya_editaste():
    call_command("cargar_catalogos", stdout=StringIO())
    Deporte.objects.filter(nombre="Futsal").update(cantidad_jugadores=6, descripcion="Editado por el administrador")
    salida = StringIO()
    call_command("cargar_catalogos", stdout=salida)
    assert Facultad.objects.count() == 12 and Deporte.objects.count() == 4 and Categoria.objects.count() == 8
    assert "Nuevos: 0 facultades, 0 deportes, 0 categorías" in salida.getvalue()
    assert Deporte.objects.get(nombre="Futsal").descripcion == "Editado por el administrador"
