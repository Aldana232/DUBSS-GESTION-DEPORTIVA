"""F6-01 — Predictor de resultados: sin fuga de datos, validación temporal, líneas base y registro."""
import random
from datetime import date, datetime, timedelta

import numpy as np
import pytest
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato, Categoria, Deporte, Equipo, Facultad
from apps.fixture.models import Partido, Resultado
from apps.fixture.tests.helpers import cliente_de, crear_usuario
from apps.ml.models import ModeloML, PrediccionPartido
from apps.ml.services import predictor as pr
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def modelos_en_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(pr, "MODEL_DIR", tmp_path)
    pr._cache.clear()


def liga_sintetica(vueltas=3, fuerzas=(3.0, 2.2, 1.6, 1.2, 0.9, 0.6, 0.4, 0.2), semilla=5):
    """Liga con equipos de distinta fuerza: los fuertes ganan con más frecuencia (resultados con ruido)."""
    rnd = random.Random(semilla)
    deporte = Deporte.objects.create(nombre=f"Deporte predictor {semilla}")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Mayores")
    campeonato = Campeonato.objects.create(
        nombre="Liga sintética", categoria=categoria, fecha_inicio=date(2026, 1, 1), fecha_fin=date(2026, 12, 31),
    )
    facultad = Facultad.objects.create(nombre=f"Facultad predictor {semilla}", sigla=f"P{semilla}")
    equipos = [Equipo.objects.create(nombre=f"Eq {i}", facultad=facultad) for i in range(len(fuerzas))]
    inicio = timezone.make_aware(datetime(2026, 1, 3, 10))
    jornada, dia, partidos = 0, 0, []
    for _ in range(vueltas):
        for i, local in enumerate(equipos):
            for j, visitante in enumerate(equipos):
                if i == j:
                    continue
                jornada += 1
                dia += 1
                p = Partido.objects.create(
                    campeonato=campeonato, equipo_local=local, equipo_visitante=visitante,
                    fecha_hora=inicio + timedelta(days=dia), jornada=jornada,
                    estado=Partido.Estado.FINALIZADO,
                )
                gl = max(0, int(round(rnd.gauss(fuerzas[i] + 0.4, 1.0))))
                gv = max(0, int(round(rnd.gauss(fuerzas[j], 1.0))))
                Resultado.objects.create(partido=p, goles_local=gl, goles_visitante=gv)
                partidos.append(p)
    return campeonato, equipos, partidos


def partido_futuro(campeonato, local, visitante, jornada=9999):
    return Partido.objects.create(
        campeonato=campeonato, equipo_local=local, equipo_visitante=visitante,
        fecha_hora=timezone.now() + timedelta(days=5), jornada=jornada,
    )


# ── Sin datos suficientes: respuesta honesta ──────────────────────────────────

def test_sin_historial_no_entrena_y_explica_por_que():
    resultado = pr.entrenar()

    assert resultado["entrenado"] is False
    assert "Datos insuficientes" in resultado["motivo"] and resultado["minimo"] == pr.MIN_PARTIDOS_ENTRENAMIENTO
    assert not ModeloML.objects.exists()


def test_con_pocos_partidos_predice_con_elo_y_baja_confianza():
    campeonato, equipos, _ = liga_sintetica(vueltas=1, fuerzas=(3, 1, 1))
    nuevo = partido_futuro(campeonato, equipos[0], equipos[1])

    p = pr.PredictorResultados().predecir(nuevo, persistir=False)

    assert p.modelo_version == "elo-base"
    assert p.datos_suficientes is True          # ya jugaron 2 partidos cada uno... pero menos de 3
    assert p.confianza <= 0.6
    assert abs(p.prob_victoria_local + p.prob_empate + p.prob_victoria_visit - 1) < 1e-3


def test_equipos_sin_historial_se_marcan_como_datos_insuficientes():
    campeonato, equipos, _ = liga_sintetica(vueltas=1, fuerzas=(2, 1))
    otro = Equipo.objects.create(nombre="Recién llegado", facultad=equipos[0].facultad)
    nuevo = partido_futuro(campeonato, equipos[0], otro)

    p = pr.PredictorResultados().predecir(nuevo, persistir=False)

    assert p.datos_suficientes is False and p.confianza == 0.0


# ── Sin fuga de datos ─────────────────────────────────────────────────────────

def test_las_caracteristicas_de_un_partido_no_dependen_de_su_propio_resultado_ni_del_futuro():
    _, _, partidos = liga_sintetica(vueltas=1, fuerzas=(3, 2, 1, 0.5))
    X1, y1, _, _ = pr.construir_dataset()

    ultimo = partidos[-1]
    Resultado.objects.filter(partido=ultimo).update(goles_local=9, goles_visitante=0)
    X2, y2, _, _ = pr.construir_dataset()

    # Cambiar el resultado del ÚLTIMO partido no puede alterar las características de ningún partido.
    assert np.array_equal(X1, X2)
    # Y el primer partido de la historia se describe con equipos sin historia.
    primera = dict(zip(pr.FEATURES, X1[0]))
    assert primera["elo_local"] == primera["elo_visitante"] == pr.ELO_INICIAL
    assert primera["partidos_local"] == primera["partidos_visitante"] == 0


def test_el_estado_se_actualiza_solo_despues_de_cada_partido():
    _, equipos, partidos = liga_sintetica(vueltas=1, fuerzas=(3, 1))
    X, _, historial, _ = pr.construir_dataset()
    primero, segundo = dict(zip(pr.FEATURES, X[0])), dict(zip(pr.FEATURES, X[1]))

    assert primero["partidos_local"] == 0
    assert segundo["partidos_local"] == 1 and segundo["partidos_visitante"] == 1   # ya jugaron el primero
    assert historial.total == 2


def test_los_walkover_no_cuentan_como_nivel_de_juego():
    _, _, partidos = liga_sintetica(vueltas=1, fuerzas=(3, 1))
    Resultado.objects.filter(partido=partidos[0]).update(walkover=True)

    X, y, _, _ = pr.construir_dataset()

    assert len(y) == 1


# ── Probabilidades de Elo ─────────────────────────────────────────────────────

def test_elo_da_probabilidades_validas_y_ventaja_de_local():
    iguales = pr.probas_elo(1500, 1500, 0.25)
    assert abs(iguales.sum() - 1) < 1e-9 and iguales[0] > iguales[2]
    assert pr.probas_elo(1700, 1400, 0.25)[0] > iguales[0] > pr.probas_elo(1400, 1700, 0.25)[0]
    # Más parejos => más probable el empate.
    assert iguales[1] > pr.probas_elo(1900, 1300, 0.25)[1]


# ── Entrenamiento, validación y registro ──────────────────────────────────────

def test_entrenar_valida_walk_forward_contra_lineas_base_y_registra_el_modelo():
    liga_sintetica(vueltas=3)

    r = pr.entrenar()

    assert r["entrenado"] is True and r["partidos"] == 168
    assert r["cortes_walk_forward"] >= 2 and r["partidos_validacion"] > 0
    for bloque in ("modelo", "linea_base_frecuencia", "linea_base_elo"):
        assert set(r[bloque]) == {"accuracy", "log_loss", "brier", "ece"}
        assert 0 <= r[bloque]["accuracy"] <= 1 and r[bloque]["log_loss"] > 0
    assert isinstance(r["supera_linea_base"], bool) and r["conclusion"]
    registro = ModeloML.objects.get(version=r["version"])
    assert registro.nombre == pr.NOMBRE_MODELO and registro.activo is r["supera_linea_base"]
    assert len(registro.hash_datos) == 64 and registro.metricas["partidos"] == 168


def test_el_modelo_solo_se_activa_si_supera_a_las_lineas_base(monkeypatch):
    liga_sintetica(vueltas=3)

    monkeypatch.setattr(pr, "MARGEN_SUPERIOR", 10)       # exigencia imposible: no puede superar
    no_supera = pr.entrenar()
    assert no_supera["activo"] is False and "NO supera" in no_supera["conclusion"]
    assert not ModeloML.objects.filter(activo=True).exists()

    monkeypatch.setattr(pr, "MARGEN_SUPERIOR", -10)      # exigencia nula: siempre supera
    supera = pr.entrenar()
    assert supera["activo"] is True
    assert ModeloML.objects.filter(activo=True).count() == 1   # el anterior queda inactivo


def test_el_hash_de_datos_es_reproducible_y_cambia_con_los_datos():
    _, _, partidos = liga_sintetica(vueltas=3)
    h1 = pr.entrenar()["hash_datos"]
    pr._cache.clear()
    h2 = pr.entrenar()["hash_datos"]
    Resultado.objects.filter(partido=partidos[0]).update(goles_local=7)
    h3 = pr.entrenar()["hash_datos"]

    assert h1 == h2 and h1 != h3


def test_la_inferencia_usa_el_modelo_activo_y_elo_cuando_no_lo_hay(monkeypatch):
    campeonato, equipos, _ = liga_sintetica(vueltas=3)
    nuevo = partido_futuro(campeonato, equipos[0], equipos[-1])
    sin_modelo = pr.PredictorResultados().predecir(nuevo, persistir=False)
    assert sin_modelo.modelo_version == "elo-base"

    monkeypatch.setattr(pr, "MARGEN_SUPERIOR", -10)
    version = pr.entrenar()["version"]
    con_modelo = pr.PredictorResultados().predecir(nuevo, persistir=False)

    assert con_modelo.modelo_version == version and con_modelo.datos_suficientes is True
    assert con_modelo.confianza > sin_modelo.confianza          # un método validado merece más confianza
    # El equipo fuerte local contra el más débil debe ser favorito con cualquiera de los dos métodos.
    for p in (sin_modelo, con_modelo):
        assert p.prob_victoria_local > p.prob_victoria_visit
        assert abs(p.prob_victoria_local + p.prob_empate + p.prob_victoria_visit - 1) < 1e-3


def test_si_el_artefacto_del_modelo_se_pierde_se_degrada_a_elo(monkeypatch):
    campeonato, equipos, _ = liga_sintetica(vueltas=3)
    monkeypatch.setattr(pr, "MARGEN_SUPERIOR", -10)
    pr.entrenar()
    ModeloML.objects.update(ruta_artefacto="/no/existe.joblib")
    pr._cache.clear()

    p = pr.PredictorResultados().predecir(partido_futuro(campeonato, equipos[0], equipos[1]), persistir=False)

    assert p.modelo_version == "elo-base"


def test_goles_esperados_salen_del_historial_y_no_de_la_probabilidad():
    campeonato, equipos, _ = liga_sintetica(vueltas=3)
    p = pr.PredictorResultados().predecir(partido_futuro(campeonato, equipos[0], equipos[-1]), persistir=False)

    assert p.goles_local_pred > p.goles_visit_pred > 0   # el equipo 0 es el más ofensivo y el último el más débil


# ── API ───────────────────────────────────────────────────────────────────────

def test_api_tablero_informa_datos_suficientes_y_modelo_sin_escribir():
    campeonato, equipos, _ = liga_sintetica(vueltas=3)
    partido_futuro(campeonato, equipos[0], equipos[1])
    org = cliente_de(crear_usuario(Usuario.Rol.ORGANIZADOR))

    r = org.get(reverse("ml-tablero"), {"campeonato": campeonato.pk})

    assert r.status_code == 200 and len(r.data) == 1
    fila = r.data[0]
    assert fila["datos_suficientes"] is True and fila["modelo"] == "elo-base"
    assert abs(fila["prob_local"] + fila["prob_empate"] + fila["prob_visitante"] - 100) < 0.5
    assert not PrediccionPartido.objects.exists() and not Bitacora.objects.exists()


def test_api_entrenar_es_solo_del_administrador_y_audita():
    liga_sintetica(vueltas=3)
    url = reverse("ml-entrenar")
    admin = cliente_de(crear_usuario(Usuario.Rol.ADMIN_DUBSS))
    org = cliente_de(crear_usuario(Usuario.Rol.ORGANIZADOR))
    delegado = cliente_de(crear_usuario(Usuario.Rol.DELEGADO))

    assert org.post(url).status_code == 403 and delegado.post(url).status_code == 403
    r = admin.post(url)

    assert r.status_code == 200 and r.data["entrenado"] is True
    assert Bitacora.objects.filter(accion=Bitacora.Accion.ML_PRED, modulo="ml", resultado="OK").exists()
    informe = org.get(url)
    assert informe.status_code == 200 and informe.data["version"] == r.data["version"]
    assert delegado.get(url).status_code == 403


def test_api_entrenar_sin_datos_devuelve_400_claro():
    admin = cliente_de(crear_usuario(Usuario.Rol.ADMIN_DUBSS))

    r = admin.post(reverse("ml-entrenar"))

    assert r.status_code == 400 and "Datos insuficientes" in r.data["motivo"]
    assert Bitacora.objects.filter(accion=Bitacora.Accion.ML_PRED, resultado="ERROR").exists()
