"""
apps/notificaciones/tasks.py
F6-03 — Recordatorios de partido (24 h y 2 h antes). Idempotente: `RecordatorioEnviado` es único por
(partido, tipo), así que ejecutar la tarea varias veces no duplica avisos.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.deportes.models import Campeonato
from apps.fixture.models import Partido
from apps.ml.services.clima import ultimo_riesgo
from apps.notificaciones.models import RecordatorioEnviado
from apps.notificaciones.services import notificar_usuarios

logger = logging.getLogger(__name__)
T = RecordatorioEnviado.Tipo


def _tipo_que_corresponde(faltan: timedelta) -> str | None:
    """24H si faltan entre 2 y 24 horas; 2H si faltan menos de 2 horas (y el partido no empezó)."""
    if timedelta(0) < faltan <= timedelta(hours=2):
        return T.DOS_HORAS
    if timedelta(hours=2) < faltan <= timedelta(hours=24):
        return T.VEINTICUATRO_HORAS
    return None


def _texto(partido: Partido, tipo: str) -> tuple[str, str]:
    inicio = timezone.localtime(partido.fecha_hora)
    cuando = "mañana" if tipo == T.VEINTICUATRO_HORAS and inicio.date() != timezone.localdate() else "hoy"
    lugar = f" en {partido.cancha.nombre}" if partido.cancha else ""
    texto = f"{partido.equipo_local} vs {partido.equipo_visitante}, {cuando} a las {inicio:%H:%M}{lugar}."
    riesgo = ultimo_riesgo(partido)
    if riesgo and riesgo.nivel_riesgo in ("ALTO", "CRITICO"):
        texto += f" Atención: riesgo climático {riesgo.get_nivel_riesgo_display().lower()}."
    titulo = "Partido en 2 horas" if tipo == T.DOS_HORAS else "Recordatorio de partido"
    return titulo, texto


@shared_task(name="notificaciones.enviar_recordatorios")
def enviar_recordatorios() -> dict:
    ahora = timezone.now()
    candidatos = Partido.objects.filter(
        estado=Partido.Estado.PROGRAMADO,
        campeonato__estado=Campeonato.Estado.EN_CURSO,        # solo fixtures publicados
        equipo_local__isnull=False, equipo_visitante__isnull=False,
        fecha_hora__gt=ahora, fecha_hora__lte=ahora + timedelta(hours=24),
    ).select_related("equipo_local__delegado", "equipo_visitante__delegado", "cancha")

    enviados = 0
    for partido in candidatos:
        tipo = _tipo_que_corresponde(partido.fecha_hora - ahora)
        if tipo is None or RecordatorioEnviado.objects.filter(partido=partido, tipo=tipo).exists():
            continue
        delegados = [partido.equipo_local.delegado, partido.equipo_visitante.delegado]
        titulo, texto = _texto(partido, tipo)
        try:
            with transaction.atomic():
                # Se reserva primero: si dos workers coinciden, solo uno pasa el UNIQUE y envía.
                registro = RecordatorioEnviado.objects.create(partido=partido, tipo=tipo)
                resumen = notificar_usuarios(delegados, titulo, texto, {"partido_id": partido.pk, "tipo": tipo})
                registro.destinatarios = resumen["usuarios"]
                registro.save(update_fields=["destinatarios"])
            enviados += 1
        except IntegrityError:
            continue
    logger.info("Recordatorios enviados: %s", enviados)
    return {"enviados": enviados}
