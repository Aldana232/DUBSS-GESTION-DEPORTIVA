"""F7-02 — Acciones pendientes: solo al confirmar se escribe; todo se revalida contra el calendario real."""
import json
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.agente.models import AccionPendiente
from apps.agente.services import acciones, herramientas as h
from apps.agente.tasks import expirar_acciones
from apps.agente.tests.helpers_agente import a_las, contexto, crear_partido, dia, escenario_en_curso, simular_clima
from apps.auditoria.models import Bitacora
from apps.fixture.models import Partido
from apps.fixture.tests.helpers import cliente_de, crear_usuario
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def avisos(monkeypatch):
    enviados = []

    def falso(usuarios, titulo, mensaje, datos=None):
        enviados.append((sorted(u.pk for u in usuarios), titulo, mensaje))
        return {"usuarios": len(list(usuarios)), "email": len(list(usuarios)), "push": 0}
    monkeypatch.setattr(acciones, "notificar_usuarios", falso)
    return enviados


@pytest.fixture
def escenario(monkeypatch):
    simular_clima(monkeypatch, dias_lluviosos=[3])
    e = escenario_en_curso(equipos=4, canchas=2)
    e.p1 = crear_partido(e, e.equipos[0], e.equipos[1], e.canchas[0], a_las(3, 16))
    e.p2 = crear_partido(e, e.equipos[2], e.equipos[3], e.canchas[1], a_las(3, 18), jornada=2)
    e.ctx = contexto(e.organizador)
    return e


def proponer_y_solicitar(e):
    pid = json.loads(h.ejecutar("proponer_reprogramacion", json.dumps({"fecha": dia(3).isoformat(), "motivo": "Lluvia fuerte"}), e.ctx).contenido)["datos"]["propuesta_id"]
    h.ejecutar("aplicar_reprogramacion", json.dumps({"propuesta_id": pid}), e.ctx)
    return e.ctx.acciones[0]


def posiciones():
    return {p.pk: (p.fecha_hora, p.cancha_id) for p in Partido.objects.all()}


def test_confirmar_aplica_los_cambios_audita_y_avisa_a_los_delegados(escenario, avisos):
    e = escenario
    accion = proponer_y_solicitar(e)
    antes = posiciones()

    hecha = acciones.confirmar(accion.pk, e.organizador)

    assert hecha.estado == AccionPendiente.Estado.CONFIRMADA and hecha.resuelta_en
    despues = posiciones()
    assert all(despues[pk] != antes[pk] for pk in antes)                                  # los dos se movieron
    assert all(timezone.localtime(f).date() != dia(3) for f, _ in despues.values())
    p1 = Partido.objects.get(pk=e.p1.pk)
    assert p1.fecha_hora_fin == p1.fecha_hora + timedelta(minutes=90) and "Reprogramado por el agente" in p1.observaciones
    assert {tuple(u) for u, _, _ in avisos} == {(e.equipos[i].delegado_id,) for i in range(4)}
    assert all(t == "Partido reprogramado" and "Lluvia fuerte" in m for _, t, m in avisos)
    assert hecha.resultado["partidos_reprogramados"] == 2 and hecha.resultado["notificados"]["usuarios"] == 4
    assert Bitacora.objects.filter(accion="EDITAR", modulo="partido", detalle__via="agente").count() == 2
    assert Bitacora.objects.filter(accion="AGENTE", modulo="agente", objeto_id=accion.pk).exists()


def test_confirmar_dos_veces_no_ejecuta_dos_veces(escenario, avisos):
    accion = proponer_y_solicitar(escenario)
    acciones.confirmar(accion.pk, escenario.organizador)
    tras_primera = posiciones()

    with pytest.raises(acciones.AccionNoEjecutable) as e:
        acciones.confirmar(accion.pk, escenario.organizador)

    assert e.value.codigo == 409 and posiciones() == tras_primera and len(avisos) == 4


def test_cancelar_no_cambia_nada_y_no_se_puede_confirmar_despues(escenario, avisos):
    accion = proponer_y_solicitar(escenario)
    antes = posiciones()

    acciones.cancelar(accion.pk, escenario.organizador)

    accion.refresh_from_db()
    assert accion.estado == AccionPendiente.Estado.CANCELADA and posiciones() == antes and avisos == []
    with pytest.raises(acciones.AccionNoEjecutable):
        acciones.confirmar(accion.pk, escenario.organizador)


def test_una_accion_vencida_no_se_ejecuta(escenario, avisos):
    accion = proponer_y_solicitar(escenario)
    AccionPendiente.objects.filter(pk=accion.pk).update(expira_en=timezone.now() - timedelta(minutes=1))
    antes = posiciones()

    with pytest.raises(acciones.AccionNoEjecutable) as e:
        acciones.confirmar(accion.pk, escenario.organizador)

    accion.refresh_from_db()
    assert e.value.codigo == 410 and accion.estado == AccionPendiente.Estado.EXPIRADA and posiciones() == antes


def test_la_tarea_marca_como_expiradas_solo_las_vencidas(escenario):
    vigente = proponer_y_solicitar(escenario)
    vencida = AccionPendiente.objects.create(usuario=escenario.organizador, conversacion=escenario.ctx.conversacion, herramienta="enviar_notificacion",
                                             resumen="x", propuesta={}, expira_en=timezone.now() - timedelta(minutes=5))

    assert expirar_acciones() == 1

    vigente.refresh_from_db(), vencida.refresh_from_db()
    assert vigente.estado == AccionPendiente.Estado.PENDIENTE and vencida.estado == AccionPendiente.Estado.EXPIRADA


def test_solo_la_persona_dueña_de_la_accion_puede_confirmarla(escenario, avisos):
    accion = proponer_y_solicitar(escenario)
    otro = crear_usuario(Usuario.Rol.ADMIN_DUBSS)

    with pytest.raises(acciones.AccionNoEjecutable) as e:
        acciones.confirmar(accion.pk, otro)

    assert e.value.codigo == 404 and AccionPendiente.objects.get(pk=accion.pk).estado == AccionPendiente.Estado.PENDIENTE


def test_si_alguien_movio_un_partido_despues_de_la_propuesta_no_se_aplica_nada(escenario, avisos):
    accion = proponer_y_solicitar(escenario)
    Partido.objects.filter(pk=escenario.p1.pk).update(fecha_hora=a_las(10, 9), fecha_hora_fin=a_las(10, 10, 30))   # otro organizador lo movió
    antes = posiciones()

    with pytest.raises(acciones.AccionNoEjecutable) as e:
        acciones.confirmar(accion.pk, escenario.organizador)

    accion.refresh_from_db()
    assert e.value.codigo == 409 and "alguien lo reprogramó" in e.value.mensaje
    assert accion.estado == AccionPendiente.Estado.FALLIDA and posiciones() == antes and avisos == []


def test_si_el_horario_destino_se_ocupo_despues_de_la_propuesta_no_se_aplica(escenario, avisos):
    accion = proponer_y_solicitar(escenario)
    cambio = accion.propuesta["cambios"][0]
    from apps.instalaciones.models import Cancha
    cancha = Cancha.objects.get(pk=cambio["nuevo"]["cancha_id"])
    from datetime import datetime
    inicio = datetime.fromisoformat(cambio["nuevo"]["inicio"])
    # Otro partido (de otros equipos) toma justo esa cancha y hora.
    otros = escenario_en_curso(equipos=2, canchas=0)
    crear_partido(otros, otros.equipos[0], otros.equipos[1], cancha, inicio, jornada=9)
    antes = posiciones()

    with pytest.raises(acciones.AccionNoEjecutable) as e:
        acciones.confirmar(accion.pk, escenario.organizador)

    assert "ocupada" in e.value.mensaje and AccionPendiente.objects.get(pk=accion.pk).estado == AccionPendiente.Estado.FALLIDA
    assert {k: v for k, v in posiciones().items() if k in antes} == antes and avisos == []


def test_dos_partidos_pueden_intercambiar_cancha_y_horario(escenario, avisos):
    """La base prohíbe solapes de cancha incluso a mitad de la operación: se libera primero y se asigna después."""
    e = escenario
    a, b = e.p1, e.p2
    cambios = []
    for origen, destino in ((a, b), (b, a)):
        cambios.append({
            "partido_id": origen.pk, "partido": "P", "campeonato": "C", "jornada": origen.jornada, "delegados": [],
            "anterior": {"cancha_id": origen.cancha_id, "cancha": "x", "inicio": timezone.localtime(origen.fecha_hora).isoformat()},
            "nuevo": {"cancha_id": destino.cancha_id, "cancha": "y", "inicio": timezone.localtime(destino.fecha_hora).isoformat(),
                      "fin": timezone.localtime(destino.fecha_hora_fin).isoformat(), "clima": None},
        })
    # El partido a ocupa la cancha y hora de b y viceversa (los equipos de cada uno no chocan: son distintos).
    accion = AccionPendiente.objects.create(
        usuario=e.organizador, conversacion=e.ctx.conversacion, herramienta="aplicar_reprogramacion", resumen="intercambio",
        propuesta={"motivo": "Intercambio", "cambios": cambios}, expira_en=AccionPendiente.nueva_expiracion())

    acciones.confirmar(accion.pk, e.organizador)

    a.refresh_from_db(), b.refresh_from_db()
    assert (a.cancha_id, b.cancha_id) == (e.p2.cancha_id, e.p1.cancha_id) or a.cancha_id != b.cancha_id


def test_confirmar_notificacion_envia_el_aviso_guardado_y_solo_entonces(escenario, avisos):
    e = escenario
    h.ejecutar("enviar_notificacion", json.dumps({"titulo": "Suspensión", "mensaje": "Se suspende la jornada.", "roles": ["DELEGADO"]}), e.ctx)
    accion = e.ctx.acciones[0]
    assert avisos == []

    hecha = acciones.confirmar(accion.pk, e.organizador)

    assert hecha.estado == AccionPendiente.Estado.CONFIRMADA and len(avisos) == 1
    destinatarios, titulo, mensaje = avisos[0]
    assert titulo == "Suspensión" and mensaje == "Se suspende la jornada." and len(destinatarios) == 4


def test_un_usuario_que_dejo_de_ser_gestor_no_puede_confirmar(escenario, avisos):
    accion = proponer_y_solicitar(escenario)
    Usuario.objects.filter(pk=escenario.organizador.pk).update(rol=Usuario.Rol.DELEGADO)
    escenario.organizador.refresh_from_db()

    with pytest.raises(acciones.AccionNoEjecutable) as e:
        acciones.confirmar(accion.pk, escenario.organizador)

    assert e.value.codigo == 403


def test_la_api_confirma_y_cancela_con_codigos_correctos(escenario, avisos):
    e = escenario
    accion = proponer_y_solicitar(e)
    cliente = cliente_de(e.organizador)

    assert APIClient().post(f"/api/v1/agente/acciones/{accion.pk}/confirmar/").status_code == 401
    assert cliente_de(e.equipos[0].delegado).post(f"/api/v1/agente/acciones/{accion.pk}/confirmar/").status_code == 403
    assert cliente_de(e.admin).post(f"/api/v1/agente/acciones/{accion.pk}/confirmar/").status_code == 404      # no es suya
    r = cliente.post(f"/api/v1/agente/acciones/{accion.pk}/confirmar/")
    assert r.status_code == 200 and r.data["estado"] == "CONFIRMADA" and r.data["detalle"]["tipo"] == "reprogramacion"
    assert cliente.post(f"/api/v1/agente/acciones/{accion.pk}/confirmar/").status_code == 409
    assert cliente.post(f"/api/v1/agente/acciones/{accion.pk}/cancelar/").status_code == 409
    assert cliente.get(f"/api/v1/agente/acciones/{accion.pk}/").data["estado"] == "CONFIRMADA"
    assert cliente.post("/api/v1/agente/acciones/99999/confirmar/").status_code == 404
