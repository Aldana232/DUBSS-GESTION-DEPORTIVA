"""
apps/fixture/services/reparacion.py
F7-01 — Optimizador en «modo reparación»: reubica SOLO los partidos afectados (por lluvia, un bloqueo, etc.)
sin tocar el resto del calendario.

Mismo enfoque híbrido del fixture (decisión D9):
* CP-SAT garantiza las restricciones DURAS: cancha y equipos sin solapes (también entre los partidos que se
  mueven a la vez), descanso mínimo del equipo, horarios y bloqueos de la cancha, restricciones de facultad,
  partidos de otros campeonatos y de los que NO se mueven, y antelación mínima.
* Con pronóstico disponible se descartan los horarios al aire libre con riesgo ALTO/CRÍTICO (los techados no
  sufren la lluvia).
* Entre las opciones válidas se prefiere, por este orden: colocar todos los partidos que se pueda, moverlos lo
  mínimo posible, conservar la cancha y, al final, el puntaje del Random Forest (`asignacion_scorer`).

No escribe en la base: devuelve una propuesta que luego debe confirmar una persona.
"""
from __future__ import annotations

import logging
import time as reloj
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

import numpy as np
from django.conf import settings
from django.utils import timezone
from ortools.sat.python import cp_model

from apps.deportes.models import Campeonato
from apps.fixture.models import Partido
from apps.fixture.services.disponibilidad import Disponibilidad, Slot
from apps.ml.services.asignacion_scorer import ModeloNoDisponible, obtener_scorer

logger = logging.getLogger(__name__)

PASO_MIN = 30
HORA_PRIMER_PARTIDO = time(7, 0)
GRANDE = 10_000_000          # colocar un partido vale más que cualquier otra preferencia
PESO_DESPLAZAMIENTO = 10      # por cada minuto de diferencia con el horario original
PENALIZA_CAMBIO_CANCHA = 60
PENALIZA_SIN_PRONOSTICO = 300
MAX_CANDIDATOS_POR_PARTIDO = 80
NIVELES_PELIGROSOS = {"ALTO", "CRITICO"}


@dataclass
class Cambio:
    partido: Partido
    cancha: object
    inicio: datetime
    fin: datetime
    clima: str | None            # nivel verificado del nuevo horario (None = sin pronóstico)
    desplazamiento_min: int
    puntaje: float


@dataclass
class PropuestaReparacion:
    cambios: list[Cambio] = field(default_factory=list)
    sin_solucion: list[tuple[Partido, str]] = field(default_factory=list)
    descartados: list[tuple[Partido, str]] = field(default_factory=list)
    modelo_version: str = "sin-modelo"
    puntaje_medio: float | None = None
    segundos: float = 0.0
    clima_verificado: bool = False
    ventana: tuple[date, date] | None = None


def _slots_del_dia(disp: Disponibilidad, cancha, dia: date, duracion: timedelta) -> list[Slot]:
    """Inicios cada 30 min dentro de las franjas habilitadas de la cancha ese día."""
    slots = []
    for hora_ini, hora_fin in disp.horarios.get((cancha.pk, dia.weekday()), []):
        inicio = datetime.combine(dia, max(hora_ini, HORA_PRIMER_PARTIDO))
        limite = datetime.combine(dia, hora_fin)
        while inicio + duracion <= limite:
            fin = inicio + duracion
            if fin.date() != dia:
                break
            slots.append(Slot(timezone.make_aware(inicio), timezone.make_aware(fin), dia.weekday(),
                              inicio.time(), fin.time(), dia))
            inicio += timedelta(minutes=PASO_MIN)
    return slots


def _desplazamiento(partido: Partido, slot: Slot) -> int:
    """
    Cuánto se aleja el nuevo horario del original: días de diferencia (1 440 min cada uno) + diferencia de hora del día.
    Así «mismo horario otro día» gana a «la mañana siguiente»: a los equipos les cambia menos la rutina.
    """
    original = timezone.localtime(partido.fecha_hora)
    dias = abs((slot.fecha - original.date()).days)
    hora_original = original.hour * 60 + original.minute
    return dias * 1440 + abs(slot.t_ini.hour * 60 + slot.t_ini.minute - hora_original)


def _motivo_sin_solucion(hubo_candidatos: bool, hay_serie: bool) -> str:
    if not hubo_candidatos:
        base = "No hay ningún horario libre en la ventana (revisa horarios de cancha, bloqueos, descanso de los equipos y restricciones de facultad)"
        return base + (" ni sin riesgo climático." if hay_serie else ".")
    return "Los horarios libres se agotan al reubicar todos los partidos a la vez."


def _resolver_grupo(partidos, ventana, ahora, evitar_clima, serie, servicio_clima, presupuesto) -> tuple[list[Cambio], list, dict]:
    """Reubica los partidos de un mismo deporte. Devuelve (cambios, sin_solucion, info)."""
    desde, hasta = ventana
    campeonato_ref = partidos[0].campeonato
    equipos = {e for p in partidos for e in (p.equipo_local, p.equipo_visitante)}
    duracion_max = max(p.duracion_min for p in partidos)
    disp = Disponibilidad(
        campeonato_ref, equipos, HORA_PRIMER_PARTIDO, 1, duracion_max, paso_min=PASO_MIN,
        descanso_min_horas=settings.FIXTURE_DESCANSO_MIN_HORAS, reparar_ids={p.pk for p in partidos},
    )
    if not disp.canchas:
        return [], [(p, "No hay canchas activas para el deporte del campeonato.") for p in partidos], {}
    minimo = ahora + timedelta(hours=settings.AGENTE_ANTELACION_HORAS)
    dias = [desde + timedelta(days=i) for i in range((hasta - desde).days + 1)]

    try:
        scorer = obtener_scorer()
    except ModeloNoDisponible:
        scorer = None

    # ── Candidatos válidos por partido ───────────────────────────────────────────
    candidatos: dict[int, list[tuple]] = defaultdict(list)    # pk -> [(cancha, slot, clima)]
    cache_slots: dict[tuple[int, date, int], list[Slot]] = {}
    for p in partidos:
        duracion = timedelta(minutes=p.duracion_min)
        facultades = [e.facultad_id for e in (p.equipo_local, p.equipo_visitante)]
        for dia in dias:
            for cancha in disp.canchas:
                clave = (cancha.pk, dia, p.duracion_min)
                if clave not in cache_slots:
                    cache_slots[clave] = _slots_del_dia(disp, cancha, dia, duracion)
                for slot in cache_slots[clave]:
                    if slot.inicio < minimo:
                        continue
                    if p.cancha_id == cancha.pk and slot.inicio == p.fecha_hora:
                        continue                                    # no es un cambio
                    if not disp.cancha_libre(cancha, slot):
                        continue
                    if not (disp.equipo_libre(p.equipo_local_id, slot) and disp.equipo_libre(p.equipo_visitante_id, slot)):
                        continue
                    if any(disp.facultad_restringida(f, slot) for f in facultades):
                        continue
                    nivel = None
                    if serie is not None:
                        r = servicio_clima.riesgo_de_ventana(serie, slot.inicio, slot.fin, cancha.techada)
                        nivel = r[0] if r else None
                        if evitar_clima and nivel in NIVELES_PELIGROSOS:
                            continue
                    candidatos[p.pk].append((cancha, slot, nivel))

    # ── Puntaje del Random Forest (desempate) ────────────────────────────────────
    por_pk = {p.pk: p for p in partidos}
    filas, meta = [], []
    for pk, lista in candidatos.items():
        p = por_pk[pk]
        facultades = [e.facultad_id for e in (p.equipo_local, p.equipo_visitante)]
        for cancha, slot, nivel in lista:
            d_local = disp.dias_desde_ultimo(p.equipo_local_id, slot)
            d_visit = disp.dias_desde_ultimo(p.equipo_visitante_id, slot)
            filas.append([slot.t_ini.hour, slot.dia_semana, 1.0 if slot.dia_semana >= 5 else 0.0, d_local, d_visit,
                          min(d_local, d_visit), 1.0, 0.0, disp.holgura_minutos(facultades, slot)])  # congestión 0: pocos partidos a la vez
            meta.append((pk, cancha, slot, nivel))
    if scorer is not None and filas:
        puntajes = scorer.puntuar_lote(np.array(filas, dtype=float).reshape(-1, 9))
        version = scorer.version
    else:
        puntajes, version = np.full(len(filas), 0.5), "sin-modelo"

    # ── Coeficientes y recorte ───────────────────────────────────────────────────
    origen = min((m[2].inicio for m in meta), default=None)
    if origen is None:
        return [], [(p, _motivo_sin_solucion(False, serie is not None)) for p in partidos], {"modelo": version}
    por_partido = defaultdict(list)
    for k, (pk, cancha, slot, nivel) in enumerate(meta):
        p = por_pk[pk]
        desplaza = _desplazamiento(p, slot)
        coef = (GRANDE + int(round(puntajes[k] * 100)) - PESO_DESPLAZAMIENTO * desplaza
                - (PENALIZA_CAMBIO_CANCHA if cancha.pk != p.cancha_id else 0)
                - (PENALIZA_SIN_PRONOSTICO if (serie is not None and nivel is None) else 0))
        por_partido[pk].append((coef, k, desplaza))

    def resolver(recortar):
        modelo = cp_model.CpModel()
        vars_, por_cancha, por_equipo = {}, defaultdict(list), defaultdict(list)
        terminos = []
        for pk, lista in por_partido.items():
            ordenada = sorted(lista, reverse=True)
            if recortar:
                ordenada = ordenada[:MAX_CANDIDATOS_POR_PARTIDO]
            p = por_pk[pk]
            literales = []
            for coef, k, _ in ordenada:
                _, cancha, slot, _n = meta[k]
                x = modelo.NewBoolVar(f"x{k}")
                vars_[k] = x
                literales.append(x)
                terminos.append((x, coef))
                ini = int((slot.inicio - origen).total_seconds() // 60)
                dur = p.duracion_min
                por_cancha[cancha.pk].append(modelo.NewOptionalFixedSizeIntervalVar(ini, dur, x, f"c{k}"))
                # El equipo ocupa su partido más el descanso mínimo: así dos partidos del mismo equipo
                # reubicados a la vez también respetan el descanso entre sí.
                ocupado = dur + int(settings.FIXTURE_DESCANSO_MIN_HORAS * 60)
                for equipo_id in (p.equipo_local_id, p.equipo_visitante_id):
                    por_equipo[equipo_id].append(modelo.NewOptionalFixedSizeIntervalVar(ini, ocupado, x, f"e{k}_{equipo_id}"))
            if literales:
                modelo.AddAtMostOne(literales)
        for grupo in list(por_cancha.values()) + list(por_equipo.values()):
            modelo.AddNoOverlap(grupo)
        modelo.Maximize(sum(coef * x for x, coef in terminos))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(1.0, presupuesto)
        solver.parameters.num_workers = 1
        solver.parameters.random_seed = 7
        estado = solver.Solve(modelo)
        if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return {}
        return {k for k, x in vars_.items() if solver.Value(x)}

    elegidos = resolver(recortar=True)
    if len(elegidos) < len(por_partido):
        elegidos = resolver(recortar=False) or elegidos

    cambios, sin_solucion, puntajes_ok = [], [], []
    colocados = set()
    for k in elegidos:
        pk, cancha, slot, nivel = meta[k]
        p = por_pk[pk]
        colocados.add(pk)
        puntajes_ok.append(float(puntajes[k]))
        cambios.append(Cambio(p, cancha, slot.inicio, slot.fin, nivel, _desplazamiento(p, slot), float(puntajes[k])))
    for p in partidos:
        if p.pk not in colocados:
            sin_solucion.append((p, _motivo_sin_solucion(p.pk in por_partido, serie is not None)))
    return cambios, sin_solucion, {"modelo": version, "puntajes": puntajes_ok}


def proponer_reparacion(partidos, *, desde: date, hasta: date, evitar_riesgo_climatico: bool = True, ahora=None) -> PropuestaReparacion:
    """
    Calcula nuevos horarios para `partidos` dentro de [desde, hasta]. No escribe nada.
    Solo se reubican partidos PROGRAMADOS, con ambos equipos definidos y de campeonatos en curso.
    """
    inicio_total = reloj.perf_counter()
    ahora = ahora or timezone.now()
    propuesta = PropuestaReparacion(ventana=(desde, hasta))
    elegibles = []
    for p in partidos:
        if p.estado != Partido.Estado.PROGRAMADO:
            propuesta.descartados.append((p, f"Su estado es «{p.get_estado_display()}»: solo se reubican partidos programados."))
        elif p.equipo_local_id is None or p.equipo_visitante_id is None:
            propuesta.descartados.append((p, "Aún no tiene los dos equipos definidos."))
        elif p.campeonato.estado != Campeonato.Estado.EN_CURSO:
            propuesta.descartados.append((p, "Su campeonato no está en curso."))
        elif p.fecha_hora <= ahora:
            propuesta.descartados.append((p, "Ya empezó o ya pasó."))
        else:
            elegibles.append(p)
    if not elegibles:
        propuesta.segundos = reloj.perf_counter() - inicio_total
        return propuesta

    serie, servicio = None, None
    if evitar_riesgo_climatico:
        from apps.ml.services.clima import ServicioClima   # evita importar el módulo de ML al cargar el de fixture
        servicio = ServicioClima()
        try:
            serie = servicio.serie()
        except Exception:  # noqa: BLE001 — sin red/API: se sigue, avisando que el clima no se verificó
            logger.warning("Reparación sin pronóstico: no se pudo consultar Open-Meteo.", exc_info=True)
    propuesta.clima_verificado = serie is not None

    grupos = defaultdict(list)
    for p in elegibles:
        grupos[p.campeonato.categoria.deporte_id].append(p)
    presupuesto = settings.ML_FIXTURE_MAX_SEGUNDOS / max(1, len(grupos))
    puntajes = []
    for grupo in grupos.values():
        cambios, sin_solucion, info = _resolver_grupo(grupo, (desde, hasta), ahora, evitar_riesgo_climatico, serie, servicio, presupuesto)
        propuesta.cambios.extend(cambios)
        propuesta.sin_solucion.extend(sin_solucion)
        puntajes.extend(info.get("puntajes", []))
        if info.get("modelo"):
            propuesta.modelo_version = info["modelo"]
    propuesta.cambios.sort(key=lambda c: c.partido.fecha_hora)
    propuesta.puntaje_medio = float(np.mean(puntajes)) if puntajes else None
    propuesta.segundos = reloj.perf_counter() - inicio_total
    return propuesta
