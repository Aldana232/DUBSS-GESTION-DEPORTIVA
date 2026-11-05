"""F7-07 — Niveles y siembra (K-means).  F7-08 — Resultados atípicos (Isolation Forest)."""
from datetime import datetime, timedelta, timezone as tz
from itertools import count

import pytest

from apps.deportes.models import Campeonato
from apps.fixture.models import Partido, Resultado
from apps.fixture.services.fixture_generator import FixtureGenerator, orden_de_siembra
from apps.fixture.tests.helpers import cliente_de, crear_campeonato, crear_escenario, crear_usuario
from apps.ml.models import ResultadoAtipico
from apps.ml.services import atipicos, niveles
from apps.ml.tasks import revisar_resultados_atipicos
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
_jornada = count(1)


def jugar(campeonato, local, visitante, gl, gv, dias=10):
    p = Partido.objects.create(
        campeonato=campeonato, equipo_local=local, equipo_visitante=visitante, jornada=next(_jornada), duracion_min=90,
        fecha_hora=datetime(2025, 3, 1, 10, tzinfo=tz.utc) + timedelta(days=dias + next(_jornada)), estado=Partido.Estado.FINALIZADO)
    Resultado.objects.create(partido=p, goles_local=gl, goles_visitante=gv)
    return p


def historial_por_fuerza(esc, fuerzas):
    """Liga previa (ida y vuelta) donde siempre gana el más fuerte, por más goles cuanto mayor la diferencia."""
    anterior = crear_campeonato(deporte=esc.deporte, estado=Campeonato.Estado.FINALIZADO)
    for i, a in enumerate(esc.equipos):
        for j, b in enumerate(esc.equipos):
            if i == j:
                continue
            d = fuerzas[i] - fuerzas[j]
            gl, gv = (min(4, 1 + abs(d) // 3), 0) if d > 0 else (0, min(4, 1 + abs(d) // 3))
            jugar(anterior, a, b, gl, gv)
    return anterior


@pytest.fixture
def torneo():
    fuerzas = [10, 9, 6, 5, 4, 2, 1, 0]
    esc = crear_escenario(equipos=8, canchas=2, formato=Campeonato.Formato.ELIMINACION)
    historial_por_fuerza(esc, fuerzas)
    esc.fuerzas = fuerzas
    return esc


# ── F7-07 ─────────────────────────────────────────────────────────────────────

def test_los_niveles_ordenan_a_los_equipos_por_rendimiento_real(torneo):
    r = niveles.analizar(torneo.campeonato)

    assert r["metodo"] == "kmeans" and r["datos_suficientes"] and 2 <= r["k"] <= 4
    nombres = [d["nombre"] for d in r["equipos"]]
    assert nombres == [e.nombre for e in torneo.equipos]            # el más fuerte primero: ya vienen ordenados por fuerza
    assert r["equipos"][0]["nivel"] == 1 and r["equipos"][0]["semilla"] == 1
    niveles_seq = [d["nivel"] for d in r["equipos"]]
    assert niveles_seq == sorted(niveles_seq) and niveles_seq[-1] == r["k"] and niveles_seq[0] == 1
    assert r["equipos"][0]["fuerza"] == 100.0 and r["equipos"][-1]["fuerza"] == 0.0
    assert sorted(r["orden_siembra"]) == sorted(e.pk for e in torneo.equipos)


def test_el_analisis_es_determinista(torneo):
    assert niveles.analizar(torneo.campeonato) == niveles.analizar(torneo.campeonato)


def test_los_grupos_serpiente_quedan_parejos(torneo):
    r = niveles.analizar(torneo.campeonato, grupos=2)
    a, b = r["grupos"]
    assert len(a["equipos"]) == len(b["equipos"]) == 4
    assert set(a["equipos"]) | set(b["equipos"]) == set(r["orden_siembra"]) and not set(a["equipos"]) & set(b["equipos"])
    # Los dos mejores caen en grupos distintos, y el reparto es más parejo que «los 4 mejores contra los 4 peores».
    seeds = r["orden_siembra"]
    assert (seeds[0] in a["equipos"]) != (seeds[1] in a["equipos"])
    assert abs(a["fuerza_media"] - b["fuerza_media"]) < 15 and r["balance"]["diferencia_max"] < 15


def test_sin_historial_suficiente_no_se_inventa_un_orden():
    esc = crear_escenario(equipos=6, canchas=1, formato=Campeonato.Formato.ELIMINACION)
    r = niveles.analizar(esc.campeonato)
    assert r["metodo"] == "inscripcion" and not r["datos_suficientes"] and "historial" in r["motivo"]
    assert r["orden_siembra"] == [e.pk for e in esc.equipos] and r["niveles"] == []


def test_un_equipo_sin_historial_se_siembra_al_final_y_se_marca(torneo):
    nuevo = crear_escenario(equipos=0, canchas=0)
    from apps.fixture.tests.helpers import crear_equipo
    novato = crear_equipo("Novato", torneo.campeonato)

    r = niveles.analizar(torneo.campeonato)

    ultimo = r["equipos"][-1]
    assert ultimo["equipo_id"] == novato.pk and ultimo["sin_historial"] and ultimo["nivel"] is None and ultimo["fuerza"] is None
    assert "sin historial" in r["motivo"] and nuevo is not None


def test_los_walkover_no_cuentan_como_rendimiento(torneo):
    antes = niveles.analizar(torneo.campeonato)
    anterior = Campeonato.objects.get(estado=Campeonato.Estado.FINALIZADO)
    p = jugar(anterior, torneo.equipos[7], torneo.equipos[0], 9, 0)
    Resultado.objects.filter(partido=p).update(walkover=True)

    assert niveles.analizar(torneo.campeonato)["orden_siembra"] == antes["orden_siembra"]


def test_endpoint_de_cabezas_de_serie_con_permisos_y_bitacora(torneo):
    url = "/api/v1/ml/cabezas-de-serie/"
    assert cliente_de(crear_usuario(Usuario.Rol.DELEGADO)).post(url, {"campeonato_id": torneo.campeonato.pk}, format="json").status_code == 403
    assert torneo.client_org.post(url, {}, format="json").status_code == 400
    assert torneo.client_org.post(url, {"campeonato_id": 99999}, format="json").status_code == 400

    r = torneo.client_org.post(url, {"campeonato_id": torneo.campeonato.pk, "grupos": 2}, format="json")

    assert r.status_code == 200 and len(r.data["grupos"]) == 2 and len(r.data["cabezas_de_serie"]) == 2
    from apps.auditoria.models import Bitacora
    assert Bitacora.objects.filter(accion="ML_PRED", modulo="campeonato", objeto_id=torneo.campeonato.pk).exists()


def test_la_siembra_ml_coloca_a_los_mejores_en_lados_opuestos_de_la_llave(torneo):
    from apps.deportes.models import Inscripcion
    # Se invierte el orden de inscripción: sin siembra, el más fuerte quedaría de último.
    for i, e in enumerate(reversed(torneo.equipos)):
        Inscripcion.objects.filter(equipo=e, campeonato=torneo.campeonato).update(fecha_inscripcion=datetime(2026, 1, 1, 8, i, tzinfo=tz.utc))

    g = FixtureGenerator(torneo.campeonato.pk)
    partidos = g.generar(sembrar_con_ml=True)

    assert g.resultado["siembra"]["aplicada"] and g.resultado["siembra"]["orden"][0]["equipo"] == torneo.equipos[0].nombre
    primera = [p for p in partidos if p.ronda == 1]
    enfrentamientos = {frozenset((p.equipo_local.nombre, p.equipo_visitante.nombre)) for p in primera}
    n = [e.nombre for e in torneo.equipos]           # ya en orden de fuerza: semillas 1..8
    esperados = {frozenset((n[a - 1], n[b - 1])) for a, b in ((1, 8), (4, 5), (2, 7), (3, 6))}
    assert enfrentamientos == esperados and orden_de_siembra(8)[:2] == [1, 8]


def test_sin_la_opcion_la_siembra_sigue_siendo_el_orden_de_inscripcion(torneo):
    g = FixtureGenerator(torneo.campeonato.pk)
    g.generar()
    assert g.resultado["siembra"] is None


def test_siembra_ml_con_datos_insuficientes_avisa_y_conserva_el_orden():
    esc = crear_escenario(equipos=4, canchas=1, formato=Campeonato.Formato.ELIMINACION)
    g = FixtureGenerator(esc.campeonato.pk)
    g.generar(sembrar_con_ml=True)
    assert g.resultado["siembra"]["aplicada"] is False and "historial" in g.resultado["siembra"]["motivo"]


def test_endpoint_generar_acepta_sembrar_con_ml(torneo):
    r = torneo.client_org.post("/api/v1/fixture/generar/", {"campeonato_id": torneo.campeonato.pk, "sembrar_con_ml": True}, format="json")
    assert r.status_code == 201 and r.data["siembra"]["aplicada"] is True


# ── F7-08 ─────────────────────────────────────────────────────────────────────

MARCADORES_NORMALES = [(1, 0), (2, 1), (1, 1), (0, 0), (2, 0), (1, 2), (3, 1), (0, 1), (2, 2), (1, 0)]


@pytest.fixture
def liga_normal():
    esc = crear_escenario(equipos=6, canchas=1)
    liga = crear_campeonato(deporte=esc.deporte, estado=Campeonato.Estado.FINALIZADO)
    partidos = []
    for k in range(40):
        a, b = esc.equipos[k % 6], esc.equipos[(k % 6 + 1 + (k // 6) % 5) % 6]      # nunca un equipo contra sí mismo
        gl, gv = MARCADORES_NORMALES[k % 10]
        partidos.append(jugar(liga, a, b, gl, gv))
    esc.liga, esc.partidos = liga, partidos
    return esc


def test_un_marcador_normal_no_genera_alertas(liga_normal):
    assert atipicos.detectar(liga_normal.deporte.pk) == []


def test_un_9_a_0_se_detecta_y_se_explica(liga_normal):
    raro = jugar(liga_normal.liga, liga_normal.equipos[0], liga_normal.equipos[1], 9, 0)

    encontrados = atipicos.detectar(liga_normal.deporte.pk)

    assert [h["partido"].pk for h in encontrados] == [raro.pk]
    assert "9-0" in encontrados[0]["motivo"] and "lo habitual" in encontrados[0]["motivo"] and 0 < encontrados[0]["puntaje"] < 1


def test_con_poco_historial_no_se_dice_nada():
    esc = crear_escenario(equipos=2, canchas=1)
    liga = crear_campeonato(deporte=esc.deporte, estado=Campeonato.Estado.FINALIZADO)
    for gl, gv in [(1, 0)] * 10 + [(12, 0)]:
        jugar(liga, esc.equipos[0], esc.equipos[1], gl, gv)
    assert atipicos.detectar(esc.deporte.pk) == []


def test_el_escaneo_es_idempotente_y_no_cuenta_walkover(liga_normal):
    jugar(liga_normal.liga, liga_normal.equipos[0], liga_normal.equipos[1], 9, 0)
    wo = jugar(liga_normal.liga, liga_normal.equipos[2], liga_normal.equipos[3], 10, 0)
    Resultado.objects.filter(partido=wo).update(walkover=True)

    primera, segunda = atipicos.escanear(), atipicos.escanear()

    assert len(primera) == 1 and segunda == [] and ResultadoAtipico.objects.count() == 1


def test_la_tarea_avisa_a_la_administracion_solo_de_lo_nuevo(liga_normal, monkeypatch):
    jugar(liga_normal.liga, liga_normal.equipos[0], liga_normal.equipos[1], 9, 0)
    avisos = []
    monkeypatch.setattr("apps.ml.tasks.notificar_usuarios", lambda usuarios, titulo, mensaje, datos=None: avisos.append((len(list(usuarios)), titulo, mensaje)))

    assert revisar_resultados_atipicos() == {"nuevas": 1}
    assert revisar_resultados_atipicos() == {"nuevas": 0}
    assert len(avisos) == 1 and "9-0" in avisos[0][2] and avisos[0][1] == "Resultado atípico por revisar" and avisos[0][0] >= 1


def test_endpoints_de_atipicos_permisos_y_revision(liga_normal):
    jugar(liga_normal.liga, liga_normal.equipos[0], liga_normal.equipos[1], 9, 0)
    delegado = cliente_de(liga_normal.equipos[0].delegado)
    assert delegado.get("/api/v1/ml/atipicos/").status_code == 403
    assert liga_normal.client_org.post("/api/v1/ml/atipicos/").status_code == 403          # buscar ahora: solo administración
    r = liga_normal.client.post("/api/v1/ml/atipicos/")
    assert r.status_code == 200 and r.data["nuevos"] == 1

    lista = liga_normal.client_org.get("/api/v1/ml/atipicos/").data
    assert lista["pendientes"] == 1 and lista["resultados"][0]["marcador"] == "9-0" and lista["resultados"][0]["revisado"] is False
    alerta_id = lista["resultados"][0]["id"]
    assert liga_normal.client_org.post(f"/api/v1/ml/atipicos/{alerta_id}/revisar/").data["revisado"] is True
    assert liga_normal.client_org.get("/api/v1/ml/atipicos/").data["pendientes"] == 0
    assert liga_normal.client_org.get("/api/v1/ml/atipicos/?revisado=false").data["resultados"] == []
    assert liga_normal.client_org.post("/api/v1/ml/atipicos/99999/revisar/").status_code == 404
