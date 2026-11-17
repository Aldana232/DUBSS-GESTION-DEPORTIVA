"""AuditaCrudMixin: altas, ediciones y bajas quedan en la bitácora con el mismo texto de siempre."""
import pytest

from apps.auditoria.models import Bitacora
from apps.fixture.tests.helpers import cliente_de, crear_equipo, crear_jugador, crear_usuario
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
A = Bitacora.Accion


def _log(accion, modulo):
    return Bitacora.objects.filter(accion=accion, modulo=modulo)


def test_equipo_editar_y_eliminar_se_auditan():
    admin = crear_usuario(Usuario.Rol.ADMIN_DUBSS)
    equipo = crear_equipo("Auditados")
    c = cliente_de(admin)

    assert c.patch(f"/api/v1/deportes/equipos/{equipo.pk}/", {"nombre": "Auditados B"}, format="json").status_code == 200
    log = _log(A.EDITAR, "equipo").get()
    assert log.descripcion == "Equipo actualizado." and log.objeto_id == equipo.pk and log.usuario == admin

    assert c.delete(f"/api/v1/deportes/equipos/{equipo.pk}/").status_code == 204
    assert _log(A.ELIMINAR, "equipo").get().descripcion == "Equipo eliminado."


def test_delegado_crea_equipo_con_su_facultad_y_queda_auditado():
    facultad_equipo = crear_equipo("Base")
    delegado = facultad_equipo.delegado
    r = cliente_de(delegado).post("/api/v1/deportes/equipos/", {"nombre": "Nuevo del delegado", "facultad": delegado.facultad_id}, format="json")
    assert r.status_code == 201, r.content
    from apps.deportes.models import Equipo
    nuevo = Equipo.objects.get(nombre="Nuevo del delegado")
    assert nuevo.delegado == delegado and nuevo.facultad == delegado.facultad
    assert _log(A.CREAR, "equipo").filter(objeto_id=nuevo.pk).exists()


def test_ficha_de_jugador_editar_y_eliminar_se_auditan():
    equipo = crear_equipo("Con ficha")
    ficha = crear_jugador(equipo, 7)
    c = cliente_de(equipo.delegado)

    assert c.patch(f"/api/v1/deportes/jugadores/{ficha.pk}/", {"numero_camiseta": 9}, format="json").status_code == 200
    assert _log(A.EDITAR, "ficha_jugador").get().descripcion == "Ficha de jugador actualizada."
    assert c.delete(f"/api/v1/deportes/jugadores/{ficha.pk}/").status_code == 204
    assert _log(A.ELIMINAR, "ficha_jugador").get().descripcion == "Ficha de jugador eliminada."


def test_inscripcion_y_alta_de_usuario_solo_auditan_el_alta_como_antes():
    admin = crear_usuario(Usuario.Rol.ADMIN_DUBSS)
    r = cliente_de(admin).post("/api/v1/usuarios/", {
        "email": "nuevo@example.com", "nombre": "Nuevo", "apellido": "Usuario", "rol": "ORGANIZADOR",
        "password": "ClaveMuySegura2026!", "password2": "ClaveMuySegura2026!",
    }, format="json")
    assert r.status_code == 201, r.content
    assert _log(A.CREAR, "usuario").get().descripcion == "Cuenta creada por un administrador."


def test_un_recurso_sin_texto_no_audita(rf):
    """Si el mixin no tiene texto para esa operación, no registra nada (comportamiento de Inscripción/Usuarios)."""
    from apps.auditoria.mixins import AuditaCrudMixin

    class Falso(AuditaCrudMixin):
        auditoria_modulo = "x"
        auditoria_textos = {"crear": "hecho"}
        request = rf.get("/")

    class Objeto:
        pk = 1
    antes = Bitacora.objects.count()
    Falso()._auditar(A.EDITAR, "editar", Objeto())
    assert Bitacora.objects.count() == antes
