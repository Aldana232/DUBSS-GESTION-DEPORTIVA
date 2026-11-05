"""
apps/fixture/services/fixture_generator.py
RF11 — Generación del fixture de un campeonato.

1. PLAN: qué partidos hay y en qué jornada (independiente de horarios).
   * LIGA: todos contra todos (Round Robin circular, BYE si el número es impar, doble vuelta opcional).
   * ELIMINACION: llaves con cabezas de serie por orden de inscripción, BYE cuando el número de
     equipos no es potencia de 2 y partidos "placeholder" enlazados (el ganador avanza solo).
2. ASIGNACIÓN de cancha y horario a cada partido del plan:
   * `usar_ml=True`: optimizador OR-Tools CP-SAT que maximiza el puntaje del Random Forest
     (fixture_optimizer). Solo entonces el partido queda con `generado_por_ml=True`.
     Si el modelo no está disponible o el solver no halla solución, se cae al método base y se avisa.
   * Método base: primer horario libre, en paralelo por cancha (determinista y rápido).
3. CREACIÓN: todo en una sola transacción (incluido el borrado previo). Los partidos con resultado
   o en curso nunca se borran: si existen, se rechaza la regeneración.

Precondición (RF10/RF11): el campeonato debe estar en «Inscripciones cerradas».
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import time

from django.db import transaction

from apps.deportes.models import Campeonato, Inscripcion
from apps.fixture.models import Partido
from apps.fixture.services import metricas, tabla
from apps.fixture.services import fixture_optimizer
from apps.fixture.services.disponibilidad import Disponibilidad
from apps.ml.services.asignacion_scorer import ModeloNoDisponible

logger = logging.getLogger(__name__)

PASO_MINUTOS = 30


class FixtureError(ValueError):
    """El fixture no se puede generar con los datos actuales (400)."""


class FixtureConflicto(FixtureError):
    """Hay partidos jugados o en curso que impiden regenerar el fixture (409)."""


@dataclass
class PartidoPlan:
    """Un partido por programar: quiénes juegan y en qué jornada (aún sin cancha ni horario)."""
    jornada: int
    local: object | None
    visitante: object | None
    fase: str
    ronda: int | None = None
    origen_local: int | None = None       # índice del partido del plan cuyo ganador entra aquí
    origen_visitante: int | None = None


def nombre_ronda(ronda: int, total_rondas: int) -> str:
    restantes = total_rondas - ronda
    return {0: "Final", 1: "Semifinal", 2: "Cuartos de final", 3: "Octavos de final"}.get(
        restantes, f"Ronda {ronda}"
    )


def orden_de_siembra(tamano: int) -> list[int]:
    """Posiciones de las cabezas de serie en una llave de `tamano` (potencia de 2)."""
    if tamano == 1:
        return [1]
    anterior = orden_de_siembra(tamano // 2)
    orden = []
    for semilla in anterior:
        orden += [semilla, tamano + 1 - semilla]
    return orden


def _round_robin(equipos: list) -> list[list]:
    """
    Round Robin circular. Devuelve una lista de jornadas con tuplas (local, visitante).
    Con número impar de equipos se agrega un BYE (None) y ese equipo descansa.
    """
    n = len(equipos)
    if n % 2 != 0:
        equipos = equipos + [None]
        n += 1
    fijo = equipos[0]
    rotativos = equipos[1:]
    jornadas = []
    for ronda in range(n - 1):
        jornada = []
        circulo = [fijo] + rotativos
        for i in range(n // 2):
            local, visitante = circulo[i], circulo[n - 1 - i]
            if local is not None and visitante is not None:
                jornada.append((local, visitante) if ronda % 2 == 0 else (visitante, local))
        jornadas.append(jornada)
        rotativos = [rotativos[-1]] + rotativos[:-1]
    return jornadas


class FixtureGenerator:
    """
    Uso:
        gen = FixtureGenerator(campeonato_id=1, doble_vuelta=True)
        partidos = gen.generar(usar_ml=True)
        gen.resultado  # {"generado_por_ml", "aviso", "calidad", "ml": {...}}
    """

    DURACION_PARTIDO_MINUTOS = 90

    def __init__(self, campeonato_id: int, hora_inicio: str = "08:00",
                 dias_entre_jornadas: int = 7, doble_vuelta: bool = False):
        try:
            self.campeonato = Campeonato.objects.select_related("categoria__deporte").get(pk=campeonato_id)
        except Campeonato.DoesNotExist:
            raise FixtureError("El campeonato indicado no existe.")
        try:
            horas, minutos = map(int, str(hora_inicio).split(":"))
            self.hora_inicio = time(horas, minutos)
        except (ValueError, TypeError):
            raise FixtureError("La hora de inicio debe tener el formato HH:MM.")
        if int(dias_entre_jornadas) < 1:
            raise FixtureError("Los días entre jornadas deben ser al menos 1.")
        self.dias_entre_jornadas = int(dias_entre_jornadas)
        self.doble_vuelta = bool(doble_vuelta)
        self.resultado: dict = {"generado_por_ml": False, "aviso": "", "calidad": None, "ml": None, "siembra": None}

    # ── API pública ───────────────────────────────────────────────────────────

    def generar(self, usar_ml: bool = False, sembrar_con_ml: bool = False) -> list[Partido]:
        campeonato = self.campeonato
        if campeonato.estado != Campeonato.Estado.INSCRIPCION_CERRADA:
            raise FixtureError(
                "Cierra las inscripciones del campeonato antes de generar el fixture "
                "(estado «Inscripciones cerradas»)."
            )
        equipos = [
            i.equipo
            for i in Inscripcion.objects.filter(
                campeonato=campeonato, estado=Inscripcion.Estado.APROBADA, equipo__estado="ACTIVO",
            ).select_related("equipo").order_by("fecha_inscripcion", "pk")
        ]
        if len(equipos) < 2:
            raise FixtureError(
                "Se necesitan al menos 2 equipos con inscripción aprobada para generar el fixture."
            )

        siembra = None
        if sembrar_con_ml and campeonato.formato == Campeonato.Formato.ELIMINACION:
            equipos, siembra = self._sembrar(equipos)

        with transaction.atomic():
            Campeonato.objects.select_for_update().get(pk=campeonato.pk)
            protegidos = Partido.objects.filter(campeonato=campeonato).filter(
                estado__in=[Partido.Estado.FINALIZADO, Partido.Estado.WALKOVER, Partido.Estado.EN_CURSO]
            ).count()
            if protegidos:
                raise FixtureConflicto(
                    f"El campeonato tiene {protegidos} partido(s) con resultado o en curso; "
                    "no se puede regenerar el fixture sin perderlos."
                )
            Partido.objects.filter(campeonato=campeonato).delete()

            plan = self._planificar(equipos)
            asignaciones, por_ml, aviso, info_ml = self._asignar(plan, equipos, usar_ml)
            partidos = self._crear(plan, asignaciones, por_ml)
            tabla.recalcular(campeonato)
            self.resultado = {
                "generado_por_ml": por_ml,
                "aviso": aviso,
                "calidad": metricas.calcular_calidad(campeonato),
                "ml": info_ml,
                "siembra": siembra,
            }
        return partidos

    def _sembrar(self, equipos):
        """F7-07 — Ordena a los equipos por nivel de rendimiento (K-means) para que los mejores no se crucen temprano."""
        from apps.ml.services import niveles
        analisis = niveles.analizar(self.campeonato)
        if not analisis["datos_suficientes"]:
            return equipos, {"aplicada": False, "motivo": analisis["motivo"]}
        por_id = {e.pk: e for e in equipos}
        ordenados = [por_id[i] for i in analisis["orden_siembra"] if i in por_id]
        return ordenados, {"aplicada": True, "metodo": analisis["metodo"], "niveles": analisis["k"],
                           "orden": [{"semilla": d["semilla"], "equipo": d["nombre"], "nivel": d["nivel"]} for d in analisis["equipos"]],
                           "motivo": analisis["motivo"]}

    # ── 1. Plan ───────────────────────────────────────────────────────────────

    def _planificar(self, equipos) -> list[PartidoPlan]:
        if self.campeonato.formato == Campeonato.Formato.ELIMINACION:
            return self._plan_eliminacion(equipos)
        return self._plan_liga(equipos)

    def _plan_liga(self, equipos) -> list[PartidoPlan]:
        jornadas = _round_robin(equipos)
        if self.doble_vuelta:
            jornadas += [[(v, l) for l, v in jornada] for jornada in jornadas]
        return [
            PartidoPlan(jornada=numero, local=local, visitante=visitante, fase="Liga")
            for numero, enfrentamientos in enumerate(jornadas, start=1)
            for local, visitante in enfrentamientos
        ]

    def _plan_eliminacion(self, equipos) -> list[PartidoPlan]:
        tamano = 1
        while tamano < len(equipos):
            tamano *= 2
        total_rondas = tamano.bit_length() - 1
        # Entradas: ("equipo", Equipo) | ("plan", indice) | None (BYE)
        entradas = [
            ("equipo", equipos[semilla - 1]) if semilla <= len(equipos) else None
            for semilla in orden_de_siembra(tamano)
        ]
        plan: list[PartidoPlan] = []
        for ronda in range(1, total_rondas + 1):
            siguientes = []
            for izquierda, derecha in zip(entradas[0::2], entradas[1::2]):
                if izquierda is None or derecha is None:
                    siguientes.append(izquierda or derecha)  # BYE: avanza directo
                    continue
                spec = PartidoPlan(jornada=ronda, local=None, visitante=None,
                                   fase=nombre_ronda(ronda, total_rondas), ronda=ronda)
                for lado, entrada in (("local", izquierda), ("visitante", derecha)):
                    tipo, valor = entrada
                    if tipo == "equipo":
                        setattr(spec, lado, valor)
                    else:
                        setattr(spec, f"origen_{lado}", valor)
                plan.append(spec)
                siguientes.append(("plan", len(plan) - 1))
            entradas = siguientes
        return plan

    # ── 2. Asignación de cancha y horario ─────────────────────────────────────

    def _asignar(self, plan, equipos, usar_ml):
        """Devuelve (asignaciones, generado_por_ml, aviso, info_ml). asignaciones = [(cancha, slot)]."""
        deporte = self.campeonato.categoria.deporte
        aviso = ""
        if usar_ml:
            try:
                r = fixture_optimizer.optimizar_fixture(self.campeonato, plan, equipos, self.hora_inicio,
                                      self.dias_entre_jornadas, self.DURACION_PARTIDO_MINUTOS)
                info = {"modelo_version": r.modelo_version, "puntaje_medio": round(r.puntaje_medio, 3),
                        "segundos": round(r.segundos, 2), "jornadas": r.jornadas, "tiempos": r.tiempos}
                return r.asignaciones, True, "", info
            except fixture_optimizer.OptimizadorSinSolucion as e:
                aviso = f"El optimizador con ML no encontró solución ({e}) Se usó el método base."
            except ModeloNoDisponible as e:
                aviso = f"El modelo de ML no está disponible ({e}) Se usó el método base."
            except Exception:  # noqa: BLE001 - un fallo inesperado del ML nunca debe impedir generar el fixture
                logger.exception("Fallo inesperado del optimizador ML; se usa el método base.")
                aviso = "El módulo de ML falló de forma inesperada. Se usó el método base."

        from apps.instalaciones.models import Cancha
        if not Cancha.objects.filter(deporte=deporte, activa=True).exists():
            raise FixtureError("No hay canchas activas para el deporte del campeonato.")
        return self._asignar_base(plan, equipos), False, aviso, None

    def _asignar_base(self, plan, equipos):
        disp = Disponibilidad(self.campeonato, equipos, self.hora_inicio, self.dias_entre_jornadas,
                              self.DURACION_PARTIDO_MINUTOS, paso_min=PASO_MINUTOS)
        asignaciones = []
        for spec in plan:
            participantes = [e.pk for e in (spec.local, spec.visitante) if e is not None]
            facultades = [e.facultad_id for e in (spec.local, spec.visitante) if e is not None]
            elegido = None
            for slot in disp.ventana(spec.jornada):
                if not all(disp.equipo_libre(e, slot) for e in participantes):
                    continue
                if any(disp.facultad_restringida(f, slot) for f in facultades):
                    continue
                cancha = next((c for c in disp.canchas if disp.cancha_libre(c, slot)), None)
                if cancha is not None:
                    elegido = (cancha, slot)
                    break
            if elegido is None:
                etiqueta = (f"{spec.local.nombre} vs {spec.visitante.nombre}" if spec.local and spec.visitante
                            else f"un partido de {spec.fase}")
                raise FixtureError(
                    f"No hay cancha y horario disponibles para programar {etiqueta} en la "
                    f"jornada {spec.jornada}. Revisa los horarios de las canchas, los bloqueos y las "
                    "restricciones de facultad, o aumenta los días entre jornadas."
                )
            disp.reservar(elegido[0], elegido[1], participantes)
            asignaciones.append(elegido)
        return asignaciones

    # ── 3. Creación ───────────────────────────────────────────────────────────

    def _crear(self, plan, asignaciones, por_ml: bool) -> list[Partido]:
        creados: list[Partido] = []
        for spec, (cancha, slot) in zip(plan, asignaciones):
            creados.append(Partido.objects.create(
                campeonato=self.campeonato,
                equipo_local=spec.local,
                equipo_visitante=spec.visitante,
                cancha=cancha,
                fecha_hora=slot.inicio,
                duracion_min=self.DURACION_PARTIDO_MINUTOS,
                jornada=spec.jornada,
                fase=spec.fase,
                ronda=spec.ronda,
                partido_origen_local=creados[spec.origen_local] if spec.origen_local is not None else None,
                partido_origen_visitante=creados[spec.origen_visitante] if spec.origen_visitante is not None else None,
                generado_por_ml=por_ml,
            ))
        return creados
