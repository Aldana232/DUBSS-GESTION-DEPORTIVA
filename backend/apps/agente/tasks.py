import logging

from celery import shared_task

from apps.agente.services.acciones import expirar_vencidas

logger = logging.getLogger(__name__)


@shared_task(name="agente.expirar_acciones")
def expirar_acciones():
    """Las acciones que nadie confirmó a tiempo pasan a EXPIRADA (nunca se ejecutan solas)."""
    n = expirar_vencidas()
    if n:
        logger.info("Acciones del agente expiradas: %s", n)
    return n
