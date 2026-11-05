from datetime import datetime, time, timedelta

import pytest
from django.utils import timezone

from apps.deportes.models import Deporte
from apps.instalaciones.models import (
    BloqueoCancha,
    Cancha,
    HorarioCancha,
    Instalacion,
)
from apps.instalaciones.services import canchas_disponibles


@pytest.mark.django_db
def test_canchas_disponibles_respeta_franja_y_bloqueo():
    deporte = Deporte.objects.create(nombre="Futsal disponibilidad")
    instalacion = Instalacion.objects.create(
        nombre="Coliseo disponibilidad",
        ubicacion="Campus",
        tipo="Coliseo",
        capacidad=100,
    )
    cancha = Cancha.objects.create(
        instalacion=instalacion,
        nombre="Cancha cubierta",
        deporte=deporte,
    )
    dia = datetime(2026, 1, 5).weekday()
    HorarioCancha.objects.create(
        cancha=cancha,
        dia_semana=dia,
        hora_inicio=time(9),
        hora_fin=time(12),
    )
    inicio = timezone.make_aware(datetime(2026, 1, 5, 10))
    duracion = timedelta(minutes=60)

    assert list(canchas_disponibles(inicio, duracion, deporte)) == [cancha]

    BloqueoCancha.objects.create(
        cancha=cancha,
        fecha_inicio=inicio + timedelta(minutes=30),
        fecha_fin=inicio + timedelta(minutes=90),
        tipo=BloqueoCancha.Tipo.MANTENIMIENTO,
        motivo="Mantenimiento",
    )
    assert list(canchas_disponibles(inicio, duracion, deporte)) == []


@pytest.mark.django_db
def test_canchas_disponibles_exige_horario_completo_y_fecha_con_zona():
    deporte = Deporte.objects.create(nombre="Voleibol disponibilidad")
    instalacion = Instalacion.objects.create(
        nombre="Gimnasio disponibilidad",
        ubicacion="Campus",
    )
    Cancha.objects.create(
        instalacion=instalacion,
        nombre="Cancha sin horario",
        deporte=deporte,
    )
    inicio = timezone.make_aware(datetime(2026, 1, 5, 10))

    assert list(canchas_disponibles(inicio, timedelta(minutes=30), deporte)) == []
    with pytest.raises(ValueError, match="zona horaria"):
        canchas_disponibles(datetime(2026, 1, 5, 10), timedelta(minutes=30))
    with pytest.raises(ValueError, match="positivo"):
        canchas_disponibles(inicio, timedelta(0))
