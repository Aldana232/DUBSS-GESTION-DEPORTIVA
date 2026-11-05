"""Tests de los helpers y permisos de los roles finales."""
from types import SimpleNamespace

import pytest
from django.contrib.auth.models import AnonymousUser
from django.urls import reverse
from rest_framework.test import APIClient

from apps.users.models import Usuario
from apps.users.permissions import (
    EsAdmin,
    EsAdminOrganizadorODelegado,
    EsAdminUOrganizador,
    EsSuperadmin,
    EsUsuarioOperativo,
)
from apps.users.roles import (
    es_admin,
    es_delegado,
    es_organizador,
    es_superadmin,
)


ROLES = [rol for rol, _ in Usuario.Rol.choices]
CASOS_USUARIO = [
    pytest.param("none", None, False, id="none"),
    pytest.param("anonimo", None, False, id="anonimo"),
    *[
        pytest.param("rol", rol, False, id=rol.lower())
        for rol in ROLES
    ],
    pytest.param("superusuario", Usuario.Rol.ADMIN_DUBSS, True, id="superusuario"),
]
CASOS_HELPERS = [
    (es_superadmin, {Usuario.Rol.SUPERADMIN}, True),
    (es_admin, {Usuario.Rol.ADMIN_DUBSS, Usuario.Rol.SUPERADMIN}, True),
    (es_organizador, {Usuario.Rol.ORGANIZADOR}, False),
    (es_delegado, {Usuario.Rol.DELEGADO}, False),
]
CASOS_PERMISOS = [
    (EsSuperadmin, {Usuario.Rol.SUPERADMIN}, True),
    (EsAdmin, {Usuario.Rol.ADMIN_DUBSS, Usuario.Rol.SUPERADMIN}, True),
    (
        EsAdminUOrganizador,
        {Usuario.Rol.ADMIN_DUBSS, Usuario.Rol.SUPERADMIN, Usuario.Rol.ORGANIZADOR},
        True,
    ),
    (
        EsAdminOrganizadorODelegado,
        {
            Usuario.Rol.ADMIN_DUBSS,
            Usuario.Rol.SUPERADMIN,
            Usuario.Rol.ORGANIZADOR,
            Usuario.Rol.DELEGADO,
        },
        True,
    ),
    (
        EsUsuarioOperativo,
        {
            Usuario.Rol.ADMIN_DUBSS,
            Usuario.Rol.SUPERADMIN,
            Usuario.Rol.ORGANIZADOR,
            Usuario.Rol.DELEGADO,
        },
        True,
    ),
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


@pytest.mark.parametrize(
    ("helper", "roles_permitidos", "permite_superusuario"),
    CASOS_HELPERS,
)
@pytest.mark.parametrize(("tipo", "rol", "superusuario"), CASOS_USUARIO)
def test_helpers_de_rol(helper, roles_permitidos, permite_superusuario, tipo, rol, superusuario):
    user = crear_usuario(tipo, rol, superusuario)
    esperado = (
        permite_superusuario
        if superusuario
        else tipo == "rol" and rol in roles_permitidos
    )

    assert helper(user) is esperado


@pytest.mark.parametrize(
    ("permiso", "roles_permitidos", "permite_superusuario"),
    CASOS_PERMISOS,
)
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


@pytest.mark.django_db
def test_admin_no_puede_crear_cuenta_superadmin():
    admin = Usuario.objects.create_user(
        email="admin-roles@uagrm.edu.bo",
        password="AdminPass123!",
        nombre="Admin",
        apellido="Roles",
        rol=Usuario.Rol.ADMIN_DUBSS,
    )
    client = APIClient()
    client.force_authenticate(user=admin)

    response = client.post(
        reverse("auth-registro"),
        {
            "email": "superadmin-nuevo@uagrm.edu.bo",
            "nombre": "Nuevo",
            "apellido": "Superadmin",
            "rol": Usuario.Rol.SUPERADMIN,
            "password": "NuevaSegura456!",
            "password2": "NuevaSegura456!",
        },
        format="json",
    )

    assert response.status_code == 403
    assert not Usuario.objects.filter(email="superadmin-nuevo@uagrm.edu.bo").exists()


@pytest.mark.django_db
def test_superadmin_puede_crear_cuenta_superadmin():
    superadmin = Usuario.objects.create_superuser(
        email="superadmin-roles@uagrm.edu.bo",
        password="SuperAdminPass123!",
        nombre="Super",
        apellido="Admin",
    )
    assert superadmin.rol == Usuario.Rol.SUPERADMIN
    client = APIClient()
    client.force_authenticate(user=superadmin)

    response = client.post(
        reverse("auth-registro"),
        {
            "email": "superadmin-nuevo@uagrm.edu.bo",
            "nombre": "Nuevo",
            "apellido": "Superadmin",
            "rol": Usuario.Rol.SUPERADMIN,
            "password": "NuevaSegura456!",
            "password2": "NuevaSegura456!",
        },
        format="json",
    )

    assert response.status_code == 201
    creado = Usuario.objects.get(email="superadmin-nuevo@uagrm.edu.bo")
    assert creado.rol == Usuario.Rol.SUPERADMIN
    assert not creado.is_superuser


@pytest.mark.django_db
def test_admin_no_puede_editar_ni_dar_de_baja_a_superadmin():
    admin = Usuario.objects.create_user(
        email="admin-roles@uagrm.edu.bo",
        password="AdminPass123!",
        nombre="Admin",
        apellido="Roles",
        rol=Usuario.Rol.ADMIN_DUBSS,
    )
    superadmin = Usuario.objects.create_superuser(
        email="superadmin-roles@uagrm.edu.bo",
        password="SuperAdminPass123!",
        nombre="Super",
        apellido="Admin",
    )
    client = APIClient()
    client.force_authenticate(user=admin)

    response_edicion = client.patch(
        reverse("usuario-detalle", kwargs={"pk": superadmin.pk}),
        {"nombre": "Alterado"},
        format="multipart",
    )
    response_baja = client.delete(
        reverse("usuario-detalle", kwargs={"pk": superadmin.pk})
    )

    superadmin.refresh_from_db()
    assert response_edicion.status_code == 403
    assert response_baja.status_code == 403
    assert superadmin.nombre == "Super"
    assert superadmin.is_active


@pytest.mark.django_db
def test_jugador_puede_gestionar_solo_su_propia_cuenta():
    """F7-10: el jugador con cuenta ve y edita SU cuenta (sin poder cambiarse el rol) y cambia su contraseña."""
    jugador = Usuario.objects.create_user(email="jugador-propio@uagrm.edu.bo", password="JugadorPass123!", nombre="Jugador", apellido="Propio",
                                          rol=Usuario.Rol.JUGADOR)
    client = APIClient()
    client.force_authenticate(user=jugador)
    assert client.get(reverse("usuario-me")).data["rol"] == "JUGADOR"
    r = client.patch(reverse("usuario-perfil"), {"telefono": "71234567", "rol": "SUPERADMIN"}, format="json")
    jugador.refresh_from_db()
    assert r.status_code == 200 and jugador.telefono == "71234567" and jugador.rol == Usuario.Rol.JUGADOR       # el rol no se puede escalar
    mala = client.post(reverse("auth-cambio-password"), {"password_actual": "JugadorPass123!", "password_nuevo": "corta", "password_nuevo2": "corta"}, format="json")
    assert mala.status_code == 400                                                    # permitido, pero valida la contraseña nueva
    assert client.post(reverse("auth-logout"), {"refresh": "x"}, format="json").status_code in (200, 400, 205)


@pytest.mark.django_db
def test_jugador_no_puede_usar_endpoints_de_escritura():
    jugador = Usuario.objects.create_user(
        email="jugador-sin-permisos@uagrm.edu.bo",
        password="JugadorPass123!",
        nombre="Jugador",
        apellido="Reservado",
        rol=Usuario.Rol.JUGADOR,
    )
    client = APIClient()
    client.force_authenticate(user=jugador)
    peticiones = [
        ("post", reverse("auth-registro")),
        ("post", reverse("usuario-fcm-token")),
        ("patch", reverse("usuario-detalle", kwargs={"pk": 999999})),
        ("delete", reverse("usuario-detalle", kwargs={"pk": 999999})),
        ("post", reverse("deporte-list")),
        ("post", reverse("categoria-list")),
        ("post", reverse("campeonato-list")),
        ("patch", reverse("campeonato-cambiar-estado", kwargs={"pk": 999999})),
        ("post", reverse("equipo-list")),
        ("post", reverse("jugador-list")),
        ("post", reverse("instalacion-list")),
        ("post", reverse("cancha-list")),
        ("post", reverse("bloqueo-list")),
        ("post", reverse("partido-list")),
        ("post", reverse("partido-registrar-resultado", kwargs={"pk": 999999})),
        ("post", reverse("partido-registrar-incidencia", kwargs={"pk": 999999})),
        ("post", reverse("fixture-generar")),
        ("post", reverse("notificacion-enviar")),
        ("post", reverse("ml-entrenar")),
    ]

    for metodo, url in peticiones:
        response = getattr(client, metodo)(url, {}, format="json")
        assert response.status_code == 403, f"{metodo.upper()} {url}: {response.status_code}"
