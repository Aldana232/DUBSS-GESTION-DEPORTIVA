"""seed_realista — datos de ejemplo de la UAGRM: completos, coherentes y repetibles."""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.deportes.models import Campeonato, Equipo, Facultad, FichaJugador, Inscripcion
from apps.fixture.models import Partido, PosicionHistorial, TablaPosiciones
from apps.fixture.tests.helpers import hay_solapes
from apps.quejas.models import Queja
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
PASSWORD = "Dubss2026!"


@pytest.fixture(scope="module")
def sembrado(django_db_setup, django_db_blocker):
    """
    El seed tarda unos segundos: se ejecuta una sola vez para todas las comprobaciones de solo lectura. Todo ocurre dentro de
    una transacción que se REVIERTE al terminar el módulo, así no deja datos que contaminen otras pruebas.
    """
    from django.conf import settings
    from django.db import transaction
    settings.DEBUG = True
    with django_db_blocker.unblock():
        bloque = transaction.atomic()
        bloque.__enter__()
        try:
            ajeno = Usuario.objects.create_user(email="programador@gmail.com", password="Otra123456!", nombre="Programa", apellido="Dor", rol="SUPERADMIN")
            salida = StringIO()
            call_command("seed_realista", "--sin-ia", stdout=salida)
            yield {"salida": salida.getvalue(), "ajeno": ajeno}
        finally:
            transaction.set_rollback(True)
            bloque.__exit__(None, None, None)
            settings.DEBUG = False


def test_crea_la_estructura_de_la_uagrm(sembrado):
    assert Facultad.objects.count() == 12 and Facultad.objects.filter(sigla="FICCT").exists()
    assert Equipo.objects.count() == 44 and FichaJugador.objects.count() > 500
    assert Campeonato.objects.count() == 6
    estados = dict(Campeonato.objects.values_list("nombre", "estado"))
    assert estados["Interfacultades de Fútbol Varones 2025"] == "FINALIZADO"
    assert estados["Interfacultades de Fútbol Varones 2026"] == "EN_CURSO"
    assert estados["Copa Relámpago de Futsal Varones 2026"] == "INSCRIPCION_CERRADA"
    assert estados["Copa de Voleibol Damas 2026"] == "INSCRIPCIONES"
    assert estados["Torneo Interfacultades de Baloncesto Varones 2026"] == "PLANIFICACION"


def test_todas_las_cuentas_entran_con_la_contrasena_de_ejemplo_y_cada_rol_existe(sembrado, settings):
    # El seed se ejecutó con los algoritmos reales; las pruebas usan uno rápido, así que se permiten ambos.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher", "django.contrib.auth.hashers.MD5PasswordHasher"]
    roles = {u.rol for u in Usuario.objects.filter(email__endswith="@uagrm.edu.bo")}
    assert roles == {"SUPERADMIN", "ADMIN_DUBSS", "ORGANIZADOR", "DELEGADO", "JUGADOR"}
    malas = [u.email for u in Usuario.objects.filter(email__endswith="@uagrm.edu.bo") if not (u.check_password(PASSWORD) and u.is_active)]
    assert malas == []
    assert Usuario.objects.filter(rol="DELEGADO").count() == 12
    assert all(u.facultad_id for u in Usuario.objects.filter(rol="DELEGADO"))
    assert "admin@uagrm.edu.bo" in sembrado["salida"] and PASSWORD in sembrado["salida"]


def test_no_toca_las_cuentas_que_no_son_de_ejemplo(sembrado):
    assert Usuario.objects.filter(email="programador@gmail.com").exists()


def test_el_fixture_en_curso_lo_genero_el_sistema_sin_choques_y_con_historial(sembrado):
    c = Campeonato.objects.get(nombre="Interfacultades de Fútbol Varones 2026")
    partidos = list(Partido.objects.filter(campeonato=c))
    assert len(partidos) == 66 and all(p.generado_por_ml for p in partidos)
    assert hay_solapes(Partido.objects.all()) is None
    assert Partido.objects.filter(campeonato=c, estado="FINALIZADO").count() == 18          # jornadas 1 a 3
    assert Partido.objects.filter(campeonato=c, estado="PROGRAMADO", fecha_hora__gte=timezone.now() - timedelta(days=1)).exists()
    assert TablaPosiciones.objects.filter(campeonato=c).count() == 12 and PosicionHistorial.objects.filter(campeonato=c).exists()
    assert min(TablaPosiciones.objects.filter(campeonato=c).values_list("posicion", flat=True)) == 1


def test_las_temporadas_2025_estan_completas(sembrado):
    assert Partido.objects.filter(campeonato__nombre="Interfacultades de Fútbol Varones 2025", estado="FINALIZADO").count() == 66
    assert Partido.objects.filter(campeonato__nombre="Interfacultades de Futsal Varones 2025", estado="FINALIZADO").count() == 28


def test_hay_un_jugador_sancionado_y_su_cuenta(sembrado):
    sancionado = FichaJugador.objects.filter(partidos_sancion_restantes__gt=0).first()
    assert sancionado is not None and sancionado.usuario is not None and sancionado.usuario.rol == "JUGADOR"


def test_las_inscripciones_muestran_todos_los_estados(sembrado):
    estados = set(Inscripcion.objects.filter(campeonato__nombre="Copa de Voleibol Damas 2026").values_list("estado", flat=True))
    assert estados == {"APROBADA", "PENDIENTE", "RECHAZADA"}
    assert set(Queja.objects.values_list("estado", flat=True)) == {"ABIERTA", "EN_REVISION", "RESUELTA", "RECHAZADA"}


def test_se_puede_ejecutar_otra_vez_y_queda_igual(sembrado):
    antes = (Equipo.objects.count(), FichaJugador.objects.count(), Partido.objects.count(), Usuario.objects.count())
    call_command("seed_realista", "--sin-ia", stdout=StringIO())
    assert (Equipo.objects.count(), FichaJugador.objects.count(), Partido.objects.count(), Usuario.objects.count()) == antes


def test_se_niega_a_correr_fuera_de_desarrollo(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="DEBUG"):
        call_command("seed_realista")
