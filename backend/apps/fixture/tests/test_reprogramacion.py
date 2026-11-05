"""F3-09 — Programación manual y reprogramación con detección de conflictos."""
from datetime import datetime, timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.auditoria.models import Bitacora
from apps.deportes.models import Inscripcion, RestriccionHorarioFacultad
from apps.fixture.models import Partido
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.instalaciones.models import BloqueoCancha, HorarioCancha
from apps.users.models import Usuario

from .helpers import (
    cliente_de, crear_equipo, crear_escenario, crear_usuario,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def mundo():
    esc = crear_escenario(equipos=4, canchas=2)
    esc.partidos = list(FixtureGenerator(esc.campeonato.pk).generar())
    esc.partido = esc.partidos[0]
    return esc


def hora(esc, dias=30, h=15, m=0):
    """Una fecha lejana, libre y dentro del horario 08:00-22:00."""
    dia = esc.campeonato.fecha_inicio + timedelta(days=dias)
    return timezone.make_aware(datetime(dia.year, dia.month, dia.day, h, m))


def mover(client, partido, **cambios):
    return client.patch(
        reverse("partido-detail", kwargs={"pk": partido.pk}), cambios, format="json"
    )


def conflictos(respuesta):
    return " ".join(respuesta.data["conflictos"])


def test_mover_a_un_horario_libre_actualiza_registra_y_notifica(mundo):
    esc = mundo
    anterior = esc.partido.fecha_hora
    nueva = hora(esc)

    respuesta = mover(esc.client, esc.partido, fecha_hora=nueva.isoformat())

    assert respuesta.status_code == 200
    esc.partido.refresh_from_db()
    assert esc.partido.fecha_hora == nueva
    assert esc.partido.fecha_hora_fin == nueva + timedelta(minutes=90)
    registro = Bitacora.objects.filter(modulo="partido", objeto_id=esc.partido.pk).latest("pk")
    assert registro.descripcion == "Partido reprogramado."
    assert registro.detalle["anterior"]["fecha_hora"] == timezone.localtime(anterior).isoformat()
    assert registro.detalle["nuevo"]["fecha_hora"] == timezone.localtime(nueva).isoformat()
    destinatarios = {a for m in mail.outbox for a in m.to}
    assert destinatarios == {
        esc.partido.equipo_local.delegado.email, esc.partido.equipo_visitante.delegado.email,
    }
    assert "reprogramado" in mail.outbox[0].subject.lower()


def test_mover_a_una_cancha_ocupada_devuelve_409_con_detalle(mundo):
    esc = mundo
    p1, p2 = [p for p in esc.partidos if p.jornada == 1][:2]
    assert p1.cancha_id != p2.cancha_id and p1.fecha_hora == p2.fecha_hora

    respuesta = mover(esc.client, p1, cancha=p2.cancha_id)

    assert respuesta.status_code == 409
    assert "ya está ocupada" in conflictos(respuesta)
    assert respuesta.data["conflictos"]
    assert "No se puede programar el partido" in respuesta.data["detail"]
    p1.refresh_from_db()
    assert p1.cancha_id != p2.cancha_id  # no se movió
    assert len(mail.outbox) == 0


def test_conflicto_con_partido_de_otro_campeonato(mundo):
    esc = mundo
    otro = crear_escenario(equipos=2, canchas=0, deporte=esc.deporte)
    destino = esc.partidos[0]
    ocupante = Partido.objects.create(
        campeonato=otro.campeonato, equipo_local=otro.equipos[0],
        equipo_visitante=otro.equipos[1], cancha=esc.canchas[0],
        fecha_hora=hora(esc, 40),
    )

    respuesta = mover(esc.client, destino, fecha_hora=ocupante.fecha_hora.isoformat(),
                      cancha=esc.canchas[0].pk)

    assert respuesta.status_code == 409
    assert otro.campeonato.nombre in conflictos(respuesta)


def test_conflicto_con_un_bloqueo_de_mantenimiento(mundo):
    esc = mundo
    nueva = hora(esc, 25)
    BloqueoCancha.objects.create(
        cancha=esc.canchas[0], fecha_inicio=nueva - timedelta(hours=1),
        fecha_fin=nueva + timedelta(hours=1), tipo=BloqueoCancha.Tipo.MANTENIMIENTO,
        motivo="Riego",
    )

    respuesta = mover(esc.client, esc.partido, fecha_hora=nueva.isoformat(),
                      cancha=esc.canchas[0].pk)

    assert respuesta.status_code == 409
    assert "bloqueada" in conflictos(respuesta) and "Riego" in conflictos(respuesta)


def test_conflicto_fuera_de_la_franja_habilitada(mundo):
    esc = mundo

    respuesta = mover(esc.client, esc.partido, fecha_hora=hora(esc, 20, h=23).isoformat())

    assert respuesta.status_code == 409
    assert "franja horaria" in conflictos(respuesta) or "medianoche" in conflictos(respuesta)


def test_conflicto_si_el_partido_cruza_la_medianoche(mundo):
    esc = mundo
    HorarioCancha.objects.filter(cancha__in=esc.canchas).update(hora_fin="23:59")

    respuesta = mover(esc.client, esc.partido, fecha_hora=hora(esc, 20, h=23, m=0).isoformat())

    assert respuesta.status_code == 409
    assert "medianoche" in conflictos(respuesta)


def test_conflicto_si_un_equipo_ya_juega_a_esa_hora_en_otra_cancha(mundo):
    esc = mundo
    p1 = esc.partidos[0]
    otro_de_los_mismos = next(
        p for p in esc.partidos
        if p.pk != p1.pk and {p.equipo_local_id, p.equipo_visitante_id} & {
            p1.equipo_local_id, p1.equipo_visitante_id}
    )
    cancha_libre = next(c for c in esc.canchas if c.pk != otro_de_los_mismos.cancha_id)

    respuesta = mover(esc.client, p1, fecha_hora=otro_de_los_mismos.fecha_hora.isoformat(),
                      cancha=cancha_libre.pk)

    assert respuesta.status_code == 409
    assert "ya juega" in conflictos(respuesta)


def test_conflicto_con_restriccion_horaria_de_la_facultad(mundo):
    esc = mundo
    nueva = hora(esc, 35, h=10)
    RestriccionHorarioFacultad.objects.create(
        facultad=esc.partido.equipo_local.facultad, dia_semana=nueva.weekday(),
        hora_inicio="09:00", hora_fin="12:00", motivo="Exámenes",
    )

    respuesta = mover(esc.client, esc.partido, fecha_hora=nueva.isoformat())

    assert respuesta.status_code == 409
    assert "restricción horaria" in conflictos(respuesta)


def test_se_reportan_todos_los_conflictos_a_la_vez(mundo):
    esc = mundo
    p1, p2 = [p for p in esc.partidos if p.jornada == 1][:2]
    BloqueoCancha.objects.create(
        cancha=p2.cancha, fecha_inicio=p2.fecha_hora - timedelta(minutes=10),
        fecha_fin=p2.fecha_hora + timedelta(minutes=10), motivo="Evento",
        tipo=BloqueoCancha.Tipo.EVENTO,
    )

    respuesta = mover(esc.client, p1, cancha=p2.cancha_id)

    assert respuesta.status_code == 409
    assert len(respuesta.data["conflictos"]) >= 2


def test_el_partido_no_choca_consigo_mismo(mundo):
    esc = mundo

    respuesta = mover(esc.client, esc.partido, fecha_hora=esc.partido.fecha_hora.isoformat(),
                      duracion_min=60)

    assert respuesta.status_code == 200
    esc.partido.refresh_from_db()
    assert esc.partido.duracion_min == 60


def test_editar_solo_observaciones_no_valida_horario_ni_notifica(mundo):
    esc = mundo

    respuesta = mover(esc.client, esc.partido, observaciones="Llevar balón oficial")

    assert respuesta.status_code == 200
    assert len(mail.outbox) == 0


def test_no_se_edita_un_partido_con_resultado(mundo):
    esc = mundo
    esc.client.post(
        reverse("partido-registrar-resultado", kwargs={"pk": esc.partido.pk}),
        {"goles_local": 1, "goles_visitante": 0}, format="json",
    )

    respuesta = mover(esc.client, esc.partido, fecha_hora=hora(esc).isoformat())

    assert respuesta.status_code == 400
    assert "corrige el resultado" in str(respuesta.data)


def test_no_se_cambian_equipos_ni_campeonato_ni_se_finaliza_por_patch(mundo):
    esc = mundo
    ajeno = crear_equipo("Ajeno", esc.campeonato)

    cambio_equipo = mover(esc.client, esc.partido, equipo_local=ajeno.pk)
    finalizar = mover(esc.client, esc.partido, estado="FINALIZADO")
    suspender = mover(esc.client, esc.partido, estado="SUSPENDIDO")

    assert cambio_equipo.status_code == 400 and "equipo_local" in cambio_equipo.data
    assert finalizar.status_code == 400 and "estado" in finalizar.data
    assert suspender.status_code == 200


def test_delegado_y_anonimo_no_reprograman(mundo):
    esc = mundo
    delegado = cliente_de(crear_usuario(Usuario.Rol.DELEGADO, esc.partido.equipo_local.facultad))
    cuerpo = {"fecha_hora": hora(esc).isoformat()}
    url = reverse("partido-detail", kwargs={"pk": esc.partido.pk})

    assert delegado.patch(url, cuerpo, format="json").status_code == 403
    from rest_framework.test import APIClient
    assert APIClient().patch(url, cuerpo, format="json").status_code == 401
    assert esc.client_org.patch(url, cuerpo, format="json").status_code == 200


# ── Alta manual ───────────────────────────────────────────────────────────────

def cuerpo_manual(esc, **extra):
    return {
        "campeonato": esc.campeonato.pk,
        "equipo_local": esc.equipos[0].pk,
        "equipo_visitante": esc.equipos[1].pk,
        "cancha": esc.canchas[0].pk,
        "fecha_hora": hora(esc, 50).isoformat(),
        "jornada": 20,
        **extra,
    }


def crear_manual(esc, **extra):
    return esc.client.post(reverse("partido-list"), cuerpo_manual(esc, **extra), format="json")


def test_alta_manual_valida(mundo):
    respuesta = crear_manual(mundo)

    assert respuesta.status_code == 201
    partido = Partido.objects.get(pk=respuesta.data["id"])
    assert partido.instalacion == mundo.canchas[0].instalacion
    assert partido.generado_por_ml is False
    assert Bitacora.objects.filter(accion=Bitacora.Accion.CREAR, modulo="partido").exists()


def test_alta_manual_exige_inscripcion_aprobada(mundo):
    esc = mundo
    sin_aprobar = crear_equipo("Sin aprobar", esc.campeonato, Inscripcion.Estado.PENDIENTE)

    respuesta = crear_manual(esc, equipo_visitante=sin_aprobar.pk)

    assert respuesta.status_code == 400
    assert "no tiene inscripción aprobada" in str(respuesta.data)


def test_alta_manual_rechaza_mismo_equipo_y_falta_de_equipos(mundo):
    esc = mundo

    mismo = crear_manual(esc, equipo_visitante=esc.equipos[0].pk)
    sin_visitante = crear_manual(esc, equipo_visitante=None)

    assert mismo.status_code == 400
    assert sin_visitante.status_code == 400


def test_alta_manual_con_cancha_ocupada_devuelve_409(mundo):
    esc = mundo
    primera = crear_manual(esc)
    assert primera.status_code == 201

    repetida = crear_manual(esc, equipo_local=esc.equipos[2].pk,
                            equipo_visitante=esc.equipos[3].pk, jornada=21)

    assert repetida.status_code == 409
    assert "ya está ocupada" in conflictos(repetida)


def test_alta_manual_en_campeonato_cerrado(mundo):
    esc = mundo
    esc.campeonato.estado = "CANCELADO"
    esc.campeonato.save(update_fields=["estado"])

    assert crear_manual(esc).status_code == 400
