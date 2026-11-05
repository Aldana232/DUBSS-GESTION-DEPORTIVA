"""
apps/ml/services/asignacion_scorer.py
RF11 — Puntuador de asignaciones con Random Forest (scikit-learn).

Una *asignación* es "este partido se juega en esta instalación, a esta hora y en este día".
El modelo recibe las variables que pide el documento (franja horaria, día de la semana,
días desde el último partido de cada equipo, disponibilidad de la instalación y conflictos
de horario, más la holgura con las restricciones de facultad) y devuelve la probabilidad de
que sea una **buena asignación**. El optimizador (OR-Tools CP-SAT) garantiza las restricciones
duras y usa este puntaje para elegir, entre las asignaciones posibles, las mejores.

Datos de entrenamiento (`MuestraAsignacion`)
* ARRANQUE EN FRÍO (origen REGLAS): mientras no hay historial, las muestras se etiquetan con
  las reglas explícitas de `puntaje_por_reglas` (documentadas abajo). Las métricas de ese
  modelo miden cuánto aprendió de las reglas, NO la calidad real de un torneo.
* HISTORIAL (origen REAL): partidos reales ya jugados. Un partido finalizado con normalidad
  es una asignación BUENA; uno suspendido, postergado o resuelto por W.O. es MALA. Con ellos
  `reentrenar()` ajusta el modelo a la realidad de la DUBSS (se ponderan más que las reglas).
"""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import joblib
import numpy as np
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

from apps.ml.models import MuestraAsignacion

logger = logging.getLogger(__name__)

MODEL_DIR = Path(settings.BASE_DIR) / "apps" / "ml" / "models_trained"
MODEL_PATH = MODEL_DIR / "asignacion_scorer.joblib"

FEATURES = [
    "franja_horaria", "dia_semana", "es_fin_de_semana",
    "dias_desde_ultimo_local", "dias_desde_ultimo_visit", "descanso_minimo",
    "instalacion_disponible", "conflictos_horario", "holgura_facultad_min",
]
VERSION_REGLAS = "2026-10-30"  # subir al cambiar las reglas: invalida los modelos entrenados con otras
UMBRAL_BUENA = 0.9          # puntaje por reglas desde el cual una asignación es BUENA (franja ideal)
SIN_PARTIDOS_PREVIOS = 30   # "días desde el último partido" cuando el equipo no tiene historial
HOLGURA_MAXIMA = 240        # minutos; sin restricciones de facultad cerca = holgura máxima
PESO_MUESTRA_REAL = 5.0     # un partido real pesa más que una muestra de reglas
MIN_MUESTRAS_REALES = 30    # por debajo, el reentrenamiento sigue apoyándose en las reglas


class ModeloNoDisponible(RuntimeError):
    """No se pudo entrenar o cargar el puntuador (datos insuficientes o inconsistentes)."""


@dataclass(frozen=True)
class Asignacion:
    franja_horaria: int
    dia_semana: int
    dias_desde_ultimo_local: int = SIN_PARTIDOS_PREVIOS
    dias_desde_ultimo_visit: int = SIN_PARTIDOS_PREVIOS
    instalacion_disponible: bool = True
    conflictos_horario: int = 0
    holgura_facultad_min: int = HOLGURA_MAXIMA

    def vector(self) -> list[float]:
        return [
            self.franja_horaria,
            self.dia_semana,
            1.0 if self.dia_semana >= 5 else 0.0,
            self.dias_desde_ultimo_local,
            self.dias_desde_ultimo_visit,
            min(self.dias_desde_ultimo_local, self.dias_desde_ultimo_visit),
            1.0 if self.instalacion_disponible else 0.0,
            self.conflictos_horario,
            self.holgura_facultad_min,
        ]


# ─── Reglas explícitas del arranque en frío ───────────────────────────────────

def puntaje_por_reglas(a: Asignacion) -> float:
    """
    Puntaje 0-1 de una asignación según las reglas de la DUBSS usadas en el arranque en frío.

    * Franja (30 %): 10-17 h ideal; 8-9 h y 18-19 h aceptable; antes de las 8 o desde las 20 h mala.
    * Descanso (25 %): menos de 1 día = 0; 1 día = 0,3; 2-3 días = 0,8; 4 o más = 1.
    * Conflictos con otros partidos de la misma instalación (20 %): cada uno resta 35 %.
    * Holgura con restricciones de facultad (15 %): menos de 30 min = 0,2; menos de 60 min = 0,6.
    * Día (10 %): sábado 1,0; lunes a viernes 0,9; domingo 0,5.
    * Instalación no disponible: el puntaje se reduce al 20 %.
    """
    h = a.franja_horaria
    franja = 1.0 if 10 <= h <= 17 else 0.6 if h in (8, 9, 18, 19) else 0.1
    dia = {5: 1.0, 6: 0.5}.get(a.dia_semana, 0.9)
    r = min(a.dias_desde_ultimo_local, a.dias_desde_ultimo_visit)
    descanso = 0.0 if r < 1 else 0.3 if r < 2 else 0.8 if r < 4 else 1.0
    holgura = 0.2 if a.holgura_facultad_min < 30 else 0.6 if a.holgura_facultad_min < 60 else 1.0
    conflictos = max(0.0, 1.0 - 0.35 * a.conflictos_horario)
    puntaje = 0.30 * franja + 0.25 * descanso + 0.15 * holgura + 0.10 * dia + 0.20 * conflictos
    return puntaje if a.instalacion_disponible else puntaje * 0.2


def etiqueta_por_reglas(a: Asignacion) -> str:
    buena = a.instalacion_disponible and a.conflictos_horario == 0 and puntaje_por_reglas(a) >= UMBRAL_BUENA
    return MuestraAsignacion.Calidad.BUENA if buena else MuestraAsignacion.Calidad.MALA


def generar_asignaciones_de_arranque(n: int = 3000, semilla: int = 7) -> list[Asignacion]:
    """Asignaciones sintéticas distribuidas por todo el espacio de variables (reproducibles)."""
    rng = np.random.default_rng(semilla)
    filas = []
    for _ in range(n):
        filas.append(Asignacion(
            franja_horaria=int(rng.integers(6, 23)),
            dia_semana=int(rng.integers(0, 7)),
            dias_desde_ultimo_local=int(rng.choice([0, 1, 2, 3, 4, 5, 7, 10, 14, 21, 30], p=[.08, .1, .1, .1, .1, .12, .14, .1, .06, .04, .06])),
            dias_desde_ultimo_visit=int(rng.choice([0, 1, 2, 3, 4, 5, 7, 10, 14, 21, 30], p=[.08, .1, .1, .1, .1, .12, .14, .1, .06, .04, .06])),
            instalacion_disponible=bool(rng.random() > 0.1),
            conflictos_horario=int(rng.choice([0, 1, 2, 3], p=[.6, .22, .12, .06])),
            holgura_facultad_min=int(rng.choice([0, 15, 30, 45, 60, 90, 120, 240], p=[.05, .05, .05, .05, .1, .1, .1, .5])),
        ))
    return filas


def _a_muestra(a: Asignacion, origen: str, calidad: str, **extra) -> MuestraAsignacion:
    return MuestraAsignacion(
        equipo_local_id=extra.pop("equipo_local_id", 0),
        equipo_visitante_id=extra.pop("equipo_visitante_id", 0),
        instalacion_id=extra.pop("instalacion_id", 0),
        franja_horaria=a.franja_horaria,
        dia_semana=a.dia_semana,
        dias_desde_ultimo_local=a.dias_desde_ultimo_local,
        dias_desde_ultimo_visit=a.dias_desde_ultimo_visit,
        instalacion_disponible=a.instalacion_disponible,
        conflictos_horario=a.conflictos_horario,
        holgura_facultad_min=a.holgura_facultad_min,
        calidad=calidad,
        origen=origen,
        **extra,
    )


def _a_asignacion(m: MuestraAsignacion) -> Asignacion:
    return Asignacion(
        franja_horaria=m.franja_horaria,
        dia_semana=m.dia_semana,
        dias_desde_ultimo_local=m.dias_desde_ultimo_local,
        dias_desde_ultimo_visit=m.dias_desde_ultimo_visit,
        instalacion_disponible=m.instalacion_disponible,
        conflictos_horario=m.conflictos_horario,
        holgura_facultad_min=m.holgura_facultad_min,
    )


@transaction.atomic
def sembrar_muestras_de_arranque(n: int = 3000, semilla: int = 7) -> int:
    """Reemplaza las muestras de reglas por un lote nuevo (las reales no se tocan)."""
    MuestraAsignacion.objects.filter(origen=MuestraAsignacion.Origen.REGLAS).delete()
    MuestraAsignacion.objects.bulk_create(
        [_a_muestra(a, MuestraAsignacion.Origen.REGLAS, etiqueta_por_reglas(a))
         for a in generar_asignaciones_de_arranque(n, semilla)],
        batch_size=1000,
    )
    return n


# ─── Modelo ───────────────────────────────────────────────────────────────────

class AsignacionScorer:
    """Envoltura del RandomForest: puntúa lotes de asignaciones y conoce su versión y métricas."""

    def __init__(self, modelo: RandomForestClassifier, version: str, metricas: dict):
        self.modelo = modelo
        self.version = version
        self.metricas = metricas

    def puntuar_lote(self, matriz: np.ndarray) -> np.ndarray:
        """Probabilidad (0-1) de "buena asignación" para cada fila de `matriz` (n × len(FEATURES))."""
        if len(matriz) == 0:
            return np.zeros(0)
        clases = list(self.modelo.classes_)
        return self.modelo.predict_proba(matriz)[:, clases.index(1)]

    def puntuar(self, asignaciones: list[Asignacion]) -> np.ndarray:
        return self.puntuar_lote(np.array([a.vector() for a in asignaciones], dtype=float))

    def info(self) -> dict:
        return {"version": self.version, "features": FEATURES, **self.metricas}


def _entrenar(muestras: list[MuestraAsignacion]) -> AsignacionScorer:
    if len(muestras) < 50:
        raise ModeloNoDisponible("Datos insuficientes para entrenar el puntuador (mínimo 50 muestras).")
    X = np.array([_a_asignacion(m).vector() for m in muestras], dtype=float)
    y = np.array([1 if m.calidad == MuestraAsignacion.Calidad.BUENA else 0 for m in muestras])
    pesos = np.array([PESO_MUESTRA_REAL if m.origen == MuestraAsignacion.Origen.REAL else 1.0 for m in muestras])
    if len(set(y)) < 2:
        raise ModeloNoDisponible("Las muestras tienen una sola clase: no se puede entrenar el clasificador.")

    X_ent, X_val, y_ent, y_val, w_ent, _ = train_test_split(
        X, y, pesos, test_size=0.2, random_state=42, stratify=y
    )
    parametros = dict(n_estimators=80, min_samples_leaf=4, max_depth=14,
                      class_weight="balanced", random_state=42, n_jobs=1)
    validacion = RandomForestClassifier(**parametros).fit(X_ent, y_ent, sample_weight=w_ent)
    pred = validacion.predict(X_val)
    proba = validacion.predict_proba(X_val)[:, list(validacion.classes_).index(1)]
    n_real = sum(1 for m in muestras if m.origen == MuestraAsignacion.Origen.REAL)

    # El modelo que se usa se reentrena con todo el lote; las métricas salen de la validación.
    modelo = RandomForestClassifier(**parametros).fit(X, y, sample_weight=pesos)
    metricas = {
        "muestras": len(muestras),
        "muestras_reales": n_real,
        "muestras_reglas": len(muestras) - n_real,
        "exactitud": round(float(accuracy_score(y_val, pred)), 4),
        "precision": round(float(precision_score(y_val, pred, zero_division=0)), 4),
        "sensibilidad": round(float(recall_score(y_val, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_val, pred, zero_division=0)), 4),
        "auc": round(float(roc_auc_score(y_val, proba)), 4),
        "importancias": {f: round(float(i), 4) for f, i in zip(FEATURES, modelo.feature_importances_)},
        "etiquetado": "historial real + reglas" if n_real >= MIN_MUESTRAS_REALES else "reglas de arranque en frío",
        "entrenado_en": timezone.now().isoformat(),
    }
    version = f"asignacion-rf-{timezone.now():%Y%m%d%H%M%S}"
    return AsignacionScorer(modelo, version, metricas)


def _guardar(scorer: AsignacionScorer) -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": scorer.modelo, "version": scorer.version, "metricas": scorer.metricas,
                 "features": FEATURES, "version_reglas": VERSION_REGLAS}, MODEL_PATH)
    (MODEL_DIR / "asignacion_scorer.json").write_text(
        json.dumps(scorer.info(), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _cargar() -> AsignacionScorer | None:
    if not MODEL_PATH.exists():
        return None
    try:
        datos = joblib.load(MODEL_PATH)
        if datos.get("features") != FEATURES or datos.get("version_reglas") != VERSION_REGLAS:
            return None  # variables o reglas distintas a las actuales: hay que reentrenar
        return AsignacionScorer(datos["modelo"], datos["version"], datos["metricas"])
    except Exception:  # archivo corrupto o de otra versión de scikit-learn
        logger.warning("No se pudo cargar el puntuador guardado; se reentrenará.", exc_info=True)
        return None


_cache: dict = {"scorer": None, "mtime": None}
_candado = threading.Lock()


def _invalidar_cache() -> None:
    _cache.update(scorer=None, mtime=None)


def entrenar_arranque_en_frio(n: int = 3000) -> AsignacionScorer:
    """Siembra muestras etiquetadas con reglas, entrena y guarda el puntuador."""
    with _candado:
        sembrar_muestras_de_arranque(n)
        scorer = _entrenar(list(MuestraAsignacion.objects.all()))
        _guardar(scorer)
        _invalidar_cache()
    return scorer


def obtener_scorer() -> AsignacionScorer:
    """
    Devuelve el puntuador listo para usar. Si todavía no hay modelo entrenado (precondición del
    RF11) lo entrena con el arranque en frío. Lanza ModeloNoDisponible si no es posible.
    """
    with _candado:
        mtime = MODEL_PATH.stat().st_mtime if MODEL_PATH.exists() else None
        if _cache["scorer"] is not None and _cache["mtime"] == mtime:
            return _cache["scorer"]
        scorer = _cargar()
    if scorer is None:
        try:
            scorer = entrenar_arranque_en_frio()
        except ModeloNoDisponible:
            raise
        except Exception as e:  # noqa: BLE001 - cualquier fallo de entrenamiento debe degradar con aviso
            raise ModeloNoDisponible(f"No se pudo entrenar el modelo de asignación: {e}") from e
    with _candado:
        _cache.update(scorer=scorer, mtime=MODEL_PATH.stat().st_mtime if MODEL_PATH.exists() else None)
    return scorer


# ─── Historial real y reentrenamiento ─────────────────────────────────────────

def asignacion_de_partido(partido) -> Asignacion | None:
    """Reconstruye las variables de un partido ya programado. None si le faltan equipos o cancha."""
    from django.db.models import Q

    from apps.deportes.models import RestriccionHorarioFacultad
    from apps.fixture.models import Partido

    if not (partido.equipo_local_id and partido.equipo_visitante_id and partido.cancha_id):
        return None
    inicio = timezone.localtime(partido.fecha_hora)

    def dias_desde_ultimo(equipo_id):
        previo = (
            Partido.objects.filter(Q(equipo_local_id=equipo_id) | Q(equipo_visitante_id=equipo_id),
                                   fecha_hora_fin__lte=partido.fecha_hora)
            .exclude(pk=partido.pk).order_by("-fecha_hora_fin").first()
        )
        if previo is None:
            return SIN_PARTIDOS_PREVIOS
        return min(SIN_PARTIDOS_PREVIOS, (inicio.date() - timezone.localtime(previo.fecha_hora_fin).date()).days)

    holgura = HOLGURA_MAXIMA
    for equipo in (partido.equipo_local, partido.equipo_visitante):
        for r in RestriccionHorarioFacultad.objects.filter(facultad_id=equipo.facultad_id, dia_semana=inicio.weekday()):
            ini = inicio.replace(hour=r.hora_inicio.hour, minute=r.hora_inicio.minute, second=0, microsecond=0)
            fin = inicio.replace(hour=r.hora_fin.hour, minute=r.hora_fin.minute, second=0, microsecond=0)
            distancia = max(0, int((ini - timezone.localtime(partido.fecha_hora_fin)).total_seconds() // 60),
                            int((inicio - fin).total_seconds() // 60))
            holgura = min(holgura, distancia)
    margen = timedelta(minutes=60)
    conflictos = (
        Partido.objects.filter(instalacion_id=partido.instalacion_id, fecha_hora__lt=partido.fecha_hora_fin + margen,
                               fecha_hora_fin__gt=partido.fecha_hora - margen)
        .exclude(pk=partido.pk).exclude(cancha_id=partido.cancha_id).count()
    )
    return Asignacion(
        franja_horaria=inicio.hour, dia_semana=inicio.weekday(),
        dias_desde_ultimo_local=dias_desde_ultimo(partido.equipo_local_id),
        dias_desde_ultimo_visit=dias_desde_ultimo(partido.equipo_visitante_id),
        instalacion_disponible=True, conflictos_horario=conflictos, holgura_facultad_min=holgura,
    )


def sincronizar_muestras_reales() -> int:
    """
    Convierte en muestras REAL los partidos cuyo desenlace ya se conoce (idempotente: una por partido).
    FINALIZADO = BUENA; SUSPENDIDO, POSTERGADO o W.O. = MALA. Devuelve cuántas muestras nuevas creó.
    """
    from apps.fixture.models import Partido

    ya = set(MuestraAsignacion.objects.filter(partido_id__isnull=False).values_list("partido_id", flat=True))
    estados = {Partido.Estado.FINALIZADO: "BUENA", Partido.Estado.SUSPENDIDO: "MALA",
               Partido.Estado.POSTERGADO: "MALA", Partido.Estado.WALKOVER: "MALA"}
    nuevas = []
    for p in Partido.objects.filter(estado__in=list(estados)).select_related("equipo_local", "equipo_visitante").exclude(pk__in=ya):
        a = asignacion_de_partido(p)
        if a is None:
            continue
        nuevas.append(_a_muestra(a, MuestraAsignacion.Origen.REAL, estados[p.estado], equipo_local_id=p.equipo_local_id,
                                 equipo_visitante_id=p.equipo_visitante_id, instalacion_id=p.instalacion_id or 0,
                                 partido_id=p.pk))
    MuestraAsignacion.objects.bulk_create(nuevas)
    return len(nuevas)


def reentrenar() -> AsignacionScorer:
    """Suma al dataset los partidos reales nuevos y reentrena con todo (reglas + historial)."""
    with _candado:
        nuevas = sincronizar_muestras_reales()
        if not MuestraAsignacion.objects.filter(origen=MuestraAsignacion.Origen.REGLAS).exists():
            sembrar_muestras_de_arranque()
        scorer = _entrenar(list(MuestraAsignacion.objects.all()))
        scorer.metricas["muestras_reales_nuevas"] = nuevas
        _guardar(scorer)
        _invalidar_cache()
    return scorer


def info_modelo() -> dict:
    """Estado del puntuador sin entrenarlo: `entrenado` indica si ya existe un modelo guardado."""
    scorer = _cargar()
    if scorer is None:
        return {"entrenado": False, "features": FEATURES}
    return {"entrenado": True, **scorer.info()}


__all__ = [
    "Asignacion", "AsignacionScorer", "FEATURES", "HOLGURA_MAXIMA", "ModeloNoDisponible",
    "SIN_PARTIDOS_PREVIOS",
]
