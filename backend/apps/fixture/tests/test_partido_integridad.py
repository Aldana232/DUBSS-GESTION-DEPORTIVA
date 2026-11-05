from datetime import date, timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.deportes.models import Campeonato, Categoria, Deporte, Equipo, Facultad
from apps.fixture.models import Partido
from apps.instalaciones.models import Cancha, Instalacion


def crear_campeonato(nombre, deporte):
    categoria = Categoria.objects.create(deporte=deporte, nombre=f"Categoría {nombre}")
    return Campeonato.objects.create(
        nombre=nombre,
        categoria=categoria,
        estado=Campeonato.Estado.INSCRIPCIONES,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
    )


@pytest.mark.django_db
def test_partido_rechaza_solapamiento_en_la_misma_cancha():
    deporte = Deporte.objects.create(nombre="Fútbol integridad")
    campeonato_uno = crear_campeonato("Fixture uno", deporte)
    campeonato_dos = crear_campeonato("Fixture dos", deporte)
    facultad = Facultad.objects.create(nombre="Facultad integridad", sigla="FIN")
    equipo_local = Equipo.objects.create(nombre="Local integridad", facultad=facultad)
    equipo_visitante = Equipo.objects.create(
        nombre="Visitante integridad",
        facultad=facultad,
    )
    instalacion = Instalacion.objects.create(
        nombre="Instalación integridad",
        ubicacion="Campus",
    )
    cancha = Cancha.objects.create(
        instalacion=instalacion,
        nombre="Cancha integridad",
        deporte=deporte,
    )
    inicio = timezone.now() + timedelta(days=1)
    partido = Partido.objects.create(
        campeonato=campeonato_uno,
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
        cancha=cancha,
        fecha_hora=inicio,
    )

    assert partido.duracion_min == 90
    assert partido.fecha_hora_fin == inicio + timedelta(minutes=90)
    assert partido.instalacion == instalacion

    with pytest.raises(IntegrityError), transaction.atomic():
        Partido.objects.create(
            campeonato=campeonato_dos,
            equipo_local=equipo_local,
            equipo_visitante=equipo_visitante,
            cancha=cancha,
            fecha_hora=inicio + timedelta(minutes=30),
        )


@pytest.mark.django_db
def test_partido_permite_partidos_adyacentes_en_la_misma_cancha():
    deporte = Deporte.objects.create(nombre="Vóley integridad")
    campeonato = crear_campeonato("Fixture adyacente", deporte)
    facultad = Facultad.objects.create(nombre="Facultad adyacente", sigla="FAD")
    equipos = [
        Equipo.objects.create(nombre=f"Equipo adyacente {numero}", facultad=facultad)
        for numero in range(1, 5)
    ]
    instalacion = Instalacion.objects.create(
        nombre="Instalación adyacente",
        ubicacion="Campus",
    )
    cancha = Cancha.objects.create(
        instalacion=instalacion,
        nombre="Cancha adyacente",
        deporte=deporte,
    )
    inicio = timezone.now() + timedelta(days=2)

    primero = Partido.objects.create(
        campeonato=campeonato,
        equipo_local=equipos[0],
        equipo_visitante=equipos[1],
        cancha=cancha,
        fecha_hora=inicio,
        jornada=1,
    )
    segundo = Partido.objects.create(
        campeonato=campeonato,
        equipo_local=equipos[2],
        equipo_visitante=equipos[3],
        cancha=cancha,
        fecha_hora=primero.fecha_hora_fin,
        jornada=1,
    )

    assert segundo.fecha_hora == primero.fecha_hora_fin
    assert segundo.fecha_hora_fin > segundo.fecha_hora


@pytest.mark.django_db
def test_partido_rechaza_mismos_equipos_y_enfrentamiento_duplicado():
    deporte = Deporte.objects.create(nombre="Básquet integridad")
    campeonato = crear_campeonato("Fixture constraints", deporte)
    facultad = Facultad.objects.create(nombre="Facultad constraints", sigla="FCO")
    equipos = [
        Equipo.objects.create(nombre=f"Equipo constraints {numero}", facultad=facultad)
        for numero in range(1, 3)
    ]
    inicio = timezone.now() + timedelta(days=3)
    partido = Partido.objects.create(
        campeonato=campeonato,
        equipo_local=equipos[0],
        equipo_visitante=equipos[1],
        fecha_hora=inicio,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        Partido.objects.create(
            campeonato=campeonato,
            equipo_local=equipos[0],
            equipo_visitante=equipos[0],
            fecha_hora=inicio + timedelta(days=1),
            jornada=2,
        )

    with pytest.raises(IntegrityError), transaction.atomic():
        Partido.objects.create(
            campeonato=campeonato,
            equipo_local=equipos[0],
            equipo_visitante=equipos[1],
            fecha_hora=inicio + timedelta(days=1),
            jornada=partido.jornada,
        )
