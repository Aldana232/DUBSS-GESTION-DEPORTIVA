"""F3-02 — Flujo de inscripciones (RF6/RF8): solicitud, elegibilidad y validación."""
from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato, Inscripcion
from apps.deportes.services import evaluar_inscripcion
from apps.fixture.models import Partido
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.fixture.tests.helpers import (
    cliente_de, crear_campeonato, crear_canchas, crear_equipo, crear_jugador,
    crear_usuario,
)
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
E = Inscripcion.Estado


@pytest.fixture
def mundo():
    campeonato = crear_campeonato(min_jugadores=2, max_jugadores=3, max_equipos=3)
    equipo = crear_equipo("Ingeniería A", jugadores=2)
    return {
        "campeonato": campeonato,
        "equipo": equipo,
        "delegado": equipo.delegado,
        "admin": crear_usuario(Usuario.Rol.ADMIN_DUBSS, prefijo="admin"),
        "organizador": crear_usuario(Usuario.Rol.ORGANIZADOR, prefijo="org"),
    }


def solicitar(client, campeonato, equipo):
    return client.post(
        reverse("inscripcion-list"),
        {"campeonato": campeonato.pk, "equipo": equipo.pk},
        format="json",
    )


def validar(client, inscripcion, estado, **extra):
    return client.patch(
        reverse("inscripcion-validar", kwargs={"pk": inscripcion.pk}),
        {"estado": estado, **extra},
        format="json",
    )


def test_flujo_completo_solicitud_aprobacion_y_fixture(mundo):
    campeonato = mundo["campeonato"]
    canchas = crear_canchas(campeonato.categoria.deporte, 1)
    otro = crear_equipo("Medicina B", jugadores=2)
    pendiente = crear_equipo("Derecho C", jugadores=2)

    # 1. Los delegados solicitan.
    r1 = solicitar(cliente_de(mundo["delegado"]), campeonato, mundo["equipo"])
    r2 = solicitar(cliente_de(otro.delegado), campeonato, otro)
    r3 = solicitar(cliente_de(pendiente.delegado), campeonato, pendiente)
    assert (r1.status_code, r2.status_code, r3.status_code) == (201, 201, 201)
    assert r1.data["estado"] == E.PENDIENTE

    # 2. El organizador revisa la elegibilidad y aprueba dos.
    admin = cliente_de(mundo["organizador"])
    primera = Inscripcion.objects.get(equipo=mundo["equipo"])
    segunda = Inscripcion.objects.get(equipo=otro)
    revision = admin.get(reverse("inscripcion-elegibilidad", kwargs={"pk": primera.pk}))
    assert revision.status_code == 200 and revision.data["aprobable"] is True
    assert validar(admin, primera, E.APROBADA).status_code == 200
    assert validar(admin, segunda, E.APROBADA, observaciones="Todo en orden").status_code == 200

    # 3. Solo las aprobadas entran al fixture.
    # El organizador cierra las inscripciones y recién entonces genera el fixture.
    cierre = admin.patch(
        reverse("campeonato-cambiar-estado", kwargs={"pk": campeonato.pk}),
        {"estado": Campeonato.Estado.INSCRIPCION_CERRADA}, format="json",
    )
    assert cierre.status_code == 200
    partidos = FixtureGenerator(campeonato.pk).generar()
    assert len(partidos) == 1
    assert {partidos[0].equipo_local, partidos[0].equipo_visitante} == {mundo["equipo"], otro}
    assert Partido.objects.filter(
        equipo_local=pendiente
    ).count() + Partido.objects.filter(equipo_visitante=pendiente).count() == 0
    assert canchas  # la cancha existe


def test_el_delegado_no_puede_validar_inscripciones(mundo):
    inscripcion = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=mundo["equipo"])

    respuesta = validar(cliente_de(mundo["delegado"]), inscripcion, E.APROBADA)

    assert respuesta.status_code == 403
    inscripcion.refresh_from_db()
    assert inscripcion.estado == E.PENDIENTE


def test_el_delegado_ve_la_elegibilidad_solo_de_su_facultad(mundo):
    propia = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=mundo["equipo"])
    ajena = Inscripcion.objects.create(
        campeonato=mundo["campeonato"], equipo=crear_equipo("Ajeno elegibilidad", jugadores=2)
    )
    cliente = cliente_de(mundo["delegado"])

    suya = cliente.get(reverse("inscripcion-elegibilidad", kwargs={"pk": propia.pk}))
    otra = cliente.get(reverse("inscripcion-elegibilidad", kwargs={"pk": ajena.pk}))

    assert suya.status_code == 200 and suya.data["aprobable"] is True
    assert otra.status_code == 404


def test_aprobar_registra_validador_fecha_bitacora_y_notifica_al_delegado(mundo):
    inscripcion = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=mundo["equipo"])

    respuesta = validar(cliente_de(mundo["admin"]), inscripcion, E.APROBADA, observaciones="Ok")

    assert respuesta.status_code == 200
    inscripcion.refresh_from_db()
    assert inscripcion.validado_por == mundo["admin"]
    assert inscripcion.fecha_validacion is not None
    assert Bitacora.objects.filter(
        modulo="inscripcion", objeto_id=inscripcion.pk, resultado=Bitacora.Resultado.OK
    ).exists()
    assert len(mail.outbox) == 1
    assert mundo["delegado"].email in mail.outbox[0].to
    assert "aprobada" in mail.outbox[0].subject


def test_rechazar_exige_observacion(mundo):
    inscripcion = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=mundo["equipo"])
    admin = cliente_de(mundo["admin"])

    sin_motivo = validar(admin, inscripcion, E.RECHAZADA)
    con_motivo = validar(admin, inscripcion, E.RECHAZADA, observaciones="Documentos incompletos")

    assert sin_motivo.status_code == 400 and "observaciones" in sin_motivo.data
    assert con_motivo.status_code == 200
    inscripcion.refresh_from_db()
    assert inscripcion.estado == E.RECHAZADA
    assert inscripcion.observaciones == "Documentos incompletos"


def test_solo_se_validan_inscripciones_pendientes(mundo):
    inscripcion = Inscripcion.objects.create(
        campeonato=mundo["campeonato"], equipo=mundo["equipo"], estado=E.APROBADA
    )

    respuesta = validar(cliente_de(mundo["admin"]), inscripcion, E.RECHAZADA, observaciones="x")

    assert respuesta.status_code == 400


def test_estado_de_validacion_invalido(mundo):
    inscripcion = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=mundo["equipo"])

    respuesta = validar(cliente_de(mundo["admin"]), inscripcion, "PENDIENTE")

    assert respuesta.status_code == 400


# ── Elegibilidad: motivos de rechazo ─────────────────────────────────────────

def test_no_aprueba_equipo_bajo_el_minimo_de_jugadores(mundo):
    corto = crear_equipo("Equipo corto", jugadores=1)
    inscripcion = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=corto)

    respuesta = validar(cliente_de(mundo["admin"]), inscripcion, E.APROBADA)

    assert respuesta.status_code == 400
    assert any("mínimo de 2" in m for m in respuesta.data["motivos"])
    inscripcion.refresh_from_db()
    assert inscripcion.estado == E.PENDIENTE
    registro = Bitacora.objects.get(modulo="inscripcion", resultado=Bitacora.Resultado.ERROR)
    assert registro.detalle["motivos"]


def test_no_aprueba_equipo_sobre_el_maximo_de_jugadores(mundo):
    grande = crear_equipo("Equipo grande", jugadores=4)
    inscripcion = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=grande)

    respuesta = validar(cliente_de(mundo["admin"]), inscripcion, E.APROBADA)

    assert respuesta.status_code == 400
    assert any("máximo de 3" in m for m in respuesta.data["motivos"])


def test_no_aprueba_si_un_jugador_ya_esta_en_otro_equipo_del_campeonato(mundo):
    rival = crear_equipo("Rival", jugadores=2)
    ficha = rival.jugadores.first()
    crear_jugador(mundo["equipo"], 9, carnet=ficha.carnet)  # el mismo carnet
    Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=rival, estado=E.APROBADA)
    inscripcion = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=mundo["equipo"])

    respuesta = validar(cliente_de(mundo["admin"]), inscripcion, E.APROBADA)

    assert respuesta.status_code == 400
    assert any("ya está inscrito en otro equipo" in m for m in respuesta.data["motivos"])


def test_no_aprueba_si_el_campeonato_ya_alcanzo_el_maximo_de_equipos(mundo):
    campeonato = mundo["campeonato"]  # max_equipos=3
    for i in range(3):
        crear_equipo(f"Aprobado {i}", campeonato, jugadores=2)
    inscripcion = Inscripcion.objects.create(campeonato=campeonato, equipo=mundo["equipo"])

    respuesta = validar(cliente_de(mundo["admin"]), inscripcion, E.APROBADA)

    assert respuesta.status_code == 400
    assert any("máximo de 3 equipos" in m for m in respuesta.data["motivos"])


def test_un_jugador_sancionado_es_advertencia_no_bloqueo(mundo):
    ficha = mundo["equipo"].jugadores.first()
    ficha.partidos_sancion_restantes = 2
    ficha.save()
    inscripcion = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=mundo["equipo"])

    evaluacion = evaluar_inscripcion(inscripcion)
    respuesta = validar(cliente_de(mundo["admin"]), inscripcion, E.APROBADA)

    assert evaluacion["bloqueantes"] == []
    assert any("sanción" in a for a in evaluacion["advertencias"])
    assert respuesta.status_code == 200
    assert any("sanción" in a for a in respuesta.data["advertencias"])


def test_la_aprobacion_no_se_bloquea_por_plazo_vencido_si_se_solicito_a_tiempo(mundo):
    campeonato = mundo["campeonato"]
    inscripcion = Inscripcion.objects.create(campeonato=campeonato, equipo=mundo["equipo"])
    Campeonato.objects.filter(pk=campeonato.pk).update(
        fecha_cierre_inscripcion=timezone.now() - timedelta(days=1)
    )

    respuesta = validar(cliente_de(mundo["admin"]), inscripcion, E.APROBADA)

    assert respuesta.status_code == 200


# ── Solicitud ─────────────────────────────────────────────────────────────────

def test_no_se_solicita_con_inscripcion_cerrada_por_plazo(mundo):
    campeonato = mundo["campeonato"]
    Campeonato.objects.filter(pk=campeonato.pk).update(
        fecha_cierre_inscripcion=timezone.now() - timedelta(minutes=1)
    )

    respuesta = solicitar(cliente_de(mundo["delegado"]), campeonato, mundo["equipo"])

    assert respuesta.status_code == 400
    assert "plazo de inscripción" in str(respuesta.data)


def test_no_se_solicita_si_el_campeonato_no_recibe_inscripciones(mundo):
    campeonato = mundo["campeonato"]
    Campeonato.objects.filter(pk=campeonato.pk).update(estado=Campeonato.Estado.EN_CURSO)

    respuesta = solicitar(cliente_de(mundo["delegado"]), campeonato, mundo["equipo"])

    assert respuesta.status_code == 400


def test_no_se_solicita_dos_veces_ni_con_equipo_ajeno(mundo):
    cliente = cliente_de(mundo["delegado"])
    assert solicitar(cliente, mundo["campeonato"], mundo["equipo"]).status_code == 201
    assert solicitar(cliente, mundo["campeonato"], mundo["equipo"]).status_code == 400

    ajeno = crear_equipo("De otra facultad", jugadores=2)
    assert solicitar(cliente, mundo["campeonato"], ajeno).status_code == 400


def test_el_delegado_solo_ve_las_inscripciones_de_su_facultad(mundo):
    ajeno = crear_equipo("Ajeno", jugadores=2)
    propia = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=mundo["equipo"])
    otra = Inscripcion.objects.create(campeonato=mundo["campeonato"], equipo=ajeno)
    cliente = cliente_de(mundo["delegado"])

    lista = cliente.get(reverse("inscripcion-list"))
    detalle_ajeno = cliente.get(reverse("inscripcion-detail", kwargs={"pk": otra.pk}))

    ids = [i["id"] for i in lista.data["results"]] if "results" in lista.data \
        else [i["id"] for i in lista.data]
    assert ids == [propia.pk]
    assert detalle_ajeno.status_code == 404


def test_no_se_aprueban_equipos_con_las_inscripciones_cerradas(mundo):
    campeonato = mundo["campeonato"]
    inscripcion = Inscripcion.objects.create(campeonato=campeonato, equipo=mundo["equipo"])
    Campeonato.objects.filter(pk=campeonato.pk).update(estado=Campeonato.Estado.INSCRIPCION_CERRADA)
    admin = cliente_de(mundo["admin"])

    aprobar = validar(admin, inscripcion, E.APROBADA)
    rechazar = validar(admin, inscripcion, E.RECHAZADA, observaciones="Fuera de plazo")

    assert aprobar.status_code == 400 and "no están abiertas" in str(aprobar.data)
    assert rechazar.status_code == 200  # rechazar sí se permite
