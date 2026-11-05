"""
apps/fixture/services/metricas.py
RF11 — Métricas de calidad de un fixture (para mostrar al organizador).

* conflictos: solapes de cancha o de equipo (debe ser 0).
* descanso: días entre el fin de un partido y el inicio del siguiente del mismo equipo.
* franja ideal: partidos jugados entre las 10:00 y las 17:59.
* equidad: qué parejo reparte el fixture esos horarios ideales entre los equipos
  (100 % = todos los equipos tienen la misma proporción de partidos en franja ideal).
"""
from __future__ import annotations

from collections import defaultdict

from django.utils import timezone

from apps.fixture.models import Partido

FRANJA_IDEAL = range(10, 18)


def _solapa(a, b) -> bool:
    return a.fecha_hora < b.fecha_hora_fin and b.fecha_hora < a.fecha_hora_fin


def calcular_calidad(campeonato) -> dict:
    partidos = list(
        Partido.objects.filter(campeonato=campeonato, equipo_local__isnull=False, equipo_visitante__isnull=False)
        .order_by("fecha_hora")
    )
    total = len(partidos)
    if total == 0:
        return {"partidos": 0, "conflictos": 0, "descanso_promedio_dias": None, "descanso_minimo_dias": None,
                "en_franja_ideal_pct": None, "equidad_pct": None}

    conflictos = 0
    for i, a in enumerate(partidos):
        for b in partidos[i + 1:]:
            if b.fecha_hora >= a.fecha_hora_fin:
                break  # ordenados por inicio: ninguno de los siguientes puede solaparse con `a`
            comparten_cancha = a.cancha_id is not None and a.cancha_id == b.cancha_id
            comparten_equipo = {a.equipo_local_id, a.equipo_visitante_id} & {b.equipo_local_id, b.equipo_visitante_id}
            if _solapa(a, b) and (comparten_cancha or comparten_equipo):
                conflictos += 1

    por_equipo = defaultdict(list)
    for p in partidos:
        por_equipo[p.equipo_local_id].append(p)
        por_equipo[p.equipo_visitante_id].append(p)
    descansos = []
    for lista in por_equipo.values():
        for previo, siguiente in zip(lista, lista[1:]):
            descansos.append((siguiente.fecha_hora - previo.fecha_hora_fin).total_seconds() / 86400)

    def ideal(p) -> bool:
        return timezone.localtime(p.fecha_hora).hour in FRANJA_IDEAL

    proporciones = [sum(1 for p in lista if ideal(p)) / len(lista) for lista in por_equipo.values()]
    return {
        "partidos": total,
        "conflictos": conflictos,
        "descanso_promedio_dias": round(sum(descansos) / len(descansos), 1) if descansos else None,
        "descanso_minimo_dias": round(min(descansos), 1) if descansos else None,
        "en_franja_ideal_pct": round(100 * sum(1 for p in partidos if ideal(p)) / total),
        "equidad_pct": round(100 * (1 - (max(proporciones) - min(proporciones)))),
    }
