"""Tests para los helpers de roles y permisos asociados."""
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser

from apps.users.models import Usuario
from apps.users.permissions import (
    EsAdminDUBSS,
    EsArbitroOAdmin,
    EsCoordinadorOAdmin,
    EsDeportistaPropioOAdmin,
)
from apps.users.roles import (
    es_admin,
    es_arbitro,
    es_delegado,
    es_organizador,
    es_superadmin,
)


ROLES_ACTUALES = [rol for rol, _ in Usuario.Rol.choices]
CASOS_USUARIO = [
    pytest.param("none", None, False, id="none"),
    pytest.param("anonimo", None, False, id="anonimo"),
    *[
        pytest.param("rol", rol, False, id=rol.lower())
        for rol in ROLES_ACTUALES
    ],
    pytest.param("superusuario", Usuario.Rol.ADMIN_DUBSS, True, id="superusuario"),
]
CASOS_HELPERS = [
    (es_superadmin, set(), True),
    (es_admin, {Usuario.Rol.ADMIN_DUBSS}, True),
    (es_organizador, {Usuario.Rol.COORDINADOR}, False),
    (es_delegado, {Usuario.Rol.COORDINADOR}, False),
    (es_arbitro, {Usuario.Rol.ARBITRO}, False),
]
CASOS_PERMISOS = [
    (EsAdminDUBSS, {Usuario.Rol.ADMIN_DUBSS}, True),
    (EsCoordinadorOAdmin, {Usuario.Rol.ADMIN_DUBSS, Usuario.Rol.COORDINADOR}, True),
    (EsArbitroOAdmin, {Usuario.Rol.ADMIN_DUBSS, Usuario.Rol.ARBITRO}, True),
]


def crear_usuario(tipo, rol, superusuario):
    if tipo == "none":
        return None
    if tipo == "anonimo":
        return AnonymousUser()
    return Usuario(
        email=f"{rol.lower()}@uagrm.edu.bo",
        rol=rol,
        is_superuser=superusuario,
    )


@pytest.mark.parametrize(("helper", "roles_permitidos", "permite_superusuario"), CASOS_HELPERS)
@pytest.mark.parametrize(("tipo", "rol", "superusuario"), CASOS_USUARIO)
def test_helpers_de_rol(helper, roles_permitidos, permite_superusuario, tipo, rol, superusuario):
    user = crear_usuario(tipo, rol, superusuario)

    esperado = (
        permite_superusuario
        if superusuario
        else tipo == "rol" and rol in roles_permitidos
    )
    assert helper(user) is esperado


@pytest.mark.parametrize(("permiso", "roles_permitidos", "permite_superusuario"), CASOS_PERMISOS)
@pytest.mark.parametrize(("tipo", "rol", "superusuario"), CASOS_USUARIO)
def test_permisos_por_rol(permiso, roles_permitidos, permite_superusuario, tipo, rol, superusuario):
    user = crear_usuario(tipo, rol, superusuario)
    request = SimpleNamespace(user=user)

    esperado = (
        permite_superusuario
        if superusuario
        else tipo == "rol" and rol in roles_permitidos
    )
    assert permiso().has_permission(request, None) is esperado


@pytest.mark.parametrize(("tipo", "rol", "superusuario"), CASOS_USUARIO)
def test_permiso_deportista_propio_o_admin(tipo, rol, superusuario):
    user = crear_usuario(tipo, rol, superusuario)
    request = SimpleNamespace(user=user)

    assert EsDeportistaPropioOAdmin().has_object_permission(request, None, object()) is (
        (tipo == "rol" and rol == Usuario.Rol.ADMIN_DUBSS) or superusuario
    )
    if user is not None and getattr(user, "is_authenticated", False):
        assert EsDeportistaPropioOAdmin().has_object_permission(request, None, user)
