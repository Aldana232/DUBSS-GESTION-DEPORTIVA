from datetime import date

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.deportes.models import (
    Campeonato,
    Categoria,
    Deporte,
    Equipo,
    Facultad,
    FichaJugador,
)
from apps.fixture.models import Incidencia, Partido
from apps.users.models import Usuario


@pytest.fixture
def escenario_partido(db):
    admin = Usuario.objects.create_user(
        email="admin-resultado-incidencias@example.com",
        password="prueba-segura-123",
        nombre="Admin",
        apellido="Resultado",
        rol=Usuario.Rol.ADMIN_DUBSS,
    )
    deporte = Deporte.objects.create(nombre="Fútbol incidencias")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Primera incidencias")
    campeonato = Campeonato.objects.create(
        nombre="Campeonato incidencias",
        categoria=categoria,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
    )
    facultad = Facultad.objects.create(nombre="Facultad incidencias", sigla="FIN")
    local = Equipo.objects.create(nombre="Local incidencias", facultad=facultad)
    visitante = Equipo.objects.create(nombre="Visitante incidencias", facultad=facultad)
    jugadores = [
        FichaJugador.objects.create(
            equipo=equipo,
            nombre=f"Jugador {numero}",
            apellido="Incidencias",
            carnet=f"CI-{numero}",
            registro=f"REG-{numero}",
            posicion="Delantero",
        )
        for numero, equipo in enumerate((local, visitante), start=1)
    ]
    partido = Partido.objects.create(
        campeonato=campeonato,
        equipo_local=local,
        equipo_visitante=visitante,
        fecha_hora=timezone.now(),
    )
    client = APIClient()
    client.force_authenticate(admin)
    return client, partido, jugadores


@pytest.mark.django_db
def test_resultado_coincide_con_incidencias_de_gol(escenario_partido):
    client, partido, jugadores = escenario_partido
    Incidencia.objects.create(partido=partido, tipo=Incidencia.Tipo.GOL, jugador=jugadores[0])
    Incidencia.objects.create(partido=partido, tipo=Incidencia.Tipo.GOL, jugador=jugadores[0])
    Incidencia.objects.create(partido=partido, tipo=Incidencia.Tipo.GOL, jugador=jugadores[1])

    respuesta = client.post(
        reverse("partido-registrar-resultado", kwargs={"pk": partido.pk}),
        {"goles_local": 2, "goles_visitante": 1},
        format="json",
    )

    assert respuesta.status_code == 201


@pytest.mark.django_db
def test_resultado_rechaza_marcador_distinto_a_incidencias_de_gol(escenario_partido):
    client, partido, jugadores = escenario_partido
    Incidencia.objects.create(partido=partido, tipo=Incidencia.Tipo.GOL, jugador=jugadores[0])
    Incidencia.objects.create(partido=partido, tipo=Incidencia.Tipo.GOL, jugador=jugadores[1])

    respuesta = client.post(
        reverse("partido-registrar-resultado", kwargs={"pk": partido.pk}),
        {"goles_local": 0, "goles_visitante": 2},
        format="json",
    )

    assert respuesta.status_code == 400
    assert "marcador" in str(respuesta.data).lower()


@pytest.mark.django_db
def test_resultado_rechaza_gol_sin_jugador_identificable(escenario_partido):
    client, partido, _ = escenario_partido
    Incidencia.objects.create(partido=partido, tipo=Incidencia.Tipo.GOL)

    respuesta = client.post(
        reverse("partido-registrar-resultado", kwargs={"pk": partido.pk}),
        {"goles_local": 1, "goles_visitante": 0},
        format="json",
    )

    assert respuesta.status_code == 400
    assert "jugador" in str(respuesta.data).lower()
