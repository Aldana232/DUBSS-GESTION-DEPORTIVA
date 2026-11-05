"""
apps/ml/services/atipicos.py
F7-08 — Detección de resultados atípicos con Isolation Forest.

Por cada deporte se aprende cómo son los marcadores habituales (goles totales, diferencia, goles de cada lado) y se
señalan los que quedan aislados. Para evitar falsas alarmas, un marcador solo se reporta si ADEMÁS se desvía de forma
clara en términos simples (z robusto con mediana y MAD) y la alerta explica por qué. Los walkover no cuentan.
"""
from __future__ import annotations

import logging

import numpy as np
from sklearn.ensemble import IsolationForest

from apps.fixture.models import Partido
from apps.ml.models import ResultadoAtipico

logger = logging.getLogger(__name__)

MIN_PARTIDOS = 20            # partidos finalizados de un deporte para poder hablar de «habitual»
UMBRAL_Z = 3.5               # desviación robusta mínima para explicar la alerta (un 3-3 NO es atípico; un 9-0 sí)
PISO_SIGMA = 1.0             # evita dividir por casi cero cuando casi todos los marcadores son iguales


def _sigma(valores: np.ndarray) -> float:
    mad = float(np.median(np.abs(valores - np.median(valores))))
    return max(1.4826 * mad, PISO_SIGMA)


def detectar(deporte_id: int) -> list[dict]:
    """Marcadores atípicos del deporte (lista vacía si no hay historial suficiente)."""
    partidos = list(
        Partido.objects.filter(estado=Partido.Estado.FINALIZADO, resultado__walkover=False, campeonato__categoria__deporte_id=deporte_id)
        .select_related("resultado", "equipo_local", "equipo_visitante").order_by("fecha_hora", "pk")
    )
    if len(partidos) < MIN_PARTIDOS:
        return []
    gl = np.array([p.resultado.goles_local for p in partidos], dtype=float)
    gv = np.array([p.resultado.goles_visitante for p in partidos], dtype=float)
    total, dif = gl + gv, np.abs(gl - gv)
    X = np.column_stack([total, dif, gl, gv])
    bosque = IsolationForest(n_estimators=200, contamination="auto", random_state=7).fit(X)
    anomalia = -bosque.score_samples(X)
    aislado = bosque.predict(X) == -1

    med_total, med_dif = float(np.median(total)), float(np.median(dif))
    s_total, s_dif = _sigma(total), _sigma(dif)
    encontrados = []
    for i, p in enumerate(partidos):
        if not aislado[i]:
            continue
        razones = []
        if (total[i] - med_total) / s_total >= UMBRAL_Z:
            razones.append(f"{int(total[i])} goles en total (lo habitual en este deporte es {med_total:.0f})")
        if (dif[i] - med_dif) / s_dif >= UMBRAL_Z:
            razones.append(f"diferencia de {int(dif[i])} goles (lo habitual es {med_dif:.0f})")
        if not razones:
            continue
        encontrados.append({
            "partido": p, "puntaje": round(float(anomalia[i]), 3),
            "motivo": f"Marcador inusual {int(gl[i])}-{int(gv[i])}: " + " y ".join(razones) + ".",
        })
    return encontrados


def escanear(deporte_ids=None) -> list[ResultadoAtipico]:
    """Detecta y guarda las alertas nuevas (idempotente: una alerta por partido). Devuelve solo las NUEVAS."""
    from apps.deportes.models import Deporte

    nuevas = []
    for deporte in Deporte.objects.filter(pk__in=deporte_ids) if deporte_ids else Deporte.objects.all():
        for h in detectar(deporte.pk):
            alerta, creada = ResultadoAtipico.objects.get_or_create(
                partido=h["partido"], defaults={"puntaje": h["puntaje"], "motivo": h["motivo"][:300]})
            if creada:
                nuevas.append(alerta)
    return nuevas
