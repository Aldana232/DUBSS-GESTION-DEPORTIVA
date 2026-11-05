from datetime import date

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.deportes.models import Campeonato, Categoria, Deporte
from apps.users.models import Usuario


@pytest.mark.django_db
def test_campeonato_deriva_deporte_de_categoria_y_valida_jugadores():
    admin = Usuario.objects.create_superuser(
        email="admin-campeonato-schema@example.com",
        password="PruebaSegura123!",
        nombre="Ada",
        apellido="Admin",
    )
    deporte = Deporte.objects.create(nombre="Natación")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Mayores")
    client = APIClient()
    client.force_authenticate(admin)
    datos = {
        "nombre": "Torneo de Natación",
        "categoria": categoria.pk,
        "formato": Campeonato.Formato.ELIMINACION,
        "estado": Campeonato.Estado.PLANIFICACION,
        "fecha_inicio": date(2026, 8, 1).isoformat(),
        "fecha_fin": date(2026, 8, 30).isoformat(),
        "max_equipos": 8,
        "min_jugadores": 2,
        "max_jugadores": 12,
        "puntos_victoria": 3,
        "puntos_empate": 1,
        "puntos_derrota": 0,
    }

    respuesta = client.post(reverse("campeonato-list"), datos, format="json")

    assert respuesta.status_code == 201
    campeonato = Campeonato.objects.get(pk=respuesta.data["id"])
    assert not hasattr(campeonato, "deporte_id")
    assert respuesta.data["deporte"] == deporte.pk
    assert respuesta.data["deporte_detalle"]["id"] == deporte.pk
    assert campeonato.puntos_victoria == 3

    datos["nombre"] = "Torneo inválido"
    datos["min_jugadores"] = 13
    datos["max_jugadores"] = 12
    respuesta_invalida = client.post(
        reverse("campeonato-list"),
        datos,
        format="json",
    )
    assert respuesta_invalida.status_code == 400
    assert Campeonato.objects.count() == 1
