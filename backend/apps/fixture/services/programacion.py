"""
apps/fixture/services/programacion.py
F3-09 — Detección de conflictos al programar o reprogramar un partido.
"""
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from apps.deportes.services import facultad_tiene_restriccion
from apps.fixture.models import Partido
from apps.instalaciones.models import BloqueoCancha, HorarioCancha


class ConflictoProgramacion(APIException):
    """409: el horario o la cancha elegidos chocan con otra reserva o restricción."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "El horario elegido tiene conflictos."
    default_code = "conflicto_programacion"

    def __init__(self, conflictos: list[str]):
        super().__init__({
            "detail": "No se puede programar el partido: " + " ".join(conflictos),
            "conflictos": conflictos,
        })
        self.conflictos = conflictos


def _descripcion_partido(p: Partido) -> str:
    local = p.equipo_local.nombre if p.equipo_local_id else "Por definir"
    visitante = p.equipo_visitante.nombre if p.equipo_visitante_id else "Por definir"
    inicio = timezone.localtime(p.fecha_hora)
    return f"{local} vs {visitante} ({p.campeonato.nombre}, {inicio:%d/%m/%Y %H:%M})"


def partidos_solapados(inicio, fin, *, cancha=None, equipos=(), excluir_partido_id=None, excluir_ids=()):
    """Partidos que se solapan con [inicio, fin) en la cancha o con alguno de los equipos."""
    filtro = Q()
    if cancha is not None:
        filtro |= Q(cancha=cancha)
    equipos = [e for e in equipos if e is not None]
    if equipos:
        filtro |= Q(equipo_local__in=equipos) | Q(equipo_visitante__in=equipos)
    if not filtro:
        return Partido.objects.none()
    qs = Partido.objects.filter(
        filtro, fecha_hora__lt=fin, fecha_hora_fin__gt=inicio
    ).select_related("equipo_local", "equipo_visitante", "campeonato")
    if excluir_partido_id is not None:
        qs = qs.exclude(pk=excluir_partido_id)
    if excluir_ids:
        qs = qs.exclude(pk__in=list(excluir_ids))
    return qs


def detectar_conflictos(
    *, cancha, fecha_hora, duracion_min, equipo_local, equipo_visitante, partido_id=None, excluir_ids=()
) -> list[str]:
    """Devuelve los motivos (en español) por los que el partido no puede ir ahí."""
    if timezone.is_naive(fecha_hora):
        return ["La fecha y hora deben incluir zona horaria."]
    duracion = timedelta(minutes=duracion_min)
    fin = fecha_hora + duracion
    inicio_local = timezone.localtime(fecha_hora)
    if inicio_local.date() != timezone.localtime(fin).date():
        return ["El partido no puede cruzar la medianoche."]

    conflictos: list[str] = []
    solapados = list(partidos_solapados(
        fecha_hora, fin, cancha=cancha, equipos=(equipo_local, equipo_visitante),
        excluir_partido_id=partido_id, excluir_ids=excluir_ids,
    ))

    if cancha is not None:
        if not cancha.activa:
            conflictos.append(f"La cancha {cancha.nombre} está inactiva.")
        else:
            tiene_franja = HorarioCancha.objects.filter(
                cancha=cancha,
                dia_semana=inicio_local.weekday(),
                hora_inicio__lte=inicio_local.time().replace(tzinfo=None),
                hora_fin__gte=timezone.localtime(fin).time().replace(tzinfo=None),
            ).exists()
            if not tiene_franja:
                conflictos.append(
                    f"La cancha {cancha.nombre} no tiene una franja horaria habilitada "
                    "para ese día y hora."
                )
            bloqueo = BloqueoCancha.objects.filter(
                cancha=cancha, fecha_inicio__lt=fin, fecha_fin__gt=fecha_hora
            ).first()
            if bloqueo:
                conflictos.append(
                    f"La cancha {cancha.nombre} está bloqueada ({bloqueo.get_tipo_display()}: "
                    f"{bloqueo.motivo})."
                )
        for p in solapados:
            if p.cancha_id == cancha.pk:
                conflictos.append(
                    f"La cancha {cancha.nombre} ya está ocupada por {_descripcion_partido(p)}."
                )

    for equipo in (equipo_local, equipo_visitante):
        if equipo is None:
            continue
        for p in solapados:
            if equipo.pk in (p.equipo_local_id, p.equipo_visitante_id):
                conflictos.append(
                    f"El equipo {equipo.nombre} ya juega {_descripcion_partido(p)}."
                )

    facultades = [e.facultad_id for e in (equipo_local, equipo_visitante) if e is not None]
    if facultades and facultad_tiene_restriccion(facultades, fecha_hora, duracion):
        conflictos.append("Una de las facultades tiene una restricción horaria en ese momento.")

    # Sin duplicados, conservando el orden.
    return list(dict.fromkeys(conflictos))
