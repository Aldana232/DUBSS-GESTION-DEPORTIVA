"""Endpoint de salud (sin sesión): lo usan Docker y los monitores para saber si el sistema responde."""
import logging

from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _base_de_datos() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        logger.exception("La comprobación de salud no pudo consultar la base de datos.")
        return False


def _redis() -> bool:
    from django.conf import settings

    try:
        import redis

        redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2).ping()
        return True
    except Exception:  # noqa: BLE001
        return False


def salud(request):
    """
    200 si la base de datos responde (aunque Redis falle: el sistema sigue sirviendo, solo se pausan las tareas
    en segundo plano y se marca «degradado»); 503 si no hay base de datos. No expone datos internos.
    """
    bd, rd = _base_de_datos(), _redis()
    estado = "ok" if bd and rd else "degradado" if bd else "caido"
    return JsonResponse({"estado": estado, "base_de_datos": bd, "redis": rd}, status=200 if bd else 503)
