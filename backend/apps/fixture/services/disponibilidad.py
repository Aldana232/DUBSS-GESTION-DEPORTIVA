"""
apps/fixture/services/disponibilidad.py
RF11 — Reglas duras de programación, compartidas por el generador base y el optimizador ML.

Precarga UNA vez todo lo necesario (horarios de cancha, bloqueos, partidos ya reservados,
restricciones de facultad y partidos de otros campeonatos) y responde en memoria si un horario
es válido. Así programar 20 equipos no hace miles de consultas a la base (RNF04).
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.deportes.models import Campeonato, RestriccionHorarioFacultad
from apps.fixture.models import Partido
from apps.instalaciones.models import BloqueoCancha, Cancha, HorarioCancha

SIN_PARTIDOS_PREVIOS = 30
HOLGURA_MAXIMA = 240
MARGEN_CONGESTION = timedelta(minutes=60)


@dataclass(frozen=True)
class Slot:
    """Un horario posible: inicio y fin con zona horaria, día de la semana y horas locales."""
    inicio: datetime
    fin: datetime
    dia_semana: int
    t_ini: time
    t_fin: time
    fecha: date


class Disponibilidad:
    def __init__(self, campeonato: Campeonato, equipos, hora_inicio: time, dias_entre_jornadas: int,
                 duracion_min: int, paso_min: int = 30, descanso_min_horas: float = 0, reparar_ids=None):
        self.campeonato = campeonato
        self.hora_inicio = hora_inicio
        self.dias_entre_jornadas = max(1, dias_entre_jornadas)
        self.duracion = timedelta(minutes=duracion_min)
        self.paso = timedelta(minutes=paso_min)
        self.descanso = timedelta(hours=descanso_min_horas)

        self.canchas = list(
            Cancha.objects.filter(
                deporte=campeonato.categoria.deporte, activa=True, instalacion__estado="ACTIVA"
            ).order_by("pk")
        )
        ids = [c.pk for c in self.canchas]
        self._instalacion = {c.pk: c.instalacion_id for c in self.canchas}
        self.horarios: dict[tuple[int, int], list[tuple[time, time]]] = defaultdict(list)
        for h in HorarioCancha.objects.filter(cancha_id__in=ids):
            self.horarios[(h.cancha_id, h.dia_semana)].append((h.hora_inicio, h.hora_fin))
        self.bloqueos: dict[int, list[tuple[datetime, datetime]]] = defaultdict(list)
        for b in BloqueoCancha.objects.filter(cancha_id__in=ids):
            self.bloqueos[b.cancha_id].append((b.fecha_inicio, b.fecha_fin))
        self.reservas: dict[int, list[tuple[datetime, datetime]]] = defaultdict(list)
        self._por_instalacion: dict[int, list[tuple[datetime, datetime, int]]] = defaultdict(list)
        # Generación: se ignoran los partidos del propio campeonato (aún no existen).
        # Reparación (`reparar_ids`): cuenta TODO el calendario salvo los partidos que se van a mover.
        ocupados = Partido.objects.filter(cancha_id__in=ids)
        ocupados = ocupados.exclude(pk__in=reparar_ids) if reparar_ids else ocupados.exclude(campeonato=campeonato)
        for p in ocupados:
            self._anotar_reserva(p.cancha_id, p.fecha_hora, p.fecha_hora_fin)

        facultades = {e.facultad_id for e in equipos}
        self.restricciones: dict[tuple[int, int], list[tuple[time, time]]] = defaultdict(list)
        for r in RestriccionHorarioFacultad.objects.filter(facultad_id__in=facultades):
            self.restricciones[(r.facultad_id, r.dia_semana)].append((r.hora_inicio, r.hora_fin))

        # Partidos de OTROS campeonatos de estos equipos (mismo equipo no puede jugar a la vez).
        self.historial: dict[int, list[tuple[datetime, datetime]]] = defaultdict(list)
        pks = [e.pk for e in equipos]
        de_los_equipos = Partido.objects.filter(Q(equipo_local__in=pks) | Q(equipo_visitante__in=pks))
        de_los_equipos = de_los_equipos.exclude(pk__in=reparar_ids) if reparar_ids else de_los_equipos.exclude(campeonato=campeonato)
        for p in de_los_equipos:
            for equipo_id in (p.equipo_local_id, p.equipo_visitante_id):
                if equipo_id in pks:
                    self.historial[equipo_id].append((p.fecha_hora, p.fecha_hora_fin))
        for lista in self.historial.values():
            lista.sort()
        self._fines: dict[int, list[datetime]] = defaultdict(list)
        for equipo_id, lista in self.historial.items():
            self._fines[equipo_id] = sorted(f for _, f in lista)
        self._fecha_local: dict[datetime, date] = {}
        self._cache_ventanas: dict[int, list[Slot]] = {}

    # ── Ventanas de tiempo ────────────────────────────────────────────────────

    def ventana(self, jornada: int) -> list[Slot]:
        """Horarios posibles de una jornada: sus días, desde la hora inicial, sin cruzar la medianoche."""
        if jornada in self._cache_ventanas:
            return self._cache_ventanas[jornada]
        dia_base = self.campeonato.fecha_inicio + timedelta(days=(jornada - 1) * self.dias_entre_jornadas)
        slots = []
        for desplazamiento in range(self.dias_entre_jornadas):
            dia = dia_base + timedelta(days=desplazamiento)
            ini = datetime.combine(dia, self.hora_inicio)
            while True:
                fin = ini + self.duracion
                if fin.date() != dia:
                    break
                slots.append(Slot(timezone.make_aware(ini), timezone.make_aware(fin), dia.weekday(), ini.time(), fin.time(), dia))
                ini += self.paso
        self._cache_ventanas[jornada] = slots
        return slots

    # ── Reglas duras ──────────────────────────────────────────────────────────

    @staticmethod
    def _choca(intervalos, inicio, fin) -> bool:
        return any(i < fin and f > inicio for i, f in intervalos)

    def cancha_libre(self, cancha: Cancha, slot: Slot) -> bool:
        if not any(hi <= slot.t_ini and hf >= slot.t_fin for hi, hf in self.horarios.get((cancha.pk, slot.dia_semana), [])):
            return False
        return not (self._choca(self.bloqueos[cancha.pk], slot.inicio, slot.fin)
                    or self._choca(self.reservas[cancha.pk], slot.inicio, slot.fin))

    def equipo_libre(self, equipo_id, slot: Slot) -> bool:
        """Sin partidos que se solapen ni queden a menos del descanso mínimo."""
        if equipo_id is None:
            return True
        ini, fin = slot.inicio - self.descanso, slot.fin + self.descanso
        return not self._choca(self.historial[equipo_id], ini, fin)

    def facultad_restringida(self, facultad_id, slot: Slot) -> bool:
        if facultad_id is None:
            return False
        return any(r_ini < slot.t_fin and r_fin > slot.t_ini
                   for r_ini, r_fin in self.restricciones.get((facultad_id, slot.dia_semana), []))

    # ── Variables para el puntuador ───────────────────────────────────────────

    def holgura_minutos(self, facultades_ids, slot: Slot) -> int:
        """Minutos hasta la restricción de facultad más cercana ese día (HOLGURA_MAXIMA si no hay)."""
        mejor = HOLGURA_MAXIMA
        for facultad_id in facultades_ids:
            for r_ini, r_fin in self.restricciones.get((facultad_id, slot.dia_semana), []):
                antes = self._minutos(r_ini) - self._minutos(slot.t_fin)
                despues = self._minutos(slot.t_ini) - self._minutos(r_fin)
                mejor = min(mejor, max(0, antes, despues))
        return mejor

    @staticmethod
    def _minutos(t: time) -> int:
        return t.hour * 60 + t.minute

    def _fecha_de(self, momento: datetime) -> date:
        fecha = self._fecha_local.get(momento)
        if fecha is None:
            fecha = self._fecha_local[momento] = timezone.localtime(momento).date()
        return fecha

    def dias_desde_ultimo(self, equipo_id, slot: Slot) -> int:
        if equipo_id is None:
            return SIN_PARTIDOS_PREVIOS
        fines = self._fines[equipo_id]
        k = bisect_right(fines, slot.inicio)
        if k == 0:
            return SIN_PARTIDOS_PREVIOS
        return min(SIN_PARTIDOS_PREVIOS, (slot.fecha - self._fecha_de(fines[k - 1])).days)

    def congestion_ventana(self, slots: list[Slot]) -> dict[tuple[int, int], int]:
        """
        Para cada (cancha, horario) de la ventana: partidos en OTRAS canchas de la misma instalación
        a ±1 hora (aglomeración del recinto). Se calcula una vez por jornada, no por candidato.
        """
        desde, hasta = slots[0].inicio - MARGEN_CONGESTION, slots[-1].fin + MARGEN_CONGESTION
        cercanas = {
            instalacion_id: [r for r in lista if r[0] < hasta and r[1] > desde]
            for instalacion_id, lista in self._por_instalacion.items()
        }
        resultado = {}
        for c in self.canchas:
            cid = c.pk
            reservas = cercanas.get(self._instalacion[cid], [])
            for i, slot in enumerate(slots):
                ini, fin = slot.inicio - MARGEN_CONGESTION, slot.fin + MARGEN_CONGESTION
                resultado[(cid, i)] = sum(1 for r_ini, r_fin, otra in reservas if otra != cid and r_ini < fin and r_fin > ini)
        return resultado

    # ── Reservas ──────────────────────────────────────────────────────────────

    def _anotar_reserva(self, cancha_id: int, inicio: datetime, fin: datetime) -> None:
        self.reservas[cancha_id].append((inicio, fin))
        self._por_instalacion[self._instalacion.get(cancha_id, 0)].append((inicio, fin, cancha_id))

    def reservar(self, cancha: Cancha, slot: Slot, equipos_ids) -> None:
        self._anotar_reserva(cancha.pk, slot.inicio, slot.fin)
        for equipo_id in equipos_ids:
            if equipo_id is not None:
                lista = self.historial[equipo_id]
                lista.insert(bisect_right(lista, (slot.inicio, slot.fin)), (slot.inicio, slot.fin))
                fines = self._fines[equipo_id]
                fines.insert(bisect_right(fines, slot.fin), slot.fin)
