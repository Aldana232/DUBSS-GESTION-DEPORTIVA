from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.utils import timezone

from .models import BloqueoCancha, Cancha


def canchas_disponibles(fecha_hora, duracion, deporte=None, excluir_partido_id=None):
    """
    Canchas libres para jugar en [fecha_hora, fecha_hora + duracion): dentro de
    una franja habilitada, sin bloqueos y sin otro partido (de cualquier
    campeonato) que se solape. `excluir_partido_id` sirve para reprogramar un
    partido sin que choque consigo mismo.
    """
    from apps.fixture.models import Partido

    if timezone.is_naive(fecha_hora):
        raise ValueError("La fecha y hora deben incluir zona horaria.")
    if not isinstance(duracion, timedelta) or duracion <= timedelta(0):
        raise ValueError("La duración debe ser un timedelta positivo.")

    fecha_hora_fin = fecha_hora + duracion
    inicio_local = timezone.localtime(fecha_hora)
    fin_local = timezone.localtime(fecha_hora_fin)
    if inicio_local.date() != fin_local.date():
        raise ValidationError("El horario del partido no puede cruzar la medianoche.")

    canchas = Cancha.objects.filter(
        activa=True,
        instalacion__estado="ACTIVA",
        horarios__dia_semana=inicio_local.weekday(),
        horarios__hora_inicio__lte=inicio_local.time().replace(tzinfo=None),
        horarios__hora_fin__gte=fin_local.time().replace(tzinfo=None),
    )
    if deporte is not None:
        canchas = canchas.filter(deporte=deporte)
    bloqueadas = BloqueoCancha.objects.filter(
        cancha=OuterRef("pk"),
        fecha_inicio__lt=fecha_hora_fin,
        fecha_fin__gt=fecha_hora,
    )
    ocupadas = Partido.objects.filter(
        cancha=OuterRef("pk"),
        fecha_hora__lt=fecha_hora_fin,
        fecha_hora_fin__gt=fecha_hora,
    )
    if excluir_partido_id is not None:
        ocupadas = ocupadas.exclude(pk=excluir_partido_id)
    return canchas.exclude(Exists(bloqueadas)).exclude(Exists(ocupadas)).distinct()
