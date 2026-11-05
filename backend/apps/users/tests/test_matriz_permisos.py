"""F2-07 — Matriz de permisos endpoint × rol (docs/PLAN_FASES_DUBSS.md, Fase 2).

Cada fila verifica el código HTTP que cada rol (incluido el anónimo y el rol
reservado JUGADOR) debe recibir. Las escrituras se envían con cuerpo vacío:
un 400 significa "pasó la capa de permisos y falló la validación".
"""
import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.deportes.models import Facultad
from apps.users.models import Usuario


pytestmark = pytest.mark.django_db

ROLES = ["anonimo", "jugador", "delegado", "organizador", "admin", "superadmin"]


def _fila(anonimo, jugador, delegado, organizador, admin, superadmin=None):
    return dict(zip(
        ROLES,
        [anonimo, jugador, delegado, organizador, admin,
         admin if superadmin is None else superadmin],
    ))


# (método, ruta, esperado por rol)
MATRIZ = [
    # Usuarios y roles (RF2) / perfil propio (RF20)
    ("GET", "/api/v1/usuarios/", _fila(401, 403, 403, 403, 200)),
    ("POST", "/api/v1/auth/registro/", _fila(401, 403, 403, 403, 400)),
    ("GET", "/api/v1/usuarios/perfil/", _fila(401, 200, 200, 200, 200)),
    ("GET", "/api/v1/me/", _fila(401, 200, 200, 200, 200)),
    ("GET", "/api/v1/mi-equipo/", _fila(401, 403, 200, 403, 403)),
    ("GET", "/api/v1/mis-quejas/", _fila(401, 403, 200, 403, 403)),
    # Bitácora (RF18)
    ("GET", "/api/v1/auditoria/bitacora/", _fila(401, 403, 403, 403, 200)),
    # Catálogos (RF3–RF5): admin CRUD, organizador lee, delegado sin acceso
    ("GET", "/api/v1/deportes/deportes/", _fila(401, 403, 403, 200, 200)),
    ("POST", "/api/v1/deportes/deportes/", _fila(401, 403, 403, 403, 400)),
    ("GET", "/api/v1/deportes/categorias/", _fila(401, 403, 403, 200, 200)),
    ("POST", "/api/v1/deportes/categorias/", _fila(401, 403, 403, 403, 400)),
    ("GET", "/api/v1/deportes/facultades/", _fila(401, 403, 403, 200, 200)),
    ("GET", "/api/v1/instalaciones/instalaciones/", _fila(401, 403, 403, 200, 200)),
    ("POST", "/api/v1/instalaciones/instalaciones/", _fila(401, 403, 403, 403, 400)),
    ("GET", "/api/v1/instalaciones/canchas/", _fila(401, 403, 403, 200, 200)),
    ("GET", "/api/v1/instalaciones/bloqueos/", _fila(401, 403, 403, 200, 200)),
    ("GET", "/api/v1/instalaciones/horarios/", _fila(401, 403, 403, 200, 200)),
    # Equipos, fichas e inscripciones (RF6–RF8)
    ("GET", "/api/v1/deportes/equipos/", _fila(401, 403, 200, 200, 200)),
    ("GET", "/api/v1/deportes/jugadores/", _fila(401, 403, 200, 200, 200)),
    ("GET", "/api/v1/deportes/inscripciones/", _fila(401, 403, 200, 200, 200)),
    ("POST", "/api/v1/deportes/inscripciones/", _fila(401, 403, 400, 403, 400)),
    # Campeonatos, fixture y tabla (RF9–RF13): lectura pública
    ("GET", "/api/v1/deportes/campeonatos/", _fila(200, 200, 200, 200, 200)),
    ("POST", "/api/v1/deportes/campeonatos/", _fila(401, 403, 403, 400, 400)),
    ("GET", "/api/v1/fixture/partidos/", _fila(200, 200, 200, 200, 200)),
    ("POST", "/api/v1/fixture/partidos/", _fila(401, 403, 403, 400, 400)),
    ("POST", "/api/v1/fixture/generar/", _fila(401, 403, 403, 400, 400)),
    ("GET", "/api/v1/fixture/tabla-posiciones/", _fila(400, 400, 400, 400, 400)),
    # Fase 3: estados, inscripciones, resultados e historial
    ("PATCH", "/api/v1/deportes/campeonatos/999999/estado/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/deportes/campeonatos/999999/historial/", _fila(404, 404, 404, 404, 404)),
    ("GET", "/api/v1/deportes/inscripciones/999999/elegibilidad/", _fila(401, 403, 404, 404, 404)),
    # Fase 5: estadísticas públicas y reportes por equipo/jugador
    ("GET", "/api/v1/fixture/estadisticas/", _fila(400, 400, 400, 400, 400)),
    ("GET", "/api/v1/fixture/estadisticas/?campeonato=999999", _fila(404, 404, 404, 404, 404)),
    ("GET", "/api/v1/reportes/equipo/999999/pdf/", _fila(401, 403, 403, 404, 404)),
    # Fase 6: facultad, notificaciones, asistente por voz e IA
    ("GET", "/api/v1/reportes/facultad/999999/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/reportes/facultad/999999/pdf/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/reportes/facultad/999999/excel/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/notificaciones/canales/", _fila(401, 403, 403, 200, 200)),
    ("POST", "/api/v1/notificaciones/enviar/", _fila(401, 403, 403, 400, 400)),
    ("GET", "/api/v1/asistente/estado/", _fila(401, 403, 403, 200, 200)),
    ("POST", "/api/v1/asistente/interpretar/", _fila(401, 403, 403, 400, 400)),
    ("POST", "/api/v1/asistente/ejecutar/", _fila(401, 403, 403, 400, 400)),
    ("POST", "/api/v1/asistente/transcribir/", _fila(401, 403, 403, 415, 415)),   # solo acepta multipart
    # Fase 7-C: niveles de equipos, atipicos y panel del jugador
    ("POST", "/api/v1/ml/cabezas-de-serie/", _fila(401, 403, 403, 400, 400)),
    ("GET", "/api/v1/ml/atipicos/", _fila(401, 403, 403, 200, 200)),
    ("POST", "/api/v1/ml/atipicos/999999/revisar/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/deportes/mi-ficha/", _fila(401, 200, 403, 403, 403)),
    # Fase 7-B: planilla móvil sin conexión
    ("GET", "/api/v1/fixture/planilla/paquete/", _fila(401, 403, 403, 200, 200)),
    # Fase 7-A: agente del organizador
    ("GET", "/api/v1/agente/estado/", _fila(401, 403, 403, 200, 200)),
    ("GET", "/api/v1/agente/conversaciones/", _fila(401, 403, 403, 200, 200)),
    ("GET", "/api/v1/agente/conversaciones/999999/", _fila(401, 403, 403, 404, 404)),
    ("POST", "/api/v1/agente/mensajes/", _fila(401, 403, 403, 400, 400)),
    ("GET", "/api/v1/agente/acciones/999999/", _fila(401, 403, 403, 404, 404)),
    ("POST", "/api/v1/agente/acciones/999999/confirmar/", _fila(401, 403, 403, 404, 404)),
    ("POST", "/api/v1/agente/acciones/999999/cancelar/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/ml/entrenar/", _fila(401, 403, 403, 200, 200)),
    ("POST", "/api/v1/ml/entrenar/", _fila(401, 403, 403, 403, 400)),
    ("GET", "/api/v1/ml/recomendaciones/", _fila(401, 403, 403, 200, 200)),
    ("POST", "/api/v1/ml/riesgo-climatico/999999/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/reportes/equipo/999999/excel/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/reportes/jugador/999999/pdf/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/reportes/jugador/999999/excel/", _fila(401, 403, 403, 404, 404)),
    ("PATCH", "/api/v1/deportes/inscripciones/999999/validar/", _fila(401, 403, 403, 404, 404)),
    ("POST", "/api/v1/fixture/partidos/999999/resultado/", _fila(401, 403, 403, 404, 404)),
    ("PATCH", "/api/v1/fixture/partidos/999999/resultado/", _fila(401, 403, 403, 404, 404)),
    ("DELETE", "/api/v1/fixture/partidos/999999/resultado/", _fila(401, 403, 403, 404, 404)),
    ("POST", "/api/v1/fixture/partidos/999999/incidencia/", _fila(401, 403, 403, 404, 404)),
    ("PATCH", "/api/v1/fixture/partidos/999999/", _fila(401, 403, 403, 404, 404)),
    # Predicciones (RF15)
    ("GET", "/api/v1/ml/tablero/", _fila(401, 403, 400, 400, 400)),
    ("POST", "/api/v1/ml/tablero/", _fila(401, 403, 403, 400, 400)),
    ("POST", "/api/v1/ml/entrenar/", _fila(401, 403, 403, 403, 400)),
    # Reportes (RF16–RF17): sin acceso para delegado
    ("GET", "/api/v1/reportes/campeonato/999999/pdf/", _fila(401, 403, 403, 404, 404)),
    ("GET", "/api/v1/reportes/campeonato/999999/excel/", _fila(401, 403, 403, 404, 404)),
    # Quejas (RF21)
    ("GET", "/api/v1/quejas/quejas/", _fila(401, 403, 200, 200, 200)),
    ("POST", "/api/v1/quejas/quejas/", _fila(401, 403, 400, 403, 403)),
    # Notificaciones
    ("POST", "/api/v1/notificaciones/enviar/", _fila(401, 403, 403, 400, 400)),
]


@pytest.fixture
def clientes():
    facultad = Facultad.objects.create(nombre="Facultad matriz F2", sigla="MTRZ")
    datos = {
        "jugador": (Usuario.Rol.JUGADOR, None),
        "delegado": (Usuario.Rol.DELEGADO, facultad),
        "organizador": (Usuario.Rol.ORGANIZADOR, None),
        "admin": (Usuario.Rol.ADMIN_DUBSS, None),
        "superadmin": (Usuario.Rol.SUPERADMIN, None),
    }
    clientes = {"anonimo": APIClient()}
    for nombre, (rol, fac) in datos.items():
        usuario = Usuario.objects.create_user(
            email=f"matriz-{nombre}@example.com",
            password="PruebaSegura123!",
            nombre=nombre.capitalize(),
            apellido="Matriz",
            rol=rol,
            facultad=fac,
        )
        cliente = APIClient()
        cliente.credentials(
            HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(usuario).access_token}"
        )
        clientes[nombre] = cliente
    return clientes


@pytest.mark.parametrize("rol", ROLES)
@pytest.mark.parametrize(
    ("metodo", "ruta", "esperados"),
    MATRIZ,
    ids=[f"{m} {r}" for m, r, _ in MATRIZ],
)
def test_matriz_endpoint_por_rol(clientes, metodo, ruta, esperados, rol):
    respuesta = getattr(clientes[rol], metodo.lower())(ruta, {}, format="json")
    assert respuesta.status_code == esperados[rol], (
        f"{rol} {metodo} {ruta}: esperado {esperados[rol]}, "
        f"recibido {respuesta.status_code}"
    )


def test_perfil_json_no_permite_escalar_rol(clientes):
    respuesta = clientes["delegado"].patch(
        "/api/v1/usuarios/perfil/",
        {"rol": "SUPERADMIN", "is_active": False, "facultad": None},
        format="json",
    )
    assert respuesta.status_code == 200
    usuario = Usuario.objects.get(email="matriz-delegado@example.com")
    assert usuario.rol == Usuario.Rol.DELEGADO
    assert usuario.is_active is True
    assert usuario.facultad_id is not None
