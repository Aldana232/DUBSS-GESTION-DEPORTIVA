"""
apps/fixture/tasks.py
F6-03 — Mantenimiento de la tabla de posiciones y su historial.
"""
from celery import shared_task

from apps.deportes.models import Campeonato
from apps.fixture.services import tabla


@shared_task(name="fixture.reconstruir_historial")
def reconstruir_historial() -> dict:
    """
    Reconstruye tabla e historial por jornada de los campeonatos en curso desde los resultados.
    Es una red de seguridad idempotente: el sistema ya los recalcula al registrar o corregir cada
    resultado, y esta tarea repara cualquier desfase (por ejemplo, ediciones directas en la base).
    """
    campeonatos = list(Campeonato.objects.filter(estado=Campeonato.Estado.EN_CURSO))
    for campeonato in campeonatos:
        tabla.recalcular(campeonato)
    return {"campeonatos": len(campeonatos)}


@shared_task(name="fixture.purgar_operaciones_idempotentes")
def purgar_operaciones_idempotentes(dias: int = 7) -> int:
    """Las claves de idempotencia solo sirven mientras un celular pueda reintentar: se borran las de más de `dias`."""
    from datetime import timedelta

    from django.utils import timezone

    from apps.fixture.models import OperacionIdempotente
    borradas, _ = OperacionIdempotente.objects.filter(creado_en__lt=timezone.now() - timedelta(days=dias)).delete()
    return borradas
