"""
apps/ml/services/predictor.py
RF15 / F6-01 — Predicción de resultados (local / empate / visitante).

Diseño honesto:
* Las características se calculan A LA FECHA de cada partido, repasando el historial en orden
  cronológico: nunca se usa información posterior al partido (sin fuga de datos).
  Elo, forma reciente (puntos de los últimos 5), goles a favor y en contra (últimos 10), descanso,
  enfrentamientos previos y local/visitante. El historial se separa por deporte.
* Validación temporal *walk-forward*: se entrena con el pasado y se evalúa con el futuro, en
  varios cortes. Se mide accuracy, log-loss, Brier y calibración (ECE), y se compara contra dos
  líneas base: «frecuencia de clases» (siempre el resultado más común) y «Elo».
* El modelo de ML solo se ACTIVA si supera a las dos líneas base en log-loss; si no, se registra
  igualmente (con su informe) pero la inferencia usa Elo. Con pocos partidos se responde con
  `datos_suficientes=False` y confianza baja, sin simular precisión que no existe.
* Cada entrenamiento queda en `ml.ModeloML` (versión, métricas, huella de los datos, artefacto).
"""
from __future__ import annotations

import hashlib
import logging
from collections import defaultdict, deque
from pathlib import Path

import joblib
import numpy as np
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import TimeSeriesSplit

from apps.fixture.models import Partido
from apps.ml.models import ModeloML, PrediccionPartido

logger = logging.getLogger(__name__)

NOMBRE_MODELO = "predictor_resultados"
MODEL_DIR = Path(settings.BASE_DIR) / "apps" / "ml" / "models_trained"

CLASES = ("local", "empate", "visitante")      # índices 0, 1, 2
ELO_INICIAL = 1500.0
ELO_K = 24.0
VENTAJA_LOCAL_ELO = 60.0
MIN_PARTIDOS_ENTRENAMIENTO = 30   # partidos finalizados necesarios para entrenar
MIN_PARTIDOS_EQUIPO = 3           # partidos previos de cada equipo para hablar de «datos suficientes»
MARGEN_SUPERIOR = 0.005           # el modelo debe mejorar el log-loss de las bases por al menos esto
SIN_DESCANSO = 30.0

FEATURES = [
    "elo_local", "elo_visitante", "elo_diferencia",
    "forma_local", "forma_visitante",
    "gf_local", "gc_local", "gf_visitante", "gc_visitante",
    "descanso_local", "descanso_visitante",
    "h2h", "partidos_local", "partidos_visitante",
]


# ─── Historial cronológico (estado a una fecha) ───────────────────────────────

class _Equipo:
    __slots__ = ("elo", "jugados", "forma", "gf", "gc", "ultimo")

    def __init__(self):
        self.elo = ELO_INICIAL
        self.jugados = 0
        self.forma = deque(maxlen=5)     # puntos de los últimos 5 partidos (3/1/0)
        self.gf = deque(maxlen=10)
        self.gc = deque(maxlen=10)
        self.ultimo = None               # fecha del último partido


class Historial:
    """Estado de todos los equipos tras repasar, en orden, los partidos ya jugados."""

    def __init__(self):
        self.equipos: dict[tuple[int, int], _Equipo] = defaultdict(_Equipo)
        self.h2h: dict[tuple, deque] = defaultdict(lambda: deque(maxlen=5))
        self.goles_por_equipo: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])  # deporte -> [goles, equipos·partidos]
        self.empates = 0
        self.total = 0

    def equipo(self, deporte_id, equipo_id) -> _Equipo:
        return self.equipos[(deporte_id, equipo_id)]

    def vector(self, deporte_id, local_id, visit_id, fecha) -> list[float]:
        l, v = self.equipo(deporte_id, local_id), self.equipo(deporte_id, visit_id)

        def media(valores, defecto):
            return sum(valores) / len(valores) if valores else defecto

        media_liga = self.media_goles(deporte_id)
        clave = (deporte_id, frozenset((local_id, visit_id)))
        h2h = list(self.h2h[clave])
        saldo = sum(1 if g == local_id else -1 if g == visit_id else 0 for g in h2h)

        def descanso(e):
            return min(SIN_DESCANSO, (fecha - e.ultimo).total_seconds() / 86400) if e.ultimo else SIN_DESCANSO

        return [
            l.elo, v.elo, l.elo - v.elo,
            media(l.forma, 1.0), media(v.forma, 1.0),
            media(l.gf, media_liga), media(l.gc, media_liga), media(v.gf, media_liga), media(v.gc, media_liga),
            descanso(l), descanso(v),
            saldo / len(h2h) if h2h else 0.0,
            l.jugados, v.jugados,
        ]

    def media_goles(self, deporte_id) -> float:
        goles, n = self.goles_por_equipo[deporte_id]
        return goles / n if n else 0.0

    def actualizar(self, deporte_id, local_id, visit_id, goles_l, goles_v, fecha) -> None:
        l, v = self.equipo(deporte_id, local_id), self.equipo(deporte_id, visit_id)
        esperado = 1 / (1 + 10 ** (-(l.elo + VENTAJA_LOCAL_ELO - v.elo) / 400))
        real = 1.0 if goles_l > goles_v else 0.5 if goles_l == goles_v else 0.0
        k = ELO_K * (1 + 0.25 * min(abs(goles_l - goles_v), 4))
        l.elo += k * (real - esperado)
        v.elo -= k * (real - esperado)
        for e, gf, gc in ((l, goles_l, goles_v), (v, goles_v, goles_l)):
            e.jugados += 1
            e.forma.append(3 if gf > gc else 1 if gf == gc else 0)
            e.gf.append(gf)
            e.gc.append(gc)
            e.ultimo = fecha
        ganador = local_id if goles_l > goles_v else visit_id if goles_v > goles_l else 0
        self.h2h[(deporte_id, frozenset((local_id, visit_id)))].append(ganador)
        acumulado = self.goles_por_equipo[deporte_id]
        acumulado[0] += goles_l + goles_v
        acumulado[1] += 2
        self.total += 1
        self.empates += goles_l == goles_v


def _partidos_jugados():
    """Partidos finalizados con marcador real (los W.O. no miden nivel de juego), en orden cronológico."""
    return (
        Partido.objects.filter(
            estado=Partido.Estado.FINALIZADO, resultado__isnull=False, resultado__walkover=False,
            equipo_local__isnull=False, equipo_visitante__isnull=False,
        ).select_related("resultado", "campeonato__categoria").order_by("fecha_hora", "pk")
    )


def construir_dataset():
    """Repasa el historial una sola vez: devuelve X, y y el Historial final (para predecir partidos futuros)."""
    historial = Historial()
    X, y, ids, firma = [], [], [], hashlib.sha256()
    for p in _partidos_jugados():
        deporte = p.campeonato.categoria.deporte_id
        r = p.resultado
        X.append(historial.vector(deporte, p.equipo_local_id, p.equipo_visitante_id, p.fecha_hora))
        y.append(0 if r.goles_local > r.goles_visitante else 1 if r.goles_local == r.goles_visitante else 2)
        ids.append(p.pk)
        firma.update(f"{p.pk}:{r.goles_local}-{r.goles_visitante};".encode())
        historial.actualizar(deporte, p.equipo_local_id, p.equipo_visitante_id, r.goles_local, r.goles_visitante, p.fecha_hora)
    return np.array(X, dtype=float).reshape(-1, len(FEATURES)), np.array(y, dtype=int), historial, firma.hexdigest()


# ─── Líneas base y métricas ───────────────────────────────────────────────────

def probas_elo(elo_l: float, elo_v: float, tasa_empate: float) -> np.ndarray:
    """Probabilidades 3 clases a partir de Elo: el empate es más probable cuanto más parejos."""
    p_local = 1 / (1 + 10 ** (-(elo_l + VENTAJA_LOCAL_ELO - elo_v) / 400))
    p_emp = tasa_empate * (1 - 0.9 * abs(2 * p_local - 1))
    return np.array([(1 - p_emp) * p_local, p_emp, (1 - p_emp) * (1 - p_local)])


def _alinear(probas, clases) -> np.ndarray:
    """Devuelve (n, 3) con las columnas de las clases que el modelo vio (0 para las ausentes)."""
    salida = np.zeros((probas.shape[0], 3))
    for col, clase in enumerate(clases):
        salida[:, int(clase)] = probas[:, col]
    return salida


def _brier(P, y) -> float:
    Y = np.eye(3)[y]
    return float(np.mean(np.sum((P - Y) ** 2, axis=1)))


def _ece(P, y, bins: int = 10) -> float:
    confianza = P.max(axis=1)
    acierto = (P.argmax(axis=1) == y).astype(float)
    total, ece = len(y), 0.0
    for i in range(bins):
        inf, sup = i / bins, (i + 1) / bins
        m = (confianza > inf) & (confianza <= sup)
        if m.any():
            ece += m.sum() / total * abs(acierto[m].mean() - confianza[m].mean())
    return float(ece)


def _metricas(P, y) -> dict:
    P = np.clip(P, 1e-6, 1)
    P = P / P.sum(axis=1, keepdims=True)
    return {
        "accuracy": round(float(accuracy_score(y, P.argmax(axis=1))), 4),
        "log_loss": round(float(log_loss(y, P, labels=[0, 1, 2])), 4),
        "brier": round(_brier(P, y), 4),
        "ece": round(_ece(P, y), 4),
    }


def _nuevo_modelo():
    return RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=3, random_state=42, n_jobs=1)


def _ajustar(X, y, calibrar: bool):
    modelo = _nuevo_modelo()
    minimo_por_clase = min(np.bincount(y, minlength=3)[np.bincount(y, minlength=3) > 0])
    if calibrar and minimo_por_clase >= 4:
        try:
            return CalibratedClassifierCV(modelo, method="sigmoid", cv=3).fit(X, y), True
        except ValueError:
            logger.info("No se pudo calibrar; se usa el modelo sin calibrar.")
    return modelo.fit(X, y), False


# ─── Entrenamiento ────────────────────────────────────────────────────────────

def entrenar() -> dict:
    """
    Entrena con TODO el historial, valida *walk-forward* y registra el modelo. Devuelve el informe.
    No requiere campeonato: el historial de un equipo atraviesa campeonatos.
    """
    X, y, _, huella = construir_dataset()
    n = len(y)
    if n < MIN_PARTIDOS_ENTRENAMIENTO:
        return {
            "entrenado": False,
            "motivo": f"Datos insuficientes: hay {n} partidos finalizados y se necesitan al menos "
                      f"{MIN_PARTIDOS_ENTRENAMIENTO}. Mientras tanto se predice con Elo y confianza baja.",
            "partidos": n, "minimo": MIN_PARTIDOS_ENTRENAMIENTO,
        }

    cortes = max(2, min(5, n // 12))
    tasa_empate_global = float((y == 1).mean())
    P_modelo, P_freq, P_elo, y_test = [], [], [], []
    for entrenamiento, prueba in TimeSeriesSplit(n_splits=cortes).split(X):
        if len(set(y[entrenamiento])) < 2:
            continue
        modelo, _ = _ajustar(X[entrenamiento], y[entrenamiento], calibrar=len(entrenamiento) >= 60)
        P_modelo.append(_alinear(modelo.predict_proba(X[prueba]), modelo.classes_))
        frecuencia = np.bincount(y[entrenamiento], minlength=3) / len(entrenamiento)
        P_freq.append(np.tile(frecuencia, (len(prueba), 1)))
        tasa = float((y[entrenamiento] == 1).mean()) or tasa_empate_global
        P_elo.append(np.array([probas_elo(f[0], f[1], max(0.03, min(0.4, tasa))) for f in X[prueba]]))
        y_test.append(y[prueba])
    if not y_test:
        return {"entrenado": False, "motivo": "El historial tiene una sola clase de resultado: no se puede validar.",
                "partidos": n, "minimo": MIN_PARTIDOS_ENTRENAMIENTO}

    y_test = np.concatenate(y_test)
    m_modelo = _metricas(np.vstack(P_modelo), y_test)
    m_freq = _metricas(np.vstack(P_freq), y_test)
    m_elo = _metricas(np.vstack(P_elo), y_test)
    mejor_base = min(m_freq["log_loss"], m_elo["log_loss"])
    supera = m_modelo["log_loss"] < mejor_base - MARGEN_SUPERIOR

    final, calibrado = _ajustar(X, y, calibrar=n >= 60)
    version = f"rf-{timezone.now():%Y%m%d%H%M%S}"
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    ruta = MODEL_DIR / f"{NOMBRE_MODELO}-{version}.joblib"
    joblib.dump({"modelo": final, "features": FEATURES, "version": version,
                 "tasa_empate": float(np.clip(tasa_empate_global, 0.03, 0.4))}, ruta)

    metricas = {
        "partidos": n, "partidos_validacion": int(len(y_test)), "cortes_walk_forward": cortes, "calibrado": calibrado,
        "modelo": m_modelo, "linea_base_frecuencia": m_freq, "linea_base_elo": m_elo,
        "supera_linea_base": bool(supera),
        "conclusion": (
            "El modelo supera a las líneas base en log-loss y queda activo."
            if supera else
            "El modelo NO supera a las líneas base con los datos actuales: se usa Elo hasta que haya más historial."
        ),
        "importancias": _importancias(final),
    }
    with transaction.atomic():
        ModeloML.objects.filter(nombre=NOMBRE_MODELO, activo=True).update(activo=False)
        registro = ModeloML.objects.create(
            nombre=NOMBRE_MODELO, version=version, metricas=metricas, hash_datos=huella,
            ruta_artefacto=str(ruta), activo=bool(supera),
        )
    _cache.clear()
    return {"entrenado": True, "activo": registro.activo, "version": version, "hash_datos": huella, **metricas}


def _importancias(modelo) -> dict:
    base = getattr(modelo, "feature_importances_", None)
    if base is None:  # CalibratedClassifierCV: promedia los estimadores internos
        arboles = [c.estimator.feature_importances_ for c in modelo.calibrated_classifiers_]
        base = np.mean(arboles, axis=0)
    return {f: round(float(i), 4) for f, i in sorted(zip(FEATURES, base), key=lambda t: -t[1])}


# ─── Inferencia ───────────────────────────────────────────────────────────────

_cache: dict = {}


def _modelo_activo():
    """Modelo activo en memoria (se recarga si cambia el registro). None si no hay uno validado."""
    registro = ModeloML.objects.filter(nombre=NOMBRE_MODELO, activo=True).first()
    if registro is None:
        return None
    if _cache.get("id") != registro.pk:
        try:
            _cache.clear()
            _cache.update(id=registro.pk, datos=joblib.load(registro.ruta_artefacto), version=registro.version)
        except Exception:  # noqa: BLE001 - artefacto perdido o corrupto: se degrada a Elo
            logger.warning("No se pudo cargar el modelo activo %s; se usa Elo.", registro.version, exc_info=True)
            return None
    return _cache


class PredictorResultados:
    """Predice un partido programado con el historial disponible a hoy."""

    def __init__(self):
        self._historial = None

    def historial(self) -> Historial:
        if self._historial is None:
            self._historial = construir_dataset()[2]
        return self._historial

    def predecir(self, partido: Partido, *, persistir: bool = True) -> PrediccionPartido:
        h = self.historial()
        deporte = partido.campeonato.categoria.deporte_id
        fecha = partido.fecha_hora
        vector = np.array([h.vector(deporte, partido.equipo_local_id, partido.equipo_visitante_id, fecha)])
        l = h.equipo(deporte, partido.equipo_local_id)
        v = h.equipo(deporte, partido.equipo_visitante_id)

        modelo = _modelo_activo()
        tasa = (h.empates / h.total) if h.total >= 10 else 0.22
        tasa = max(0.03, min(0.4, tasa))
        if modelo is not None:
            probas = _alinear(modelo["datos"]["modelo"].predict_proba(vector), modelo["datos"]["modelo"].classes_)[0]
            version = modelo["version"]
        else:
            probas = probas_elo(vector[0][0], vector[0][1], tasa)
            version = "elo-base"
        probas = probas / probas.sum()

        datos_suficientes = min(l.jugados, v.jugados) >= MIN_PARTIDOS_EQUIPO
        # Confianza = cuánta evidencia hay (partidos de ambos equipos) × qué tan validado está el método.
        confianza = round(min(1.0, min(l.jugados, v.jugados) / 8) * (0.9 if modelo is not None else 0.6), 3)

        media = h.media_goles(deporte)
        esperado_l = (np.mean(list(l.gf)) + np.mean(list(v.gc))) / 2 if l.gf and v.gc else media
        esperado_v = (np.mean(list(v.gf)) + np.mean(list(l.gc))) / 2 if v.gf and l.gc else media

        valores = {
            "prob_victoria_local": round(float(probas[0]), 4),
            "prob_empate": round(float(probas[1]), 4),
            "prob_victoria_visit": round(float(probas[2]), 4),
            "goles_local_pred": round(float(esperado_l), 1),
            "goles_visit_pred": round(float(esperado_v), 1),
            "confianza": confianza,
            "datos_suficientes": datos_suficientes,
            "modelo_version": version,
        }
        if not persistir:
            return PrediccionPartido(partido=partido, **valores)
        pred, _ = PrediccionPartido.objects.update_or_create(partido=partido, defaults=valores)
        return pred


def informe_modelo() -> dict:
    """Resumen para la interfaz: modelo activo, último entrenamiento y cuántos partidos hay."""
    ultimo = ModeloML.objects.filter(nombre=NOMBRE_MODELO).first()
    activo = ModeloML.objects.filter(nombre=NOMBRE_MODELO, activo=True).first()
    partidos = _partidos_jugados().count()
    base = {"partidos_disponibles": partidos, "minimo": MIN_PARTIDOS_ENTRENAMIENTO,
            "activo": activo.version if activo else None, "metodo_actual": activo.version if activo else "elo-base"}
    if ultimo is None:
        return {**base, "entrenado": False}
    return {**base, "entrenado": True, "version": ultimo.version, "fecha_entrenamiento": ultimo.fecha_entrenamiento,
            "es_activo": ultimo.activo, "hash_datos": ultimo.hash_datos, **ultimo.metricas}
