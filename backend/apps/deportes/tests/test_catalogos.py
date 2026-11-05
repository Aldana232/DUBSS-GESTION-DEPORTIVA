import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.deportes.models import Categoria, Deporte
from apps.users.models import Usuario


@pytest.mark.django_db
def test_deporte_categoria_exponen_campos_alineados_al_documento():
    admin = Usuario.objects.create_superuser(
        email="admin-catalogos@example.com",
        password="PruebaSegura123!",
        nombre="Ada",
        apellido="Admin",
    )
    client = APIClient()
    client.force_authenticate(admin)

    respuesta_deporte = client.post(
        reverse("deporte-list"),
        {
            "nombre": "Voleibol",
            "descripcion": "Deporte de prueba",
            "cantidad_jugadores": 6,
            "activo": True,
        },
        format="json",
    )
    assert respuesta_deporte.status_code == 201
    deporte = Deporte.objects.get(pk=respuesta_deporte.data["id"])
    assert deporte.cantidad_jugadores == 6

    respuesta_categoria = client.post(
        reverse("categoria-list"),
        {
            "deporte": deporte.pk,
            "nombre": "Mayores",
            "genero": Categoria.Genero.MIXTO,
            "rango_edad": "18-35",
            "descripcion": "",
            "activa": True,
        },
        format="json",
    )
    assert respuesta_categoria.status_code == 201
    assert respuesta_categoria.data["rango_edad"] == "18-35"
    assert "edad_min" not in respuesta_categoria.data
    assert "edad_max" not in respuesta_categoria.data


@pytest.mark.django_db
def test_categoria_mantiene_unicidad_por_deporte_nombre_y_genero():
    deporte = Deporte.objects.create(nombre="Básquet")
    Categoria.objects.create(
        deporte=deporte,
        nombre="Mayores",
        genero=Categoria.Genero.VARONES,
        rango_edad="18+",
    )
    client = APIClient()
    admin = Usuario.objects.create_superuser(
        email="admin-categoria-unica@example.com",
        password="PruebaSegura123!",
        nombre="Ada",
        apellido="Admin",
    )
    client.force_authenticate(admin)

    respuesta = client.post(
        reverse("categoria-list"),
        {
            "deporte": deporte.pk,
            "nombre": "Mayores",
            "genero": Categoria.Genero.VARONES,
            "rango_edad": "18+",
        },
        format="json",
    )

    assert respuesta.status_code == 400
    assert Categoria.objects.count() == 1
