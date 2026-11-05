from datetime import date, timedelta

import pytest
from django.utils import timezone

from apps.deportes.models import (
    Campeonato,
    Categoria,
    Deporte,
    Equipo,
    Facultad,
    FichaJugador,
    Inscripcion,
    RestriccionHorarioFacultad,
)
from apps.deportes.services import validar_elegibilidad


@pytest.mark.django_db
def test_validar_elegibilidad_retorna_cada_motivo_de_rechazo():
    facultad = Facultad.objects.create(nombre="Ciencias", sigla="CIE")
    deporte = Deporte.objects.create(nombre="Futsal elegibilidad")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Primera")
    campeonato = Campeonato.objects.create(
        nombre="Campeonato elegibilidad",
        categoria=categoria,
        estado=Campeonato.Estado.INSCRIPCIONES,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        min_jugadores=2,
        max_jugadores=4,
        fecha_cierre_inscripcion=timezone.now() - timedelta(days=1),
    )
    equipo = Equipo.objects.create(nombre="Águilas", facultad=facultad)
    otro_equipo = Equipo.objects.create(nombre="Cóndores", facultad=facultad)
    inscripcion = Inscripcion.objects.create(
        campeonato=campeonato,
        equipo=equipo,
        estado=Inscripcion.Estado.APROBADA,
    )
    otra_inscripcion = Inscripcion.objects.create(
        campeonato=campeonato,
        equipo=otro_equipo,
        estado=Inscripcion.Estado.APROBADA,
    )
    campeonato_maximo = Campeonato.objects.create(
        nombre="Campeonato máximo",
        categoria=categoria,
        estado=Campeonato.Estado.INSCRIPCIONES,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        min_jugadores=0,
        max_jugadores=0,
    )
    inscripcion_maxima = Inscripcion.objects.create(
        campeonato=campeonato_maximo,
        equipo=equipo,
        estado=Inscripcion.Estado.APROBADA,
    )
    ficha = FichaJugador.objects.create(
        equipo=equipo,
        nombre="Lucía",
        apellido="Pérez",
        carnet="CARNET-1",
        registro="REG-1",
        posicion="Defensa",
        partidos_sancion_restantes=1,
    )
    FichaJugador.objects.create(
        equipo=otro_equipo,
        nombre="Lucía",
        apellido="Pérez",
        carnet="CARNET-1",
        registro="REG-2",
        posicion="Defensa",
    )

    motivos = validar_elegibilidad(ficha, inscripcion)
    motivos_maximos = validar_elegibilidad(ficha, inscripcion_maxima)
    motivos_equipo_ajeno = validar_elegibilidad(ficha, otra_inscripcion)

    assert any("otro equipo" in motivo for motivo in motivos)
    assert any("sanción" in motivo for motivo in motivos)
    assert any("mínimo" in motivo for motivo in motivos)
    assert any("máximo" in motivo for motivo in motivos_maximos)
    assert any("cerrado" in motivo for motivo in motivos)
    assert any("no pertenece" in motivo for motivo in motivos_equipo_ajeno)


@pytest.mark.django_db
def test_validar_elegibilidad_no_rechaza_ficha_valida():
    facultad = Facultad.objects.create(nombre="Ingeniería", sigla="ING")
    deporte = Deporte.objects.create(nombre="Voleibol elegibilidad")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Mayores")
    campeonato = Campeonato.objects.create(
        nombre="Torneo válido",
        categoria=categoria,
        estado=Campeonato.Estado.INSCRIPCIONES,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        min_jugadores=1,
        max_jugadores=12,
    )
    equipo = Equipo.objects.create(nombre="Tigres", facultad=facultad)
    inscripcion = Inscripcion.objects.create(
        campeonato=campeonato,
        equipo=equipo,
        estado=Inscripcion.Estado.PENDIENTE,
    )
    ficha = FichaJugador.objects.create(
        equipo=equipo,
        nombre="Mario",
        apellido="Rojas",
        carnet="CARNET-2",
        registro="REG-2",
        posicion="Armador",
    )

    assert validar_elegibilidad(ficha, inscripcion) == []


@pytest.mark.django_db
def test_restriccion_horario_facultad_tiene_api_admin_solo():
    from django.urls import reverse
    from rest_framework.test import APIClient

    from apps.users.models import Usuario

    facultad = Facultad.objects.create(nombre="Medicina", sigla="MED")
    admin = Usuario.objects.create_superuser(
        email="admin-restriccion@example.com",
        password="PruebaSegura123!",
        nombre="Ada",
        apellido="Admin",
    )
    client = APIClient()
    client.force_authenticate(admin)
    respuesta = client.post(
        reverse("restriccion-horario-list"),
        {
            "facultad": facultad.pk,
            "dia_semana": RestriccionHorarioFacultad.DiaSemana.LUNES,
            "hora_inicio": "09:00",
            "hora_fin": "08:00",
            "motivo": "Clases obligatorias",
        },
        format="json",
    )

    assert respuesta.status_code == 400
    assert RestriccionHorarioFacultad.objects.count() == 0
