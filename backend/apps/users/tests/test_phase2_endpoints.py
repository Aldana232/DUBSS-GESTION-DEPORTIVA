import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.deportes.models import Facultad
from apps.users.models import Usuario


pytestmark = pytest.mark.django_db


@pytest.fixture
def cuentas():
    facultad = Facultad.objects.create(
        nombre="Facultad endpoints F2",
        sigla="F2EP",
    )
    return {
        "admin": Usuario.objects.create_user(
            email="admin-f2-endpoints@example.com",
            password="PruebaSegura123!",
            nombre="Ana",
            apellido="Admin",
            rol=Usuario.Rol.ADMIN_DUBSS,
        ),
        "organizador": Usuario.objects.create_user(
            email="organizador-f2-endpoints@example.com",
            password="PruebaSegura123!",
            nombre="Olga",
            apellido="Organizadora",
            rol=Usuario.Rol.ORGANIZADOR,
        ),
        "delegado": Usuario.objects.create_user(
            email="delegado-f2-endpoints@example.com",
            password="PruebaSegura123!",
            nombre="Diego",
            apellido="Delegado",
            rol=Usuario.Rol.DELEGADO,
            facultad=facultad,
        ),
        "jugador": Usuario.objects.create_user(
            email="jugador-f2-endpoints@example.com",
            password="PruebaSegura123!",
            nombre="Juan",
            apellido="Jugador",
            rol=Usuario.Rol.JUGADOR,
        ),
    }


@pytest.mark.parametrize(
    ("cuenta", "esperado"),
    [
        ("anonimo", 401),
        ("jugador", 403),
        ("delegado", 403),
        ("organizador", 403),
        ("admin", 200),
    ],
)
def test_matriz_acceso_a_gestion_de_usuarios(cuentas, cuenta, esperado):
    client = APIClient()
    if cuenta != "anonimo":
        client.force_authenticate(cuentas[cuenta])

    respuesta = client.get(reverse("usuario-lista"))

    assert respuesta.status_code == esperado


@pytest.mark.parametrize(
    ("cuenta", "esperado"),
    [
        ("anonimo", 401),
        ("jugador", 403),
        ("delegado", 200),
        ("organizador", 403),
        ("admin", 403),
    ],
)
def test_matriz_acceso_a_mis_equipos(cuentas, cuenta, esperado):
    client = APIClient()
    if cuenta != "anonimo":
        client.force_authenticate(cuentas[cuenta])

    respuesta = client.get(reverse("usuario-mi-equipo"))

    assert respuesta.status_code == esperado


@pytest.mark.parametrize(
    ("cuenta", "esperado"),
    [
        ("anonimo", 401),
        ("jugador", 403),
        ("delegado", 200),
        ("organizador", 403),
        ("admin", 403),
    ],
)
def test_matriz_acceso_a_mis_quejas(cuentas, cuenta, esperado):
    client = APIClient()
    if cuenta != "anonimo":
        client.force_authenticate(cuentas[cuenta])

    respuesta = client.get(reverse("mis-quejas"))

    assert respuesta.status_code == esperado


@pytest.mark.parametrize(
    ("cuenta", "esperado"),
    [
        ("anonimo", 401),
        ("jugador", 403),
        ("delegado", 403),
        ("organizador", 404),
        ("admin", 404),
    ],
)
def test_reportes_no_son_publicos(cuentas, cuenta, esperado):
    client = APIClient()
    if cuenta != "anonimo":
        client.force_authenticate(cuentas[cuenta])

    respuesta = client.get(
        reverse("reporte-pdf", kwargs={"campeonato_id": 999999})
    )

    assert respuesta.status_code == esperado


@pytest.mark.parametrize(
    ("cuenta", "esperado"),
    [
        ("anonimo", 200),
        ("jugador", 200),
        ("delegado", 200),
        ("organizador", 200),
        ("admin", 200),
    ],
)
def test_fixture_publico_en_lectura(cuentas, cuenta, esperado):
    client = APIClient()
    if cuenta != "anonimo":
        client.force_authenticate(cuentas[cuenta])

    respuesta = client.get(reverse("partido-list"))

    assert respuesta.status_code == esperado


def test_me_devuelve_rol_y_facultad_sin_actualizar_ultimo_acceso(cuentas):
    usuario = cuentas["delegado"]
    ultimo_acceso = usuario.ultimo_acceso
    client = APIClient()
    client.force_authenticate(usuario)

    respuesta = client.get(reverse("usuario-me"))

    usuario.refresh_from_db()
    assert respuesta.status_code == 200
    assert respuesta.data["rol"] == Usuario.Rol.DELEGADO
    assert respuesta.data["facultad"] == usuario.facultad_id
    assert usuario.ultimo_acceso == ultimo_acceso


def test_administrador_crea_cuenta_por_endpoint_usuarios(cuentas):
    client = APIClient()
    client.force_authenticate(cuentas["admin"])

    respuesta = client.post(
        reverse("usuario-lista"),
        {
            "email": "alta-f2@example.com",
            "nombre": "Alta",
            "apellido": "Fase Dos",
            "rol": Usuario.Rol.ORGANIZADOR,
            "password": "CuentaSegura123!",
            "password2": "CuentaSegura123!",
        },
        format="json",
    )

    assert respuesta.status_code == 201
    assert Usuario.objects.get(email="alta-f2@example.com").rol == Usuario.Rol.ORGANIZADOR


def test_admin_restablece_password_y_bitacora_la_accion(cuentas):
    from apps.auditoria.models import Bitacora

    client = APIClient()
    usuario = cuentas["delegado"]
    token_anterior = str(RefreshToken.for_user(usuario))
    client.force_authenticate(cuentas["admin"])

    respuesta = client.post(
        reverse("usuario-restablecer-password", kwargs={"pk": usuario.pk}),
        {"password_nuevo": "NuevaClaveSegura456!"},
        format="json",
    )

    usuario.refresh_from_db()
    assert respuesta.status_code == 200
    assert usuario.check_password("NuevaClaveSegura456!")
    respuesta_refresh = APIClient().post(
        reverse("auth-refresh"),
        {"refresh": token_anterior},
        format="json",
    )
    assert respuesta_refresh.status_code == 401
    assert Bitacora.objects.filter(
        accion=Bitacora.Accion.CAMBIO_PASSWORD,
        objeto_id=usuario.pk,
    ).exists()


def test_dos_cuentas_sin_ci_no_chocan_por_unicidad(cuentas):
    cliente = APIClient()
    cliente.force_authenticate(cuentas["admin"])
    for n in (1, 2):
        r = cliente.post(
            reverse("usuario-lista"),
            {
                "email": f"sin-ci-{n}@example.com", "nombre": "Sin", "apellido": "Carnet",
                "ci": "", "rol": "ORGANIZADOR",
                "password": "ClaveSegura#2026", "password2": "ClaveSegura#2026",
            },
            format="json",
        )
        assert r.status_code == 201, r.data
    assert Usuario.objects.filter(email__startswith="sin-ci-", ci__isnull=True).count() == 2


def test_ci_duplicado_devuelve_400_no_500(cuentas):
    cliente = APIClient()
    cliente.force_authenticate(cuentas["admin"])
    datos = {
        "nombre": "Con", "apellido": "Carnet", "ci": "1234567", "rol": "ORGANIZADOR",
        "password": "ClaveSegura#2026", "password2": "ClaveSegura#2026",
    }
    assert cliente.post(reverse("usuario-lista"), {**datos, "email": "ci1@example.com"}, format="json").status_code == 201
    r = cliente.post(reverse("usuario-lista"), {**datos, "email": "ci2@example.com"}, format="json")
    assert r.status_code == 400 and "ci" in r.data
