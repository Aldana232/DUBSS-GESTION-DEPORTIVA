"""F3-04 — Formato eliminación directa: llaves, BYE, avance del ganador y penales."""
import pytest
from django.urls import reverse

from apps.deportes.models import Campeonato
from apps.fixture.models import Partido
from apps.fixture.services.fixture_generator import (
    FixtureGenerator, nombre_ronda, orden_de_siembra,
)

from .helpers import crear_escenario, hay_solapes

pytestmark = pytest.mark.django_db


def escenario(n):
    esc = crear_escenario(
        equipos=n, canchas=2, formato=Campeonato.Formato.ELIMINACION,
    )
    esc.partidos = FixtureGenerator(esc.campeonato.pk).generar()
    return esc


def url(partido):
    return reverse("partido-registrar-resultado", kwargs={"pk": partido.pk})


def jugar(esc, partido, local, visitante, **extra):
    return esc.client.post(
        url(partido), {"goles_local": local, "goles_visitante": visitante, **extra},
        format="json",
    )


def recargar(partido):
    return Partido.objects.get(pk=partido.pk)


def test_orden_de_siembra_estandar():
    assert orden_de_siembra(2) == [1, 2]
    assert orden_de_siembra(4) == [1, 4, 2, 3]
    assert orden_de_siembra(8) == [1, 8, 4, 5, 2, 7, 3, 6]


def test_nombres_de_ronda():
    assert [nombre_ronda(r, 3) for r in (1, 2, 3)] == [
        "Cuartos de final", "Semifinal", "Final",
    ]
    assert nombre_ronda(1, 5) == "Ronda 1"


@pytest.mark.parametrize(("equipos", "partidos"), [(2, 1), (3, 2), (4, 3), (5, 4), (8, 7)])
def test_cantidad_de_partidos_de_la_llave(equipos, partidos):
    esc = escenario(equipos)

    assert len(esc.partidos) == partidos
    assert Partido.objects.filter(campeonato=esc.campeonato).count() == partidos
    assert hay_solapes(Partido.objects.filter(campeonato=esc.campeonato)) is None
    assert all(p.generado_por_ml is False for p in esc.partidos)


def test_seis_equipos_con_bye_para_las_cabezas_de_serie():
    esc = escenario(6)
    por_ronda = {}
    for p in Partido.objects.filter(campeonato=esc.campeonato).order_by("ronda", "pk"):
        por_ronda.setdefault(p.ronda, []).append(p)

    assert [len(por_ronda[r]) for r in (1, 2, 3)] == [2, 2, 1]
    assert [p.fase for r in (1, 2, 3) for p in por_ronda[r][:1]] == [
        "Cuartos de final", "Semifinal", "Final",
    ]
    semis = por_ronda[2]
    # Las semillas 1 y 2 (primeras inscritas) esperan en semifinales con BYE.
    assert {semis[0].equipo_local, semis[1].equipo_local} == {esc.equipos[0], esc.equipos[1]}
    assert all(s.equipo_visitante is None and s.partido_origen_visitante for s in semis)
    final = por_ronda[3][0]
    assert final.equipo_local is None and final.equipo_visitante is None
    assert {final.partido_origen_local, final.partido_origen_visitante} == set(semis)
    # Cada ronda juega en días distintos y ordenados.
    assert max(p.fecha_hora for p in por_ronda[1]) < min(p.fecha_hora for p in por_ronda[2])
    assert max(p.fecha_hora for p in por_ronda[2]) < final.fecha_hora


def test_torneo_de_seis_equipos_hasta_la_final():
    esc = escenario(6)
    ronda1 = list(Partido.objects.filter(campeonato=esc.campeonato, ronda=1).order_by("pk"))

    # Ronda 1: gana el local en el primero y el visitante en el segundo.
    assert jugar(esc, ronda1[0], 2, 0).status_code == 201
    assert jugar(esc, ronda1[1], 0, 1).status_code == 201
    semis = list(Partido.objects.filter(campeonato=esc.campeonato, ronda=2).order_by("pk"))
    assert recargar(ronda1[0]).siguiente_como_visitante.count() + \
        recargar(ronda1[0]).siguiente_como_local.count() == 1
    ganadores = {ronda1[0].equipo_local, ronda1[1].equipo_visitante}
    assert {s.equipo_visitante for s in map(recargar, semis)} == ganadores

    # Semifinales y final.
    assert jugar(esc, semis[0], 1, 0).status_code == 201
    assert jugar(esc, semis[1], 3, 2).status_code == 201
    final = recargar(Partido.objects.get(campeonato=esc.campeonato, ronda=3))
    assert final.equipo_local == recargar(semis[0]).equipo_local
    assert final.equipo_visitante == recargar(semis[1]).equipo_local
    assert jugar(esc, final, 2, 1).status_code == 201

    final = recargar(final)
    assert final.estado == Partido.Estado.FINALIZADO
    assert final.resultado.ganador == final.equipo_local


def test_no_se_juega_un_partido_sin_equipos_definidos():
    esc = escenario(4)
    final = Partido.objects.get(campeonato=esc.campeonato, ronda=2)

    respuesta = jugar(esc, final, 1, 0)

    assert respuesta.status_code == 400
    assert "dos equipos definidos" in str(respuesta.data)


def test_empate_en_eliminacion_exige_penales():
    esc = escenario(4)
    semi = Partido.objects.filter(campeonato=esc.campeonato, ronda=1).order_by("pk")[0]

    sin_penales = jugar(esc, semi, 1, 1)
    con_penales_iguales = jugar(esc, semi, 1, 1, penales_local=3, penales_visitante=3)
    con_uno_solo = jugar(esc, semi, 1, 1, penales_local=3)
    ok = jugar(esc, semi, 1, 1, penales_local=2, penales_visitante=4)

    assert sin_penales.status_code == 400 and "penales" in str(sin_penales.data)
    assert con_penales_iguales.status_code == 400
    assert con_uno_solo.status_code == 400
    assert ok.status_code == 201
    final = Partido.objects.get(campeonato=esc.campeonato, ronda=2)
    assert final.equipo_local == recargar(semi).equipo_visitante  # ganó por penales


def test_penales_solo_con_empate_y_solo_en_eliminacion():
    esc = escenario(4)
    semi = Partido.objects.filter(campeonato=esc.campeonato, ronda=1).order_by("pk")[0]

    sin_empate = jugar(esc, semi, 2, 1, penales_local=3, penales_visitante=1)
    assert sin_empate.status_code == 400

    liga = crear_escenario(equipos=2, canchas=1)
    (partido,) = FixtureGenerator(liga.campeonato.pk).generar()
    en_liga = liga.client.post(
        url(partido),
        {"goles_local": 1, "goles_visitante": 1, "penales_local": 3, "penales_visitante": 2},
        format="json",
    )
    assert en_liga.status_code == 400
    assert "eliminación directa" in str(en_liga.data)


def test_corregir_cambia_el_ganador_y_lo_propaga_si_la_siguiente_no_se_jugo():
    esc = escenario(4)
    semi1, semi2 = Partido.objects.filter(campeonato=esc.campeonato, ronda=1).order_by("pk")
    final = Partido.objects.get(campeonato=esc.campeonato, ronda=2)
    jugar(esc, semi1, 1, 0)
    assert recargar(final).equipo_local == semi1.equipo_local

    correccion = esc.client.patch(
        url(semi1), {"goles_local": 0, "goles_visitante": 2, "motivo": "Acta mal cargada"},
        format="json",
    )

    assert correccion.status_code == 200
    assert recargar(final).equipo_local == semi1.equipo_visitante


def test_no_se_corrige_un_ganador_que_ya_jugo_la_siguiente_ronda():
    esc = escenario(4)
    semi1, semi2 = Partido.objects.filter(campeonato=esc.campeonato, ronda=1).order_by("pk")
    final = Partido.objects.get(campeonato=esc.campeonato, ronda=2)
    jugar(esc, semi1, 1, 0)
    jugar(esc, semi2, 1, 0)
    assert jugar(esc, final, 1, 0).status_code == 201

    cambia_ganador = esc.client.patch(
        url(semi1), {"goles_local": 0, "goles_visitante": 3, "motivo": "Error"}, format="json",
    )
    mismo_ganador = esc.client.patch(
        url(semi1), {"goles_local": 5, "goles_visitante": 0, "motivo": "Goles mal contados"},
        format="json",
    )

    assert cambia_ganador.status_code == 400
    assert "ya avanzó y jugó" in str(cambia_ganador.data)
    assert mismo_ganador.status_code == 200


def test_eliminar_el_resultado_libera_la_plaza_siguiente():
    esc = escenario(4)
    semi1, _ = Partido.objects.filter(campeonato=esc.campeonato, ronda=1).order_by("pk")
    final = Partido.objects.get(campeonato=esc.campeonato, ronda=2)
    jugar(esc, semi1, 1, 0)
    assert recargar(final).equipo_local is not None

    respuesta = esc.client.delete(url(semi1), {"motivo": "Partido anulado"}, format="json")

    assert respuesta.status_code == 204
    assert recargar(final).equipo_local is None
    assert recargar(semi1).estado == Partido.Estado.PROGRAMADO


def test_listados_reportes_y_ml_toleran_partidos_por_definir():
    esc = escenario(4)

    lista = esc.client.get(reverse("partido-list"), {"campeonato": esc.campeonato.pk})
    assert lista.status_code == 200
    filas = lista.data["results"] if "results" in lista.data else lista.data
    assert any(f["local"] == "Por definir" for f in filas)

    detalle = esc.client.get(reverse("partido-detail", kwargs={
        "pk": Partido.objects.get(campeonato=esc.campeonato, ronda=2).pk}))
    assert detalle.status_code == 200 and detalle.data["equipo_local_detalle"] is None

    excel = esc.client.get(reverse("reporte-excel", kwargs={"campeonato_id": esc.campeonato.pk}))
    pdf = esc.client.get(reverse("reporte-pdf", kwargs={"campeonato_id": esc.campeonato.pk}))
    tablero = esc.client.get(reverse("ml-tablero"), {"campeonato": esc.campeonato.pk})
    assert (excel.status_code, pdf.status_code, tablero.status_code) == (200, 200, 200)

    final = Partido.objects.get(campeonato=esc.campeonato, ronda=2)
    prediccion = esc.client.get(reverse("ml-prediccion", kwargs={"partido_id": final.pk}))
    assert prediccion.status_code == 400
