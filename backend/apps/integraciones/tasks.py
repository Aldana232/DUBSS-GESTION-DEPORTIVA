from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from . import servicios
from .models import EventoSaliente


@shared_task(name="integraciones.despachar_eventos")
def despachar_eventos() -> dict:
    """Entrega los eventos pendientes a n8n (cada minuto por beat y a demanda al encolar uno)."""
    return servicios.despachar()


@shared_task(name="integraciones.purgar_eventos")
def purgar_eventos() -> dict:
    """Los entregados se conservan 30 días; los fallidos 90 (para poder investigarlos)."""
    ahora = timezone.now()
    e, _ = EventoSaliente.objects.filter(estado=EventoSaliente.Estado.ENTREGADO, creado__lt=ahora - timedelta(days=30)).delete()
    f, _ = EventoSaliente.objects.filter(estado=EventoSaliente.Estado.FALLIDO, creado__lt=ahora - timedelta(days=90)).delete()
    return {"entregados": e, "fallidos": f}
