"""F3-05 resultados corregibles, F3-06 tabla recalculable, F3-07 historial."""
from collections import defaultdict

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato
from apps.fixture.models import Incidencia, Partido, PosicionHistorial, Resultado, TablaPosiciones
from apps.fixture.services import tabla
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.users.models import Usuario

from .helpers import (
    cliente_de, crear_escenario, crear_jugador, crear_usuario,
)

pytestmark = pytest.mark.django_db


def url(partido):
    return reverse("partido-registrar-resultado", kwargs={"pk": partido.pk})


def registrar(client, partido, local, visitante, **extra):
    return client.post(
        url(partido), {"goles_local": local, "goles_visitante": visitante, **extra},
        format="json",
    )


def filas(campeonato):
    return {
        t.equipo_id: (t.posicion, t.pj, t.pg, t.pe, t.pp, t.gf, t.gc, t.puntos)
        for t in TablaPosiciones.objects.filter(campeonato=campeonato)
    }


def desde_cero(campeonato):
    """Tabla calculada de forma independiente, sin usar el servicio."""
    acumulado = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0])  # pj pg pe pp gf gc pts
    for r in Resultado.objects.filter(
        partido__campeonato=campeonato
    ).select_related("partido"):
        for equipo, favor, contra in (
            (r.partido.equipo_local_id, r.goles_local, r.goles_visitante),
            (r.partido.equipo_visitante_id, r.goles_visitante, r.goles_local),
        ):
            fila = acumulado[equipo]
            fila[0] += 1
            fila[4] += favor
            fila[5] += contra
            if favor > contra:
                fila[1] += 1
                fila[6] += campeonato.puntos_victoria
            elif favor == contra:
                fila[2] += 1
                fila[6] += campeonato.puntos_empate
            else:
                fila[3] += 1
                fila[6] += campeonato.puntos_derrota
    return acumulado


def comparar_con_desde_cero(campeonato):
    esperado = desde_cero(campeonato)
    actual = filas(campeonato)
    for equipo_id, (_, *stats) in actual.items():
        assert stats == esperado.get(equipo_id, [0] * 7)


@pytest.fixture
def liga():
    esc = crear_escenario(equipos=4, canchas=2)
    esc.partidos = list(FixtureGenerator(esc.campeonato.pk).generar())
    return esc


# ── F3-05 Resultados corregibles ─────────────────────────────────────────────

def test_registrar_resultado_finaliza_el_partido_y_actualiza_la_tabla(liga):
    partido = liga.partidos[0]

    respuesta = registrar(liga.client, partido, 3, 1)

    assert respuesta.status_code == 201
    partido.refresh_from_db()
    assert partido.estado == Partido.Estado.FINALIZADO
    tabla_fila = TablaPosiciones.objects.get(campeonato=liga.campeonato, equipo=partido.equipo_local)
    assert (tabla_fila.puntos, tabla_fila.gf, tabla_fila.gc, tabla_fila.posicion) == (3, 3, 1, 1)


def test_corregir_un_resultado_deja_la_tabla_correcta(liga):
    partido = liga.partidos[0]
    registrar(liga.client, partido, 2, 0)

    respuesta = liga.client.patch(
        url(partido),
        {"goles_local": 0, "goles_visitante": 1, "motivo": "Se anotó el acta al revés"},
        format="json",
    )

    assert respuesta.status_code == 200
    local = TablaPosiciones.objects.get(campeonato=liga.campeonato, equipo=partido.equipo_local)
    visitante = TablaPosiciones.objects.get(
        campeonato=liga.campeonato, equipo=partido.equipo_visitante
    )
    assert (local.puntos, local.pp, local.gc) == (0, 1, 1)
    assert (visitante.puntos, visitante.pg, visitante.gf, visitante.posicion) == (3, 1, 1, 1)
    comparar_con_desde_cero(liga.campeonato)


def test_la_correccion_exige_motivo_y_registra_anterior_y_nuevo_en_bitacora(liga):
    partido = liga.partidos[0]
    registrar(liga.client, partido, 2, 0)

    sin_motivo = liga.client.patch(url(partido), {"goles_local": 1}, format="json")
    assert sin_motivo.status_code == 400 and "motivo" in sin_motivo.data

    liga.client.patch(url(partido), {"goles_local": 1, "motivo": "Gol anulado por VAR"},
                      format="json")
    registro = Bitacora.objects.get(accion=Bitacora.Accion.CORREGIR_RESULTADO)
    assert registro.detalle["motivo"] == "Gol anulado por VAR"
    assert registro.detalle["anterior"]["goles_local"] == 2
    assert registro.detalle["nuevo"]["goles_local"] == 1
    assert registro.usuario == liga.admin


def test_correccion_parcial_conserva_el_otro_marcador(liga):
    partido = liga.partidos[0]
    registrar(liga.client, partido, 2, 1)

    liga.client.patch(url(partido), {"goles_visitante": 2, "motivo": "Faltaba un gol"},
                      format="json")

    resultado = Resultado.objects.get(partido=partido)
    assert (resultado.goles_local, resultado.goles_visitante) == (2, 2)


def test_organizador_corrige_y_delegado_no(liga):
    partido = liga.partidos[0]
    registrar(liga.client, partido, 1, 0)
    delegado = cliente_de(crear_usuario(Usuario.Rol.DELEGADO, liga.equipos[0].facultad))

    por_delegado = delegado.patch(url(partido), {"goles_local": 5, "motivo": "x"}, format="json")
    por_organizador = liga.client_org.patch(
        url(partido), {"goles_local": 4, "motivo": "Corrección"}, format="json"
    )
    borrado_delegado = delegado.delete(url(partido), {"motivo": "x"}, format="json")
    anonimo = APIClient().patch(url(partido), {"goles_local": 5, "motivo": "x"}, format="json")

    assert por_delegado.status_code == 403
    assert por_organizador.status_code == 200
    assert borrado_delegado.status_code == 403
    assert anonimo.status_code == 401


def test_post_duplicado_pide_usar_patch_y_patch_sin_resultado_falla(liga):
    partido, otro = liga.partidos[0], liga.partidos[1]
    registrar(liga.client, partido, 1, 0)

    repetido = registrar(liga.client, partido, 2, 0)
    sin_resultado = liga.client.patch(url(otro), {"goles_local": 1, "motivo": "x"}, format="json")

    assert repetido.status_code == 409 and "PATCH" in str(repetido.data)
    assert sin_resultado.status_code == 400


def test_eliminar_resultado_requiere_motivo_y_devuelve_el_partido_a_programado(liga):
    partido = liga.partidos[0]
    registrar(liga.client, partido, 1, 0)

    sin_motivo = liga.client.delete(url(partido), {}, format="json")
    respuesta = liga.client.delete(url(partido), {"motivo": "Partido repetido"}, format="json")

    assert sin_motivo.status_code == 400
    assert respuesta.status_code == 204
    partido.refresh_from_db()
    assert partido.estado == Partido.Estado.PROGRAMADO
    assert not Resultado.objects.filter(partido=partido).exists()
    assert filas(liga.campeonato)[partido.equipo_local_id][1] == 0  # pj = 0
    registro = Bitacora.objects.get(accion=Bitacora.Accion.CORREGIR_RESULTADO)
    assert registro.detalle["operacion"] == "eliminar"


def test_no_se_borra_un_partido_con_resultado(liga):
    partido = liga.partidos[0]
    registrar(liga.client, partido, 1, 0)

    respuesta = liga.client.delete(reverse("partido-detail", kwargs={"pk": partido.pk}))

    assert respuesta.status_code == 400
    assert Partido.objects.filter(pk=partido.pk).exists()


def test_walkover_asigna_marcador_administrativo_configurable(liga, settings):
    partido = liga.partidos[0]

    respuesta = registrar(liga.client, partido, 0, 0, walkover=True,
                          ganador_walkover="VISITANTE")
    # el marcador enviado (0-0) se respeta si se manda; sin marcador usa la configuración
    assert respuesta.status_code == 400  # un W.O. no puede empatar

    settings.WALKOVER_GOLES_GANADOR = 5
    otro = liga.partidos[1]
    ok = liga.client.post(
        url(otro), {"walkover": True, "ganador_walkover": "VISITANTE"}, format="json"
    )

    assert ok.status_code == 201
    otro.refresh_from_db()
    assert otro.estado == Partido.Estado.WALKOVER
    resultado = Resultado.objects.get(partido=otro)
    assert (resultado.goles_local, resultado.goles_visitante, resultado.walkover) == (0, 5, True)
    visitante = TablaPosiciones.objects.get(campeonato=liga.campeonato, equipo=otro.equipo_visitante)
    assert (visitante.puntos, visitante.pg) == (3, 1)


def test_walkover_exige_ganador_y_marcador_explicito_es_valido(liga):
    partido, otro = liga.partidos[0], liga.partidos[1]

    sin_ganador = liga.client.post(url(partido), {"walkover": True}, format="json")
    explicito = registrar(liga.client, otro, 3, 0, walkover=True)

    assert sin_ganador.status_code == 400 and "ganador_walkover" in sin_ganador.data
    assert explicito.status_code == 201


def test_se_puede_corregir_un_walkover_a_resultado_normal(liga):
    partido = liga.partidos[0]
    liga.client.post(url(partido), {"walkover": True, "ganador_walkover": "LOCAL"},
                     format="json")

    respuesta = liga.client.patch(
        url(partido),
        {"walkover": False, "goles_local": 1, "goles_visitante": 1, "motivo": "Sí se jugó"},
        format="json",
    )

    assert respuesta.status_code == 200
    partido.refresh_from_db()
    assert partido.estado == Partido.Estado.FINALIZADO
    assert TablaPosiciones.objects.get(
        campeonato=liga.campeonato, equipo=partido.equipo_local
    ).pe == 1


def test_el_resultado_debe_coincidir_con_las_incidencias_de_gol(liga):
    partido = liga.partidos[0]
    jugador = crear_jugador(partido.equipo_local, 9)
    liga.client.post(
        reverse("partido-registrar-incidencia", kwargs={"pk": partido.pk}),
        {"tipo": "GOL", "jugador": jugador.pk, "minuto": 10}, format="json",
    )

    mal = registrar(liga.client, partido, 3, 0)
    bien = registrar(liga.client, partido, 1, 0)
    corregir_mal = liga.client.patch(url(partido), {"goles_local": 4, "motivo": "x"},
                                     format="json")

    assert mal.status_code == 400 and "marcador" in str(mal.data)
    assert bien.status_code == 201
    assert corregir_mal.status_code == 400


# ── F3-06 Tabla recalculable ─────────────────────────────────────────────────

def test_registrar_corregir_y_borrar_equivalen_a_recalcular_desde_cero(liga):
    p1, p2, p3 = liga.partidos[:3]
    pasos = [
        lambda: registrar(liga.client, p1, 2, 1),
        lambda: registrar(liga.client, p2, 0, 0),
        lambda: registrar(liga.client, p3, 1, 4),
        lambda: liga.client.patch(url(p1), {"goles_local": 0, "motivo": "Corrección"},
                                  format="json"),
        lambda: liga.client.delete(url(p2), {"motivo": "Anulado"}, format="json"),
    ]
    for paso in pasos:
        assert paso().status_code in (200, 201, 204)
        incremental = filas(liga.campeonato)
        comparar_con_desde_cero(liga.campeonato)
        TablaPosiciones.objects.filter(campeonato=liga.campeonato).delete()
        tabla.recalcular(liga.campeonato)
        assert filas(liga.campeonato) == incremental


def test_recalcular_es_idempotente(liga):
    registrar(liga.client, liga.partidos[0], 1, 0)

    primera = filas(liga.campeonato)
    tabla.recalcular(liga.campeonato)
    tabla.recalcular(liga.campeonato)

    assert filas(liga.campeonato) == primera
    assert TablaPosiciones.objects.filter(campeonato=liga.campeonato).count() == 4


def test_puntos_configurables_por_campeonato():
    esc = crear_escenario(
        equipos=2, canchas=1, puntos_victoria=2, puntos_empate=1, puntos_derrota=0,
    )
    (partido,) = FixtureGenerator(esc.campeonato.pk).generar()

    registrar(esc.client, partido, 1, 0)

    ganador = TablaPosiciones.objects.get(campeonato=esc.campeonato, equipo=partido.equipo_local)
    assert ganador.puntos == 2


def _liga_manual(nombres):
    """Campeonato con partidos creados a mano para controlar los cruces."""
    esc = crear_escenario(equipos=len(nombres), canchas=1)
    for equipo, nombre in zip(esc.equipos, nombres):
        equipo.nombre = nombre
        equipo.save(update_fields=["nombre"])
    return esc


def _jugar(esc, local, visitante, gl, gv, jornada=1):
    from datetime import timedelta
    from django.utils import timezone
    base = timezone.now() + timedelta(days=30 + Partido.objects.count())
    partido = Partido.objects.create(
        campeonato=esc.campeonato, equipo_local=local, equipo_visitante=visitante,
        fecha_hora=base, jornada=jornada, cancha=esc.canchas[0],
    )
    assert registrar(esc.client, partido, gl, gv).status_code == 201
    return partido


def orden(esc):
    return [t.equipo.nombre for t in TablaPosiciones.objects.filter(
        campeonato=esc.campeonato).select_related("equipo").order_by("posicion")]


def test_desempate_por_diferencia_de_goles():
    esc = _liga_manual(["A", "B", "C", "D"])
    a, b, c, d = esc.equipos
    _jugar(esc, a, c, 1, 0)   # A: 3 pts, dg +1
    _jugar(esc, b, d, 3, 0)   # B: 3 pts, dg +3

    assert orden(esc)[:2] == ["B", "A"]


def test_desempate_por_goles_a_favor():
    esc = _liga_manual(["A", "B", "C", "D"])
    a, b, c, d = esc.equipos
    _jugar(esc, a, c, 2, 1)   # A: 3 pts, dg +1, gf 2
    _jugar(esc, b, d, 1, 0)   # B: 3 pts, dg +1, gf 1

    assert orden(esc)[:2] == ["A", "B"]


def test_desempate_por_enfrentamiento_directo():
    # "Zeta" y "Alfa" empatan en puntos, diferencia y goles; Zeta ganó el duelo directo,
    # aunque por nombre Alfa iría primero.
    esc = _liga_manual(["Zeta", "Alfa", "Cobre", "Delta"])
    zeta, alfa, cobre, delta = esc.equipos
    _jugar(esc, zeta, alfa, 1, 0)    # Zeta gana el duelo directo
    _jugar(esc, cobre, zeta, 1, 0)   # Zeta pierde con Cobre
    _jugar(esc, alfa, delta, 1, 0)   # Alfa gana a Delta

    assert orden(esc) == ["Cobre", "Zeta", "Alfa", "Delta"]


def test_ultimo_desempate_es_el_nombre():
    esc = _liga_manual(["Zeta", "Alfa", "Media", "Beta"])

    tabla.recalcular(esc.campeonato)

    assert orden(esc) == ["Alfa", "Beta", "Media", "Zeta"]


def test_posiciones_son_consecutivas_y_la_vista_publica_las_ordena(liga):
    registrar(liga.client, liga.partidos[0], 2, 0)

    respuesta = APIClient().get(reverse("fixture-tabla"), {"campeonato": liga.campeonato.pk})

    assert respuesta.status_code == 200
    assert [f["posicion"] for f in respuesta.data] == [1, 2, 3, 4]
    assert respuesta.data[0]["puntos"] == 3


# ── F3-07 Historial por jornada ──────────────────────────────────────────────

def jornada(liga, numero):
    return [p for p in liga.partidos if p.jornada == numero]


def test_historial_se_guarda_al_cerrar_cada_jornada(liga):
    j1a, j1b = jornada(liga, 1)

    registrar(liga.client, j1a, 1, 0)
    assert PosicionHistorial.objects.count() == 0  # la jornada sigue abierta

    registrar(liga.client, j1b, 2, 2)
    snapshot = PosicionHistorial.objects.filter(campeonato=liga.campeonato, jornada=1)
    assert snapshot.count() == 4
    assert sorted(h.posicion for h in snapshot) == [1, 2, 3, 4]
    ganador = snapshot.get(equipo=j1a.equipo_local)
    assert (ganador.posicion, ganador.puntos, ganador.pj, ganador.gf, ganador.gc) == (1, 3, 1, 1, 0)


def test_historial_acumula_jornadas_y_el_endpoint_es_publico(liga):
    for numero, marcador in ((1, (1, 0)), (2, (2, 1))):
        for partido in jornada(liga, numero):
            registrar(liga.client, partido, *marcador)

    respuesta = APIClient().get(reverse("campeonato-historial", kwargs={"pk": liga.campeonato.pk}))

    assert respuesta.status_code == 200
    assert [j["jornada"] for j in respuesta.data] == [1, 2]
    segunda = {p["equipo"]: p for p in respuesta.data[1]["posiciones"]}
    primera = {p["equipo"]: p for p in respuesta.data[0]["posiciones"]}
    for equipo_id, fila in segunda.items():
        assert fila["pj"] == primera[equipo_id]["pj"] + 1
    assert [p["posicion"] for p in respuesta.data[1]["posiciones"]] == [1, 2, 3, 4]


def test_corregir_un_resultado_actualiza_el_historial(liga):
    j1a, j1b = jornada(liga, 1)
    registrar(liga.client, j1a, 1, 0)
    registrar(liga.client, j1b, 1, 0)
    antes = PosicionHistorial.objects.get(jornada=1, equipo=j1a.equipo_local).puntos
    assert antes == 3

    liga.client.patch(url(j1a), {"goles_local": 0, "goles_visitante": 2, "motivo": "Error"},
                      format="json")

    assert PosicionHistorial.objects.get(jornada=1, equipo=j1a.equipo_local).puntos == 0
    assert PosicionHistorial.objects.get(jornada=1, equipo=j1a.equipo_visitante).puntos == 3


def test_eliminar_un_resultado_reabre_la_jornada(liga):
    j1a, j1b = jornada(liga, 1)
    registrar(liga.client, j1a, 1, 0)
    registrar(liga.client, j1b, 1, 0)
    assert PosicionHistorial.objects.filter(jornada=1).exists()

    liga.client.delete(url(j1b), {"motivo": "Anulado"}, format="json")

    assert not PosicionHistorial.objects.filter(jornada=1).exists()


def test_historial_vacio_si_no_hay_jornadas_cerradas(liga):
    respuesta = liga.client.get(
        reverse("campeonato-historial", kwargs={"pk": liga.campeonato.pk})
    )

    assert respuesta.status_code == 200 and respuesta.data == []
    assert Incidencia.objects.count() == 0
    assert liga.campeonato.estado == Campeonato.Estado.INSCRIPCION_CERRADA
