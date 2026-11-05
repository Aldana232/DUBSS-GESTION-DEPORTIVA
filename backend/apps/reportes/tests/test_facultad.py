"""F6-05 — Estadísticas y reportes por facultad, equipo y jugador."""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.auditoria.models import Bitacora
from apps.fixture.models import Incidencia, Partido, Resultado
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.fixture.tests.helpers import cliente_de, crear_escenario, crear_jugador, crear_usuario
from apps.reportes import estadisticas as est
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def liga():
    esc = crear_escenario(equipos=3, canchas=2)
    esc.partidos = list(FixtureGenerator(esc.campeonato.pk).generar())
    return esc


def jugar(partido, gl, gv, walkover=False):
    Partido.objects.filter(pk=partido.pk).update(estado=Partido.Estado.FINALIZADO)
    Resultado.objects.create(partido=partido, goles_local=gl, goles_visitante=gv, walkover=walkover)


def test_rendimiento_de_equipo_suma_victorias_empates_derrotas_y_goles(liga):
    a, b, c = liga.partidos
    jugar(a, 2, 0)
    jugar(b, 1, 1)
    jugar(c, 0, 3)
    equipo = a.equipo_local
    esperado = {"pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0}
    for p, (gl, gv) in zip((a, b, c), ((2, 0), (1, 1), (0, 3))):
        if equipo.pk in (p.equipo_local_id, p.equipo_visitante_id):
            gf, gc = (gl, gv) if p.equipo_local_id == equipo.pk else (gv, gl)
            esperado["pj"] += 1; esperado["gf"] += gf; esperado["gc"] += gc
            esperado["pg" if gf > gc else "pe" if gf == gc else "pp"] += 1

    r = est.rendimiento_de_equipo(equipo.pk)

    assert {k: r[k] for k in esperado} == esperado
    assert r["puntos"] == 3 * esperado["pg"] + esperado["pe"] and r["dg"] == esperado["gf"] - esperado["gc"]


def test_los_walkover_no_cuentan_como_rendimiento(liga):
    jugar(liga.partidos[0], 3, 0, walkover=True)

    assert est.rendimiento_de_equipo(liga.partidos[0].equipo_local_id)["pj"] == 0


def test_estadisticas_de_facultad_agregan_equipos_y_jugadores(liga):
    p = liga.partidos[0]
    jugar(p, 2, 1)
    goleador = crear_jugador(p.equipo_local, 9)
    Incidencia.objects.create(partido=p, tipo="GOL", jugador=goleador)
    Incidencia.objects.create(partido=p, tipo="GOL", jugador=goleador)
    Incidencia.objects.create(partido=p, tipo="TARJETA_AMARILLA", jugador=goleador)

    datos = est.estadisticas_facultad(p.equipo_local.facultad)

    assert datos["totales"]["pj"] == 1 and datos["totales"]["gf"] == 2 and datos["totales"]["amarillas"] == 1
    assert datos["goleadores"][0]["goles"] == 2 and datos["totales"]["jugadores"] == 1
    assert datos["campeonatos"] == [liga.campeonato.nombre]


def test_estadisticas_de_jugador_y_equipo(liga):
    p = liga.partidos[0]
    jugador = crear_jugador(p.equipo_local, 10)
    Incidencia.objects.create(partido=p, tipo="TARJETA_ROJA", jugador=jugador)

    assert est.estadisticas_jugador(jugador)["rojas"] == 1
    plantel = est.estadisticas_equipo(p.equipo_local)["plantel"]
    assert plantel[0]["rojas"] == 1 and plantel[0]["numero"] == 10


@pytest.mark.parametrize("formato,tipo", [("pdf", "application/pdf"), ("excel", "spreadsheetml")])
def test_reporte_de_facultad_se_descarga_y_se_audita(liga, formato, tipo):
    facultad = liga.equipos[0].facultad

    r = liga.client_org.get(reverse(f"reporte-facultad-{formato}", kwargs={"facultad_id": facultad.pk}))

    assert r.status_code == 200 and tipo in r["Content-Type"]
    assert facultad.sigla in r["Content-Disposition"]
    assert Bitacora.objects.filter(accion="EXPORTAR", modulo="facultad", objeto_id=facultad.pk).exists()


def test_el_json_de_facultad_y_los_permisos(liga):
    facultad = liga.equipos[0].facultad
    url = reverse("estadisticas-facultad", kwargs={"facultad_id": facultad.pk})

    assert liga.client_org.get(url).data["sigla"] == facultad.sigla
    assert APIClient().get(url).status_code == 401
    assert cliente_de(liga.equipos[0].delegado).get(url).status_code == 403
    assert cliente_de(crear_usuario(Usuario.Rol.JUGADOR)).get(url).status_code == 403
    assert liga.client.get(reverse("estadisticas-facultad", kwargs={"facultad_id": 999999})).status_code == 404
    assert liga.client.get(reverse("reporte-facultad-pdf", kwargs={"facultad_id": 999999})).status_code == 404
