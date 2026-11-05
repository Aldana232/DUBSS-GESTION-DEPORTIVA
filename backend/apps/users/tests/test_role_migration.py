"""Prueba del mapeo de los roles históricos a los roles finales."""
import importlib
from types import SimpleNamespace

import pytest
from django.apps import apps
from django.db import connection

from apps.users.models import Usuario


pytestmark = pytest.mark.django_db


def test_migracion_mapea_roles_historicos_y_desactiva_jugador(capsys):
    migracion = importlib.import_module(
        "apps.users.migrations.0004_migrar_roles_finales"
    )
    superadmin_antiguo = Usuario.objects.create_user(
        email="migracion-superadmin@uagrm.edu.bo",
        password="PruebaSegura123!",
        nombre="Super",
        apellido="Antiguo",
        rol=migracion.ROL_ADMIN_DUBSS,
        is_superuser=True,
    )
    coordinador = Usuario.objects.create_user(
        email="migracion-coordinador@uagrm.edu.bo",
        password="PruebaSegura123!",
        nombre="Coordinador",
        apellido="Antiguo",
        rol=migracion.ROL_COORDINADOR,
    )
    arbitro = Usuario.objects.create_user(
        email="migracion-arbitro@uagrm.edu.bo",
        password="PruebaSegura123!",
        nombre="Arbitro",
        apellido="Antiguo",
        rol=migracion.ROL_ARBITRO,
    )
    deportista = Usuario.objects.create_user(
        email="migracion-deportista@uagrm.edu.bo",
        password="PruebaSegura123!",
        nombre="Deportista",
        apellido="Antiguo",
        rol=migracion.ROL_DEPORTISTA,
    )
    publico = Usuario.objects.create_user(
        email="migracion-publico@uagrm.edu.bo",
        password="PruebaSegura123!",
        nombre="Publico",
        apellido="Antiguo",
        rol=migracion.ROL_PUBLICO,
    )
    administrador = Usuario.objects.create_user(
        email="migracion-admin@uagrm.edu.bo",
        password="PruebaSegura123!",
        nombre="Admin",
        apellido="Conservado",
        rol=migracion.ROL_ADMIN_DUBSS,
    )

    migracion.migrar_roles(apps, SimpleNamespace(connection=connection))

    for usuario in (superadmin_antiguo, coordinador, arbitro, deportista, publico, administrador):
        usuario.refresh_from_db()

    assert superadmin_antiguo.rol == Usuario.Rol.SUPERADMIN
    assert coordinador.rol == Usuario.Rol.DELEGADO
    assert arbitro.rol == Usuario.Rol.ORGANIZADOR
    assert deportista.rol == Usuario.Rol.JUGADOR
    assert not deportista.is_active
    assert publico.rol == Usuario.Rol.JUGADOR
    assert not publico.is_active
    assert administrador.rol == Usuario.Rol.ADMIN_DUBSS

    salida = capsys.readouterr().out
    assert "is_superuser=True -> SUPERADMIN: 1" in salida
    assert "COORDINADOR -> DELEGADO: 1" in salida
    assert "ARBITRO -> ORGANIZADOR: 1" in salida
    assert "DEPORTISTA -> JUGADOR inactivo: 1" in salida
    assert "PUBLICO -> JUGADOR inactivo: 1" in salida
    assert "ADMIN_DUBSS conservados sin cambio: 1" in salida
