"""
apps/ml/services/asistencia.py
CU20 — Estimación de asistencia de espectadores.

IMPORTANTE (honestidad): el sistema todavía NO registra la asistencia real de los partidos, así que
no hay datos para entrenar un modelo. Esta es una estimación por reglas explícitas, y se declara así
en la respuesta (`metodo`). Cuando se empiece a registrar la asistencia, podrá reemplazarse por un modelo.
"""
from __future__ import annotations

from django.utils import timezone

from apps.fixture.models import Partido
from apps.ml.models import RiesgoClimatico
from apps.ml.services.clima import ultimo_riesgo

CAPACIDAD_POR_DEFECTO = 300
OCUPACION_BASE = 0.35
POR_FASE = {"final": 1.9, "semifinal": 1.6, "cuartos": 1.35, "octavos": 1.2}
MARGEN = 0.25


def estimar_asistencia(partido: Partido) -> dict:
    capacidad = (partido.cancha.capacidad if partido.cancha and partido.cancha.capacidad else 0) or CAPACIDAD_POR_DEFECTO
    inicio = timezone.localtime(partido.fecha_hora)
    factores = {"capacidad_cancha": capacidad, "fase": partido.fase, "jornada": partido.jornada}

    multiplicador = next((m for clave, m in POR_FASE.items() if clave in partido.fase.lower()), 1.0)
    if inicio.weekday() >= 5:
        multiplicador *= 1.15
        factores["fin_de_semana"] = True
    if not 10 <= inicio.hour < 18:
        multiplicador *= 0.85
        factores["fuera_de_franja_ideal"] = True
    riesgo = ultimo_riesgo(partido)
    if riesgo and riesgo.nivel_riesgo in (RiesgoClimatico.NivelRiesgo.ALTO, RiesgoClimatico.NivelRiesgo.CRITICO) \
            and not (partido.cancha and partido.cancha.techada):
        multiplicador *= 0.6
        factores["riesgo_climatico"] = riesgo.nivel_riesgo

    estimada = int(min(capacidad, capacidad * OCUPACION_BASE * multiplicador))
    factores["metodo"] = "estimación por reglas (todavía no se registra la asistencia real)"
    return {
        "asistencia_predicha": estimada,
        "rango_min": max(0, int(estimada * (1 - MARGEN))),
        "rango_max": min(capacidad, int(estimada * (1 + MARGEN))),
        "factores": factores,
    }
