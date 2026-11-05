"""
apps/fixture/services/fixture_optimizer.py
RF11 — Optimizador del fixture: OR-Tools CP-SAT + puntuador Random Forest.

Enfoque híbrido (decisión D9 del plan):
* CP-SAT garantiza las restricciones DURAS: cada partido en exactamente un horario y una cancha,
  sin solapes de cancha ni de equipo, descanso mínimo entre partidos de un equipo, horarios de la
  cancha, bloqueos, restricciones de facultad y partidos de otros campeonatos.
* El Random Forest (`asignacion_scorer`) puntúa cada asignación posible y CP-SAT maximiza la suma
  de puntajes. Así el modelo decide *qué tan bueno* es cada horario y el solver garantiza que sea *válido*.

La liga se resuelve jornada por jornada (cada jornada es un subproblema pequeño y exacto) y
cada jornada ya resuelta alimenta las variables de "días desde el último partido" de la siguiente.
Si no hay solución, `OptimizadorSinSolucion` permite al generador caer al método base y avisar.
"""
from __future__ import annotations

import logging
import time as reloj
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from django.conf import settings
from ortools.sat.python import cp_model

from apps.fixture.services.disponibilidad import Disponibilidad, Slot
from apps.ml.services.asignacion_scorer import ModeloNoDisponible, obtener_scorer

logger = logging.getLogger(__name__)

PENALIZACION_TARDANZA = 60  # minutos de la ventana por cada punto de desempate (favorece horarios tempranos)
ESCALA_PUNTAJE = 10_000
BRECHA_OPTIMALIDAD = 0.01    # se detiene al estar a 1 % del óptimo demostrado (diferencia imperceptible)
ESTADOS_SOLVER: list[str] = []   # diagnóstico: estado del solver en cada resolución


class OptimizadorSinSolucion(RuntimeError):
    """El solver no encontró una asignación que cumpla todas las restricciones duras."""


@dataclass
class ResultadoOptimizacion:
    asignaciones: list            # [(cancha, slot)] alineado con el plan de partidos
    puntaje_medio: float          # probabilidad media de "buena asignación" (0-1)
    modelo_version: str
    segundos: float
    jornadas: int
    tiempos: dict                 # segundos por fase: candidatos, puntuacion, solver


def _construir_filas(disp: Disponibilidad, plan, idxs, slots):
    """Todas las asignaciones válidas de la jornada y sus variables para el puntuador."""
    canchas = [(c, c.pk) for c in disp.canchas]
    libre = {(cid, i): disp.cancha_libre(c, s) for c, cid in canchas for i, s in enumerate(slots)}
    congestion = disp.congestion_ventana(slots)
    filas, meta = [], []
    for idx in idxs:
        spec = plan[idx]
        local_id = spec.local.pk if spec.local else None
        visit_id = spec.visitante.pk if spec.visitante else None
        participantes = [i for i in (local_id, visit_id) if i is not None]
        facultades = [e.facultad_id for e in (spec.local, spec.visitante) if e is not None]
        for i, slot in enumerate(slots):
            if not all(disp.equipo_libre(e, slot) for e in participantes):
                continue
            if any(disp.facultad_restringida(f, slot) for f in facultades):
                continue
            holgura = disp.holgura_minutos(facultades, slot)
            d_local = disp.dias_desde_ultimo(local_id, slot)
            d_visit = disp.dias_desde_ultimo(visit_id, slot)
            fijas = [slot.t_ini.hour, slot.dia_semana, 1.0 if slot.dia_semana >= 5 else 0.0,
                     d_local, d_visit, min(d_local, d_visit), 1.0]
            for c, cid in canchas:
                if libre[(cid, i)]:
                    filas.append(fijas + [congestion[(cid, i)], holgura])
                    meta.append((idx, c, i))
    return np.array(filas, dtype=float).reshape(-1, 9), meta


def _resolver_jornada(plan, idxs, slots, meta, puntajes, maximo_por_partido, tiempo):
    """
    CP-SAT de una jornada. Devuelve {idx: (cancha, indice_slot, puntaje)} o None si es infactible.

    Los horarios de la ventana avanzan de a una duración de partido, así dos horarios distintos
    nunca se solapan: "sin solape de cancha" y "sin solape de equipo" equivalen a "a lo sumo un
    partido por (cancha, horario)" y "a lo sumo un partido por (equipo, horario)". Es una asignación
    pura que CP-SAT resuelve en milisegundos.
    """
    origen = slots[0].inicio
    coeficientes = {}
    por_partido = defaultdict(list)
    for k, (idx, cancha, i) in enumerate(meta):
        minutos = int((slots[i].inicio - origen).total_seconds() // 60)
        coeficientes[k] = int(round(puntajes[k] * ESCALA_PUNTAJE)) - minutos // PENALIZACION_TARDANZA
        por_partido[idx].append(k)
    if any(idx not in por_partido for idx in idxs):
        return None

    candidatos = []
    for idx in idxs:
        ordenados = sorted(por_partido[idx], key=lambda k: -coeficientes[k])
        candidatos.extend(ordenados[:maximo_por_partido] if maximo_por_partido else ordenados)

    modelo = cp_model.CpModel()
    variables = {k: modelo.NewBoolVar(f"x{k}") for k in candidatos}
    por_idx, por_cancha_slot, por_equipo_slot = defaultdict(list), defaultdict(list), defaultdict(list)
    for k, x in variables.items():
        idx, cancha, i = meta[k]
        por_idx[idx].append(x)
        por_cancha_slot[(cancha.pk, i)].append(x)
        for equipo in (plan[idx].local, plan[idx].visitante):
            if equipo is not None:
                por_equipo_slot[(equipo.pk, i)].append(x)
    for idx in idxs:
        modelo.AddExactlyOne(por_idx[idx])
    for grupo in list(por_cancha_slot.values()) + list(por_equipo_slot.values()):
        if len(grupo) > 1:
            modelo.AddAtMostOne(grupo)
    modelo.Maximize(cp_model.LinearExpr.WeightedSum(list(variables.values()), [coeficientes[k] for k in variables]))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max(0.5, tiempo)
    solver.parameters.num_workers = 1
    solver.parameters.linearization_level = 2      # relajación lineal fuerte: acota el óptimo rápido
    solver.parameters.relative_gap_limit = BRECHA_OPTIMALIDAD
    solver.parameters.random_seed = 7
    estado = solver.Solve(modelo)
    ESTADOS_SOLVER.append(solver.StatusName(estado))
    logger.debug("CP-SAT: %s en %.3fs (%d variables)", solver.StatusName(estado), solver.WallTime(), len(variables))
    if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None
    elegidas = {}
    for k, x in variables.items():
        if solver.Value(x):
            idx, cancha, i = meta[k]
            elegidas[idx] = (cancha, i, float(puntajes[k]))
    return elegidas if len(elegidas) == len(idxs) else None


def optimizar_fixture(campeonato, plan, equipos, hora_inicio, dias_entre_jornadas, duracion_min) -> ResultadoOptimizacion:
    """Asigna cancha y horario a cada partido del plan. Lanza OptimizadorSinSolucion o ModeloNoDisponible."""
    inicio_total = reloj.perf_counter()
    scorer = obtener_scorer()  # precondición RF11: modelo entrenado (arranque en frío si hace falta)
    disp = Disponibilidad(
        campeonato, equipos, hora_inicio, dias_entre_jornadas, duracion_min,
        paso_min=duracion_min, descanso_min_horas=settings.FIXTURE_DESCANSO_MIN_HORAS,
    )
    if not disp.canchas:
        raise OptimizadorSinSolucion("No hay canchas activas para el deporte del campeonato.")

    por_jornada = defaultdict(list)
    for idx, spec in enumerate(plan):
        por_jornada[spec.jornada].append(idx)
    presupuesto = settings.ML_FIXTURE_MAX_SEGUNDOS / max(1, len(por_jornada))

    asignaciones: list = [None] * len(plan)
    puntajes_elegidos = []
    tiempos = {"candidatos": 0.0, "puntuacion": 0.0, "solver": 0.0}
    for jornada in sorted(por_jornada):
        idxs = por_jornada[jornada]
        slots = disp.ventana(jornada)
        if not slots:
            raise OptimizadorSinSolucion(f"La jornada {jornada} no tiene horarios posibles.")
        t0 = reloj.perf_counter()
        matriz, meta = _construir_filas(disp, plan, idxs, slots)
        t1 = reloj.perf_counter()
        puntajes = scorer.puntuar_lote(matriz)
        t2 = reloj.perf_counter()
        elegidas = _resolver_jornada(plan, idxs, slots, meta, puntajes, settings.ML_CANDIDATOS_POR_PARTIDO, presupuesto)
        if elegidas is None and settings.ML_CANDIDATOS_POR_PARTIDO:
            # Reintento sin recortar candidatos: el recorte puede haber dejado sin salida a un partido.
            elegidas = _resolver_jornada(plan, idxs, slots, meta, puntajes, 0, presupuesto * 2)
        tiempos["candidatos"] += t1 - t0
        tiempos["puntuacion"] += t2 - t1
        tiempos["solver"] += reloj.perf_counter() - t2
        if elegidas is None:
            raise OptimizadorSinSolucion(
                f"No hay cancha y horario disponibles para todos los partidos de la jornada {jornada} "
                f"respetando horarios, bloqueos, restricciones de facultad y el descanso mínimo "
                f"(solver: {ESTADOS_SOLVER[-1] if ESTADOS_SOLVER else 'sin datos'})."
            )
        for idx, (cancha, i, puntaje) in elegidas.items():
            asignaciones[idx] = (cancha, slots[i])
            puntajes_elegidos.append(puntaje)
            disp.reservar(cancha, slots[i], [e.pk if e else None for e in (plan[idx].local, plan[idx].visitante)])

    return ResultadoOptimizacion(
        asignaciones=asignaciones,
        puntaje_medio=float(np.mean(puntajes_elegidos)) if puntajes_elegidos else 0.0,
        modelo_version=scorer.version,
        segundos=reloj.perf_counter() - inicio_total,
        jornadas=len(por_jornada),
        tiempos={k: round(v, 2) for k, v in tiempos.items()},
    )


__all__ = ["ModeloNoDisponible", "OptimizadorSinSolucion", "ResultadoOptimizacion", "Slot", "optimizar_fixture"]
