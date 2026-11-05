from datetime import date

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APIClient

from apps.deportes.models import (
    Campeonato, Categoria, Deporte, Equipo, Facultad, Inscripcion,
)
from apps.fixture.models import Partido
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.instalaciones.models import Cancha, HorarioCancha, Instalacion
from apps.users.models import Usuario


def crear_campeonato(nombre, admin=None, estado=Campeonato.Estado.INSCRIPCIONES):
    deporte = Deporte.objects.create(nombre=f"Deporte {nombre}")
    categoria = Categoria.objects.create(deporte=deporte, nombre=f"Categoria {nombre}")
    return Campeonato.objects.create(
        nombre=nombre,
        categoria=categoria,
        estado=estado,
        fecha_inicio=date(2026, 1, 1),
        fecha_fin=date(2026, 12, 31),
        creado_por=admin,
    )


@pytest.mark.django_db
def test_equipo_reutilizable_se_inscribe_en_dos_campeonatos():
    facultad = Facultad.objects.create(nombre="Ingeniería", sigla="ING")
    equipo = Equipo.objects.create(nombre="Tigres", facultad=facultad)
    campeonatos = [
        crear_campeonato("Primero"),
        crear_campeonato("Segundo"),
    ]

    inscripciones = [
        Inscripcion.objects.create(
            campeonato=campeonato,
            equipo=equipo,
            estado=Inscripcion.Estado.APROBADA,
        )
        for campeonato in campeonatos
    ]

    assert [inscripcion.equipo_id for inscripcion in inscripciones] == [
        equipo.pk,
        equipo.pk,
    ]


@pytest.mark.django_db
def test_equipo_no_se_duplica_con_mismo_nombre_y_facultad():
    facultad = Facultad.objects.create(nombre="Ingeniería", sigla="ING")
    Equipo.objects.create(nombre="Tigres", facultad=facultad)

    with pytest.raises(IntegrityError), transaction.atomic():
        Equipo.objects.create(nombre="Tigres", facultad=facultad)


@pytest.mark.django_db
def test_inscripcion_delegado_solo_de_su_facultad_y_validacion_admin():
    facultad = Facultad.objects.create(nombre="Ingeniería", sigla="ING")
    otra_facultad = Facultad.objects.create(nombre="Medicina", sigla="MED")
    delegado = Usuario.objects.create_user(
        email="delegado-inscripcion@example.com",
        password="PruebaSegura123!",
        nombre="Dalia",
        apellido="Delegada",
        rol=Usuario.Rol.DELEGADO,
        facultad=facultad,
    )
    admin = Usuario.objects.create_superuser(
        email="admin-inscripcion@example.com",
        password="PruebaSegura123!",
        nombre="Ada",
        apellido="Admin",
    )
    campeonato = crear_campeonato("Inscripción", admin)
    equipo_propio = Equipo.objects.create(nombre="Propio", facultad=facultad)
    equipo_ajeno = Equipo.objects.create(nombre="Ajeno", facultad=otra_facultad)
    client = APIClient()
    client.force_authenticate(delegado)

    respuesta_ajena = client.post(
        reverse("inscripcion-list"),
        {"campeonato": campeonato.pk, "equipo": equipo_ajeno.pk},
        format="json",
    )
    assert respuesta_ajena.status_code == 400
    assert Inscripcion.objects.count() == 0

    respuesta_propia = client.post(
        reverse("inscripcion-list"),
        {"campeonato": campeonato.pk, "equipo": equipo_propio.pk},
        format="json",
    )
    assert respuesta_propia.status_code == 201
    inscripcion = Inscripcion.objects.get(pk=respuesta_propia.data["id"])
    assert inscripcion.estado == Inscripcion.Estado.PENDIENTE

    client.force_authenticate(admin)
    respuesta_validacion = client.patch(
        reverse("inscripcion-validar", kwargs={"pk": inscripcion.pk}),
        {"estado": Inscripcion.Estado.APROBADA},
        format="json",
    )
    inscripcion.refresh_from_db()
    assert respuesta_validacion.status_code == 200
    assert inscripcion.estado == Inscripcion.Estado.APROBADA
    assert inscripcion.validado_por == admin
    assert inscripcion.fecha_validacion is not None


@pytest.mark.django_db
def test_fixture_usa_solo_inscripciones_aprobadas():
    campeonato = crear_campeonato("Fixture")
    facultad = Facultad.objects.create(nombre="Ingeniería", sigla="ING")
    equipos = [
        Equipo.objects.create(nombre=f"Equipo {numero}", facultad=facultad)
        for numero in range(1, 4)
    ]
    for equipo, estado in zip(
        equipos,
        [
            Inscripcion.Estado.APROBADA,
            Inscripcion.Estado.APROBADA,
            Inscripcion.Estado.PENDIENTE,
        ],
    ):
        Inscripcion.objects.create(campeonato=campeonato, equipo=equipo, estado=estado)
    instalacion = Instalacion.objects.create(
        nombre="Instalación fixture",
        ubicacion="Campus",
    )
    cancha = Cancha.objects.create(
        instalacion=instalacion,
        nombre="Cancha 1",
        deporte=campeonato.categoria.deporte,
    )
    HorarioCancha.objects.create(
        cancha=cancha,
        dia_semana=date(2026, 1, 1).weekday(),
        hora_inicio="08:00",
        hora_fin="17:00",
    )

    Campeonato.objects.filter(pk=campeonato.pk).update(estado=Campeonato.Estado.INSCRIPCION_CERRADA)
    partidos = FixtureGenerator(campeonato.pk).generar()

    assert len(partidos) == 1
    partido = Partido.objects.get(campeonato=campeonato)
    assert partido.equipo_local in equipos[:2]
    assert partido.equipo_visitante in equipos[:2]
    assert partido.equipo_local != partido.equipo_visitante
