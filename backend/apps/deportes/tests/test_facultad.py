import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.deportes.models import Facultad
from apps.users.models import Usuario


@pytest.mark.django_db
def test_facultad_solo_se_lista_para_organizador_o_admin_y_admin_puede_crearla():
    Facultad.objects.create(nombre="Ingeniería", sigla="ING")
    client = APIClient()

    respuesta_anonima = client.get(reverse("facultad-list"))
    assert respuesta_anonima.status_code == 401

    organizador = Usuario.objects.create_user(
        email="organizador-facultad@example.com",
        password="PruebaSegura123!",
        nombre="Olga",
        apellido="Organizadora",
        rol=Usuario.Rol.ORGANIZADOR,
    )
    client.force_authenticate(organizador)
    respuesta_organizador_lectura = client.get(reverse("facultad-list"))
    assert respuesta_organizador_lectura.status_code == 200
    assert respuesta_organizador_lectura.data["results"][0]["sigla"] == "ING"
    respuesta_organizador = client.post(
        reverse("facultad-list"),
        {"nombre": "Medicina", "sigla": "MED"},
        format="json",
    )
    assert respuesta_organizador.status_code == 403

    admin = Usuario.objects.create_superuser(
        email="admin-facultad@example.com",
        password="PruebaSegura123!",
        nombre="Ada",
        apellido="Admin",
    )
    client.force_authenticate(admin)
    respuesta_admin = client.post(
        reverse("facultad-list"),
        {"nombre": "Medicina", "sigla": "MED"},
        format="json",
    )
    assert respuesta_admin.status_code == 201
    assert Facultad.objects.filter(sigla="MED").exists()


@pytest.mark.django_db
def test_alta_de_delegado_exige_facultad():
    admin = Usuario.objects.create_superuser(
        email="admin-delegado@example.com",
        password="PruebaSegura123!",
        nombre="Ada",
        apellido="Admin",
    )
    client = APIClient()
    client.force_authenticate(admin)
    datos = {
        "email": "delegado-sin-facultad@example.com",
        "nombre": "Diego",
        "apellido": "Delegado",
        "rol": Usuario.Rol.DELEGADO,
        "password": "PruebaSegura123!",
        "password2": "PruebaSegura123!",
    }

    respuesta = client.post(reverse("auth-registro"), datos, format="json")

    assert respuesta.status_code == 400
    assert "facultad" in respuesta.data
    assert not Usuario.objects.filter(email=datos["email"]).exists()

    facultad = Facultad.objects.create(nombre="Ciencias", sigla="CIE")
    datos["email"] = "delegado-con-facultad@example.com"
    datos["facultad"] = facultad.pk
    respuesta = client.post(reverse("auth-registro"), datos, format="json")

    assert respuesta.status_code == 201
    assert Usuario.objects.get(email=datos["email"]).facultad == facultad
