"""F3-08 — Incidencias y sanciones (RF14, RF8)."""
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Bitacora
from apps.deportes.models import FichaJugador, Inscripcion
from apps.deportes.services import evaluar_inscripcion
from apps.fixture.models import Incidencia, Partido
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.users.models import Usuario

from .helpers import (
    cliente_de, crear_equipo, crear_escenario, crear_jugador, crear_usuario,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def mundo():
    """Dos equipos que se enfrentan en dos partidos (ida y vuelta)."""
    esc = crear_escenario(equipos=2, canchas=1)
    esc.partidos = list(
        FixtureGenerator(esc.campeonato.pk, doble_vuelta=True).generar()
    )
    esc.ida, esc.vuelta = esc.partidos
    esc.local, esc.visitante = esc.ida.equipo_local, esc.ida.equipo_visitante
    esc.jugador = crear_jugador(esc.local, 10)
    esc.rival = crear_jugador(esc.visitante, 7)
    return esc


def incidencia(esc, partido, tipo, jugador=None, **extra):
    cuerpo = {"tipo": tipo, "minuto": 30, **extra}
    if jugador is not None:
        cuerpo["jugador"] = jugador.pk
    return esc.client.post(
        reverse("partido-registrar-incidencia", kwargs={"pk": partido.pk}), cuerpo, format="json"
    )


def resultado(esc, partido, local=0, visitante=0, **extra):
    return esc.client.post(
        reverse("partido-registrar-resultado", kwargs={"pk": partido.pk}),
        {"goles_local": local, "goles_visitante": visitante, **extra},
        format="json",
    )


def sancion(jugador):
    return FichaJugador.objects.get(pk=jugador.pk).partidos_sancion_restantes


def test_ciclo_roja_sancion_cumplimiento(mundo):
    esc = mundo

    # 1. La roja en la ida sanciona 1 partido.
    roja = incidencia(esc, esc.ida, "TARJETA_ROJA", esc.jugador)
    assert roja.status_code == 201
    assert roja.data["partidos_sancion"] == 1
    ficha = FichaJugador.objects.get(pk=esc.jugador.pk)
    assert ficha.partidos_sancion_restantes == 1
    assert ficha.sancion_origen == roja.data["id"]

    # 2. Terminar el mismo partido NO descuenta la sanción recién impuesta.
    assert resultado(esc, esc.ida, 0, 1).status_code == 201
    assert sancion(esc.jugador) == 1

    # 3. El elegibilidad lo advierte y la incidencia lo bloquea en la vuelta.
    inscripcion = Inscripcion.objects.get(campeonato=esc.campeonato, equipo=esc.local)
    assert any("sanción" in a for a in evaluar_inscripcion(inscripcion)["advertencias"])
    bloqueado = incidencia(esc, esc.vuelta, "GOL", esc.jugador)
    assert bloqueado.status_code == 400
    assert "sancionado" in str(bloqueado.data)

    # 4. Al finalizar el siguiente partido del equipo se cumple la sanción.
    assert resultado(esc, esc.vuelta, 1, 0).status_code == 201
    assert sancion(esc.jugador) == 0
    inscripcion_ok = evaluar_inscripcion(inscripcion)
    assert not any("sanción" in a for a in inscripcion_ok["advertencias"])


def test_el_jugador_expulsado_puede_tener_mas_incidencias_en_el_mismo_partido(mundo):
    esc = mundo
    incidencia(esc, esc.ida, "TARJETA_ROJA", esc.jugador)

    respuesta = incidencia(esc, esc.ida, "OTRO", esc.jugador)

    assert respuesta.status_code == 201


def test_corregir_el_resultado_no_descuenta_dos_veces(mundo):
    esc = mundo
    incidencia(esc, esc.ida, "TARJETA_ROJA", esc.jugador)
    resultado(esc, esc.ida, 0, 0)
    resultado(esc, esc.vuelta, 0, 0)
    assert sancion(esc.jugador) == 0

    esc.client.patch(
        reverse("partido-registrar-resultado", kwargs={"pk": esc.vuelta.pk}),
        {"goles_local": 1, "motivo": "Corrección"}, format="json",
    )

    assert sancion(esc.jugador) == 0


def test_un_walkover_no_cuenta_como_partido_cumplido(mundo):
    esc = mundo
    incidencia(esc, esc.ida, "TARJETA_ROJA", esc.jugador)
    resultado(esc, esc.ida, 0, 0)

    esc.client.post(
        reverse("partido-registrar-resultado", kwargs={"pk": esc.vuelta.pk}),
        {"walkover": True, "ganador_walkover": "VISITANTE"}, format="json",
    )

    assert sancion(esc.jugador) == 1


def test_roja_con_sancion_configurable_de_varios_partidos(mundo, settings):
    esc = mundo
    settings.SANCION_PARTIDOS_ROJA = 2
    extra = [
        Partido.objects.create(
            campeonato=esc.campeonato, equipo_local=esc.local, equipo_visitante=esc.visitante,
            fecha_hora=timezone.now() + timedelta(days=60 + i), jornada=10 + i,
        )
        for i in range(2)
    ]
    incidencia(esc, esc.ida, "TARJETA_ROJA", esc.jugador)
    resultado(esc, esc.ida)
    assert sancion(esc.jugador) == 2

    resultado(esc, esc.vuelta)
    assert sancion(esc.jugador) == 1
    resultado(esc, extra[0])
    assert sancion(esc.jugador) == 0


def test_amarillas_acumuladas_generan_sancion(mundo, settings):
    esc = mundo
    settings.AMARILLAS_PARA_SANCION = 2

    primera = incidencia(esc, esc.ida, "TARJETA_AMARILLA", esc.jugador)
    assert primera.data["partidos_sancion"] == 0 and sancion(esc.jugador) == 0
    resultado(esc, esc.ida)
    segunda = incidencia(esc, esc.vuelta, "TARJETA_AMARILLA", esc.jugador)

    assert segunda.data["partidos_sancion"] == 1
    assert sancion(esc.jugador) == 1


def test_la_bitacora_registra_los_partidos_de_sancion(mundo):
    esc = mundo

    incidencia(esc, esc.ida, "TARJETA_ROJA", esc.jugador)

    registro = Bitacora.objects.get(accion=Bitacora.Accion.REGISTRAR_INCIDENCIA)
    assert registro.detalle["tipo"] == "TARJETA_ROJA"
    assert registro.detalle["partidos_sancion"] == 1


def test_el_jugador_debe_pertenecer_a_uno_de_los_equipos_del_partido(mundo):
    esc = mundo
    ajeno = crear_jugador(crear_equipo("Otro equipo"), 1)

    respuesta = incidencia(esc, esc.ida, "GOL", ajeno)

    assert respuesta.status_code == 400
    assert "pertenecer" in str(respuesta.data)


@pytest.mark.parametrize("tipo", ["GOL", "TARJETA_AMARILLA", "TARJETA_ROJA", "LESION"])
def test_estas_incidencias_exigen_jugador(mundo, tipo):
    respuesta = incidencia(mundo, mundo.ida, tipo)

    assert respuesta.status_code == 400 and "jugador" in respuesta.data


@pytest.mark.parametrize("tipo", ["OTRO", "SUSTITUCION"])
def test_otras_incidencias_no_exigen_jugador(mundo, tipo):
    assert incidencia(mundo, mundo.ida, tipo).status_code == 201


def test_no_se_registran_incidencias_en_un_walkover(mundo):
    esc = mundo
    esc.client.post(
        reverse("partido-registrar-resultado", kwargs={"pk": esc.ida.pk}),
        {"walkover": True, "ganador_walkover": "LOCAL"}, format="json",
    )

    respuesta = incidencia(esc, esc.ida, "OTRO")

    assert respuesta.status_code == 400 and "W.O." in str(respuesta.data)


def test_el_organizador_registra_incidencias_pero_el_delegado_no(mundo):
    esc = mundo
    cuerpo = {"tipo": "OTRO", "minuto": 5}
    url = reverse("partido-registrar-incidencia", kwargs={"pk": esc.ida.pk})
    delegado = cliente_de(crear_usuario(Usuario.Rol.DELEGADO, esc.local.facultad))

    assert esc.client_org.post(url, cuerpo, format="json").status_code == 201
    assert delegado.post(url, cuerpo, format="json").status_code == 403
    assert Incidencia.objects.count() == 1
