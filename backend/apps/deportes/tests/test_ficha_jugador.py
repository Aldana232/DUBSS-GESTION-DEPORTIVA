import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.deportes.models import Equipo, Facultad, FichaJugador
from apps.users.models import Usuario


@pytest.mark.django_db
def test_ficha_se_crea_sin_cuenta_y_carnet_es_unico_por_equipo():
    admin = Usuario.objects.create_superuser(
        email="admin-ficha@example.com",
        password="PruebaSegura123!",
        nombre="Ada",
        apellido="Admin",
    )
    facultad = Facultad.objects.create(nombre="Ingeniería", sigla="ING")
    equipo = Equipo.objects.create(nombre="Tigres", facultad=facultad)
    otro_equipo = Equipo.objects.create(nombre="Pumas", facultad=facultad)
    client = APIClient()
    client.force_authenticate(admin)
    datos = {
        "equipo": equipo.pk,
        "nombre": "Lucía",
        "apellido": "Pérez",
        "carnet": "123456",
        "registro": "REG-123",
        "posicion": "Delantera",
        "numero_camiseta": 0,
        "estado": "ACTIVO",
    }

    respuesta = client.post(reverse("jugador-list"), datos, format="json")

    assert respuesta.status_code == 201
    ficha = FichaJugador.objects.get(pk=respuesta.data["id"])
    assert ficha.usuario is None
    assert ficha.numero_camiseta == 0
    assert ficha.partidos_sancion_restantes == 0

    respuesta_duplicada = client.post(reverse("jugador-list"), datos, format="json")
    assert respuesta_duplicada.status_code == 400
    assert FichaJugador.objects.filter(equipo=equipo, carnet="123456").count() == 1

    ficha_otro_equipo = FichaJugador.objects.create(
        equipo=otro_equipo,
        nombre="Mario",
        apellido="Rojas",
        carnet="123456",
        registro="REG-456",
        posicion="Defensa",
    )
    assert ficha_otro_equipo.carnet == ficha.carnet
