"""F5b-01/02 — Muestras y puntuador de asignaciones (Random Forest)."""
import numpy as np
import pytest
from django.utils import timezone

from apps.fixture.models import Partido
from apps.fixture.tests.helpers import crear_escenario
from apps.ml.models import MuestraAsignacion
from apps.ml.services import asignacion_scorer as sc
from apps.ml.services.asignacion_scorer import Asignacion

pytestmark = pytest.mark.django_db


def buena(**cambios):
    base = dict(franja_horaria=12, dia_semana=2, dias_desde_ultimo_local=7, dias_desde_ultimo_visit=7,
                instalacion_disponible=True, conflictos_horario=0, holgura_facultad_min=240)
    return Asignacion(**{**base, **cambios})


# ── Reglas explícitas del arranque en frío ────────────────────────────────────

def test_las_reglas_distinguen_buenas_y_malas_asignaciones():
    assert sc.etiqueta_por_reglas(buena()) == "BUENA"
    assert sc.etiqueta_por_reglas(buena(franja_horaria=22)) == "MALA"            # muy tarde
    assert sc.etiqueta_por_reglas(buena(franja_horaria=6)) == "MALA"             # muy temprano
    assert sc.etiqueta_por_reglas(buena(dias_desde_ultimo_local=0)) == "MALA"    # sin descanso
    assert sc.etiqueta_por_reglas(buena(conflictos_horario=1)) == "MALA"
    assert sc.etiqueta_por_reglas(buena(instalacion_disponible=False)) == "MALA"
    assert sc.etiqueta_por_reglas(buena(holgura_facultad_min=10)) == "MALA" or \
        sc.puntaje_por_reglas(buena(holgura_facultad_min=10)) < sc.puntaje_por_reglas(buena())


def test_el_puntaje_por_reglas_esta_entre_0_y_1_y_es_monotono_en_el_descanso():
    puntajes = [sc.puntaje_por_reglas(buena(dias_desde_ultimo_local=d, dias_desde_ultimo_visit=d)) for d in (0, 1, 2, 4, 10)]
    assert puntajes == sorted(puntajes)
    assert all(0 <= p <= 1 for p in puntajes)


def test_las_muestras_de_arranque_son_reproducibles_y_estan_balanceadas():
    a = sc.generar_asignaciones_de_arranque(500, semilla=3)
    b = sc.generar_asignaciones_de_arranque(500, semilla=3)
    etiquetas = [sc.etiqueta_por_reglas(x) for x in a]
    assert a == b
    assert 0.08 < etiquetas.count("BUENA") / len(etiquetas) < 0.7   # minoritaria pero suficiente


# ── Entrenamiento ─────────────────────────────────────────────────────────────

def test_arranque_en_frio_siembra_entrena_guarda_y_reporta_metricas():
    scorer = sc.entrenar_arranque_en_frio(800)

    assert MuestraAsignacion.objects.filter(origen="REGLAS").count() == 800
    assert sc.MODEL_PATH.exists()
    m = scorer.metricas
    assert m["exactitud"] > 0.9 and m["f1"] > 0.85 and m["auc"] > 0.95
    assert m["etiquetado"] == "reglas de arranque en frío"
    assert set(m["importancias"]) == set(sc.FEATURES)
    assert sc.info_modelo()["version"] == scorer.version


def test_el_modelo_puntua_mejor_los_buenos_horarios():
    scorer = sc.obtener_scorer()

    p = scorer.puntuar([buena(), buena(franja_horaria=22), buena(dias_desde_ultimo_local=0),
                        buena(conflictos_horario=3), buena(instalacion_disponible=False)])

    assert p[0] > 0.8
    assert all(p[0] > otro for otro in p[1:])
    assert ((p >= 0) & (p <= 1)).all()


def test_puntuar_lote_vacio_y_matriz():
    scorer = sc.obtener_scorer()
    assert len(scorer.puntuar_lote(np.zeros((0, len(sc.FEATURES))))) == 0
    assert scorer.puntuar_lote(np.array([buena().vector()])).shape == (1,)


def test_obtener_scorer_entrena_si_falta_y_reutiliza_el_guardado():
    if sc.MODEL_PATH.exists():
        sc.MODEL_PATH.unlink()
    sc._invalidar_cache()

    primero = sc.obtener_scorer()
    segundo = sc.obtener_scorer()

    assert sc.MODEL_PATH.exists() and primero.version == segundo.version


def test_un_modelo_guardado_con_otras_variables_se_reentrena():
    import joblib

    sc.obtener_scorer()
    datos = joblib.load(sc.MODEL_PATH)
    joblib.dump({**datos, "features": ["otra"]}, sc.MODEL_PATH)
    sc._invalidar_cache()

    assert sc._cargar() is None
    assert sc.obtener_scorer().info()["features"] == sc.FEATURES


def test_datos_insuficientes_o_de_una_sola_clase_lanzan_error_claro():
    muestras = [sc._a_muestra(buena(), "REGLAS", "BUENA") for _ in range(10)]
    with pytest.raises(sc.ModeloNoDisponible, match="insuficientes"):
        sc._entrenar(muestras)
    with pytest.raises(sc.ModeloNoDisponible, match="una sola clase"):
        sc._entrenar([sc._a_muestra(buena(), "REGLAS", "BUENA") for _ in range(80)])


# ── Historial real y reentrenamiento ──────────────────────────────────────────

def _fixture_con_desenlaces():
    esc = crear_escenario(equipos=4, canchas=2)
    from apps.fixture.services.fixture_generator import FixtureGenerator
    partidos = FixtureGenerator(esc.campeonato.pk).generar()
    estados = [Partido.Estado.FINALIZADO, Partido.Estado.SUSPENDIDO, Partido.Estado.WALKOVER, Partido.Estado.PROGRAMADO,
               Partido.Estado.FINALIZADO, Partido.Estado.POSTERGADO]
    for p, e in zip(partidos, estados):
        Partido.objects.filter(pk=p.pk).update(estado=e)
    return partidos


def test_las_muestras_reales_salen_del_desenlace_de_los_partidos_y_son_idempotentes():
    _fixture_con_desenlaces()

    nuevas = sc.sincronizar_muestras_reales()
    otra_vez = sc.sincronizar_muestras_reales()

    reales = MuestraAsignacion.objects.filter(origen="REAL")
    assert nuevas == 5 and otra_vez == 0           # el PROGRAMADO no cuenta: aún no tiene desenlace
    assert reales.filter(calidad="BUENA").count() == 2
    assert reales.filter(calidad="MALA").count() == 3
    assert not reales.filter(partido_id__isnull=True).exists()


def test_reentrenar_incluye_el_historial_real_y_guarda_la_nueva_version():
    sc.entrenar_arranque_en_frio(600)
    anterior = sc.obtener_scorer().version
    _fixture_con_desenlaces()

    scorer = sc.reentrenar()

    assert scorer.metricas["muestras_reales"] == 5 and scorer.metricas["muestras_reales_nuevas"] == 5
    assert scorer.version != anterior and sc.info_modelo()["version"] == scorer.version


def test_asignacion_de_partido_reconstruye_las_variables():
    p = _fixture_con_desenlaces()[0]
    p.refresh_from_db()

    a = sc.asignacion_de_partido(p)

    assert a.franja_horaria == timezone.localtime(p.fecha_hora).hour
    assert a.dias_desde_ultimo_local == sc.SIN_PARTIDOS_PREVIOS   # es su primer partido
    assert a.instalacion_disponible is True


def test_un_modelo_entrenado_con_otras_reglas_se_descarta_y_reentrena():
    import joblib

    sc.obtener_scorer()
    datos = joblib.load(sc.MODEL_PATH)
    joblib.dump({**datos, "version_reglas": "antigua"}, sc.MODEL_PATH)
    sc._invalidar_cache()

    assert sc._cargar() is None
    assert sc.obtener_scorer().metricas["etiquetado"] == "reglas de arranque en frío"
    assert joblib.load(sc.MODEL_PATH)["version_reglas"] == sc.VERSION_REGLAS
