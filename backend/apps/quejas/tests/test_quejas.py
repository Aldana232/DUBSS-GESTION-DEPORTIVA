from datetime import date

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.deportes.models import (
    Campeonato,
    Categoria,
    Deporte,
    Equipo,
    Facultad,
    Inscripcion,
)
from apps.fixture.models import Partido
from apps.quejas.models import Queja
from apps.users.models import Usuario


@pytest.fixture
def escenario_queja():
    facultad = Facultad.objects.create(nombre="Ingeniería quejas", sigla="INGQ")
    otra_facultad = Facultad.objects.create(nombre="Medicina quejas", sigla="MEDQ")
    facultad_ajena = Facultad.objects.create(nombre="Derecho quejas", sigla="DERQ")
    deporte = Deporte.objects.create(nombre="Futsal quejas")
    categoria = Categoria.objects.create(deporte=deporte, nombre="Primera quejas")
    admin = Usuario.objects.create_superuser(
        email="admin-quejas@example.com",
        password="PruebaSegura123!",
        nombre="Ada",
        apellido="Admin",
    )
    campeonato = Campeonato.objects.create(
        nombre="Campeonato quejas",
        categoria=categoria,
        estado=Campeonato.Estado.EN_CURSO,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
    )
    equipo_local = Equipo.objects.create(nombre="Local quejas", facultad=facultad)
    equipo_visitante = Equipo.objects.create(
        nombre="Visitante quejas",
        facultad=otra_facultad,
    )
    for equipo in (equipo_local, equipo_visitante):
        Inscripcion.objects.create(
            campeonato=campeonato,
            equipo=equipo,
            estado=Inscripcion.Estado.APROBADA,
        )
    partido = Partido.objects.create(
        campeonato=campeonato,
        equipo_local=equipo_local,
        equipo_visitante=equipo_visitante,
        fecha_hora="2026-06-01T10:00:00Z",
    )
    delegado = Usuario.objects.create_user(
        email="delegado-quejas@example.com",
        password="PruebaSegura123!",
        nombre="Diego",
        apellido="Delegado",
        rol=Usuario.Rol.DELEGADO,
        facultad=facultad,
    )
    delegado_ajeno = Usuario.objects.create_user(
        email="otro-delegado-quejas@example.com",
        password="PruebaSegura123!",
        nombre="Marta",
        apellido="Delegada",
        rol=Usuario.Rol.DELEGADO,
        facultad=facultad_ajena,
    )
    organizador = Usuario.objects.create_user(
        email="organizador-quejas@example.com",
        password="PruebaSegura123!",
        nombre="Olga",
        apellido="Organizadora",
        rol=Usuario.Rol.ORGANIZADOR,
    )
    return partido, delegado, delegado_ajeno, admin, organizador


@pytest.mark.django_db
def test_delegado_crea_queja_solo_sobre_su_facultad(escenario_queja):
    partido, delegado, otro_delegado, _, _ = escenario_queja
    client = APIClient()
    client.force_authenticate(delegado)

    respuesta = client.post(
        reverse("queja-list"),
        {
            "tipo": Queja.Tipo.QUEJA,
            "descripcion": "El equipo rival incumplió el reglamento.",
            "encuentro": partido.pk,
        },
        format="json",
    )
    assert respuesta.status_code == 201
    queja = Queja.objects.get(pk=respuesta.data["id"])
    assert queja.estado == Queja.Estado.ABIERTA
    assert queja.delegado == delegado

    client.force_authenticate(otro_delegado)
    respuesta_ajena = client.post(
        reverse("queja-list"),
        {
            "tipo": Queja.Tipo.APELACION,
            "descripcion": "Apelación del resultado.",
            "encuentro": partido.pk,
        },
        format="json",
    )
    assert respuesta_ajena.status_code == 400
    assert Queja.objects.count() == 1


@pytest.mark.django_db
def test_quejas_tienen_acceso_por_rol_y_resolucion_auditada(escenario_queja):
    partido, delegado, _, admin, organizador = escenario_queja
    queja = Queja.objects.create(
        tipo=Queja.Tipo.APELACION,
        descripcion="Solicito revisar el acta.",
        delegado=delegado,
        encuentro=partido,
    )
    client = APIClient()

    respuesta_anonima = client.get(reverse("queja-list"))
    assert respuesta_anonima.status_code == 401

    jugador = Usuario.objects.create_user(
        email="jugador-quejas@example.com",
        password="PruebaSegura123!",
        nombre="Jorge",
        apellido="Jugador",
        rol=Usuario.Rol.JUGADOR,
    )
    client.force_authenticate(jugador)
    assert client.get(reverse("queja-list")).status_code == 403

    client.force_authenticate(delegado)
    assert client.get(reverse("queja-list")).data["count"] == 1

    client.force_authenticate(organizador)
    respuesta = client.post(
        reverse("queja-resolver", kwargs={"pk": queja.pk}),
        {
            "estado": Queja.Estado.RESUELTA,
            "resolucion": "Se revisó el acta y se confirma el resultado.",
        },
        format="json",
    )
    queja.refresh_from_db()
    assert respuesta.status_code == 200
    assert queja.estado == Queja.Estado.RESUELTA
    assert queja.admin_resuelve == organizador
    assert queja.resuelta_en is not None

    client.force_authenticate(admin)
    assert client.get(reverse("queja-list")).data["count"] == 1


@pytest.mark.django_db
def test_delegado_solo_consulta_sus_quejas(escenario_queja):
    partido, delegado, delegado_ajeno, _, organizador = escenario_queja
    propia = Queja.objects.create(
        tipo=Queja.Tipo.QUEJA,
        descripcion="Queja propia.",
        delegado=delegado,
        encuentro=partido,
    )
    ajena = Queja.objects.create(
        tipo=Queja.Tipo.APELACION,
        descripcion="Queja de otra facultad.",
        delegado=delegado_ajeno,
        encuentro=partido,
    )
    client = APIClient()

    client.force_authenticate(delegado)
    respuesta = client.get(reverse("queja-list"))
    assert respuesta.status_code == 200
    assert respuesta.data["count"] == 1
    assert respuesta.data["results"][0]["id"] == propia.pk
    assert client.get(reverse("mis-quejas")).data["results"][0]["id"] == propia.pk
    assert client.get(
        reverse("queja-detail", kwargs={"pk": ajena.pk})
    ).status_code == 404

    client.force_authenticate(organizador)
    assert client.get(reverse("queja-list")).data["count"] == 2


@pytest.mark.django_db
def test_queja_unica_por_encuentro_y_tipo(escenario_queja):
    partido, delegado, _, _, _ = escenario_queja
    Queja.objects.create(
        tipo=Queja.Tipo.QUEJA,
        descripcion="Primera queja.",
        delegado=delegado,
        encuentro=partido,
    )
    client = APIClient()
    client.force_authenticate(delegado)

    respuesta = client.post(
        reverse("queja-list"),
        {
            "tipo": Queja.Tipo.QUEJA,
            "descripcion": "Queja duplicada.",
            "encuentro": partido.pk,
        },
        format="json",
    )

    assert respuesta.status_code == 400
    assert Queja.objects.count() == 1
