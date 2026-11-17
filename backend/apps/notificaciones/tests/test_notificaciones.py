"""F6-03 / F6-04 — Push FCM v1, avisos manuales y recordatorios idempotentes."""
from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato
from apps.fixture.models import Partido
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.fixture.tests.helpers import cliente_de, crear_escenario, crear_usuario
from apps.ml.models import RiesgoClimatico
from apps.notificaciones import fcm, tasks
from apps.notificaciones.models import RecordatorioEnviado
from apps.notificaciones.services import notificar_usuarios
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db


class Resp:
    def __init__(self, codigo=200, cuerpo=None):
        self.status_code, self._c = codigo, cuerpo or {}
        self.ok = codigo < 400

    def json(self):
        return self._c


@pytest.fixture
def push_activo(monkeypatch):
    """FCM «configurado», con la autenticación y la red simuladas."""
    llamadas = []
    monkeypatch.setattr(fcm, "configurado", lambda: True)
    monkeypatch.setattr(fcm, "_token_de_acceso", lambda: ("token-de-acceso", "proyecto-dubss"))

    def post(self, url, json=None, timeout=None):
        llamadas.append((url, json))
        return fcm_respuestas.get(json["message"]["token"], Resp(200))

    fcm_respuestas = {}
    monkeypatch.setattr(fcm.requests.Session, "post", post)
    return llamadas, fcm_respuestas


# ── FCM HTTP v1 ───────────────────────────────────────────────────────────────

def test_sin_credenciales_el_push_queda_deshabilitado_sin_romper(settings):
    settings.FCM_CREDENTIALS_FILE = ""

    r = fcm.enviar_push(["abc"], "Hola", "Mensaje")

    assert fcm.configurado() is False
    assert r == {"enviados": 0, "invalidos": [], "fallidos": 0, "configurado": False}


def test_envia_por_http_v1_con_bearer_y_proyecto_y_limpia_tokens_muertos(push_activo):
    llamadas, respuestas = push_activo
    usuario_ok = crear_usuario(Usuario.Rol.DELEGADO)
    usuario_muerto = crear_usuario(Usuario.Rol.DELEGADO)
    Usuario.objects.filter(pk=usuario_ok.pk).update(fcm_token="tok-ok")
    Usuario.objects.filter(pk=usuario_muerto.pk).update(fcm_token="tok-muerto")
    respuestas["tok-muerto"] = Resp(404, {"error": {"status": "NOT_FOUND"}})
    usuario_ok.refresh_from_db(); usuario_muerto.refresh_from_db()

    resumen = notificar_usuarios([usuario_ok, usuario_muerto], "Partido", "Hoy juegas", {"partido_id": 7})

    assert resumen["push"] == 1
    urls = {u for u, _ in llamadas}
    assert urls == {"https://fcm.googleapis.com/v1/projects/proyecto-dubss/messages:send"}
    cuerpo = next(c for _, c in llamadas if c["message"]["token"] == "tok-ok")["message"]
    assert cuerpo["notification"] == {"title": "Partido", "body": "Hoy juegas"}
    assert cuerpo["data"] == {"partido_id": "7"}                    # FCM v1 exige valores string
    usuario_muerto.refresh_from_db()
    assert usuario_muerto.fcm_token == ""                            # token inválido limpiado
    usuario_ok.refresh_from_db()
    assert usuario_ok.fcm_token == "tok-ok"


def test_un_error_de_red_o_del_servidor_no_borra_el_token(push_activo):
    _, respuestas = push_activo
    u = crear_usuario(Usuario.Rol.DELEGADO)
    Usuario.objects.filter(pk=u.pk).update(fcm_token="tok-x")
    respuestas["tok-x"] = Resp(503, {"error": {"status": "UNAVAILABLE"}})

    r = fcm.enviar_push(["tok-x"], "T", "M")

    assert r["enviados"] == 0 and r["fallidos"] == 1 and r["invalidos"] == []


def test_si_firebase_rechaza_las_credenciales_el_correo_igual_sale(monkeypatch):
    monkeypatch.setattr(fcm, "configurado", lambda: True)
    monkeypatch.setattr(fcm, "_token_de_acceso", lambda: (_ for _ in ()).throw(RuntimeError("credenciales vencidas")))
    u = crear_usuario(Usuario.Rol.DELEGADO)
    Usuario.objects.filter(pk=u.pk).update(fcm_token="tok")
    u.refresh_from_db()

    resumen = notificar_usuarios([u], "Aviso", "Texto")

    assert resumen["push"] == 0 and resumen["email"] == 1 and len(mail.outbox) == 1


def test_los_usuarios_inactivos_no_reciben_avisos():
    activo = crear_usuario(Usuario.Rol.DELEGADO)
    inactivo = crear_usuario(Usuario.Rol.DELEGADO)
    Usuario.objects.filter(pk=inactivo.pk).update(is_active=False)
    inactivo.refresh_from_db()

    resumen = notificar_usuarios([activo, inactivo, None, activo], "T", "M")

    assert resumen["usuarios"] == 1 and mail.outbox[0].to == [activo.email]


# ── Envío manual ──────────────────────────────────────────────────────────────

def test_el_envio_manual_filtra_por_rol_y_facultad_y_queda_en_bitacora():
    esc = crear_escenario(equipos=3, canchas=1)
    destino = esc.equipos[0].delegado
    url = reverse("notificacion-enviar")

    r = esc.client_org.post(url, {"mensaje": "Reunión técnica", "titulo": "Aviso", "roles": ["DELEGADO"],
                                  "facultad": destino.facultad_id}, format="json")

    assert r.status_code == 200 and r.data["usuarios"] == 1 and r.data["email"] == 1
    assert mail.outbox[0].to == [destino.email] and mail.outbox[0].subject == "Aviso"
    registro = Bitacora.objects.get(modulo="notificacion")
    assert registro.usuario == esc.organizador and registro.detalle["destinatarios"] == 1


def test_el_envio_manual_exige_destinatarios_y_mensaje():
    esc = crear_escenario(equipos=2, canchas=1)
    url = reverse("notificacion-enviar")

    sin_destino = esc.client.post(url, {"mensaje": "Hola"}, format="json")
    sin_mensaje = esc.client.post(url, {"todos": True, "mensaje": "   "}, format="json")
    nadie = esc.client.post(url, {"mensaje": "Hola", "usuarios": [999999]}, format="json")

    assert sin_destino.status_code == 400 and "destinatarios" in sin_destino.data
    assert sin_mensaje.status_code == 400 and "mensaje" in sin_mensaje.data
    assert nadie.status_code == 400 and "Ningún usuario" in nadie.data["detail"]
    assert not mail.outbox


def test_solo_administracion_y_organizacion_pueden_enviar_avisos():
    esc = crear_escenario(equipos=2, canchas=1)
    url = reverse("notificacion-enviar")
    cuerpo = {"mensaje": "Hola", "todos": True}

    assert APIClient().post(url, cuerpo, format="json").status_code == 401
    assert cliente_de(esc.equipos[0].delegado).post(url, cuerpo, format="json").status_code == 403
    assert cliente_de(crear_usuario(Usuario.Rol.JUGADOR)).post(url, cuerpo, format="json").status_code == 403
    assert esc.client.post(url, cuerpo, format="json").status_code == 200


def test_el_envio_masivo_no_alcanza_a_cuentas_jugador_ni_superadmin():
    esc = crear_escenario(equipos=2, canchas=1)
    crear_usuario(Usuario.Rol.JUGADOR)

    r = esc.client.post(reverse("notificacion-enviar"), {"mensaje": "Hola", "todos": True}, format="json")

    # admin + organizador + 2 delegados
    assert r.data["usuarios"] == 4


def test_canales_informa_que_esta_configurado(settings):
    esc = crear_escenario(equipos=2, canchas=1)
    settings.FCM_CREDENTIALS_FILE = ""
    settings.N8N_URL_EVENTOS = settings.N8N_SECRETO = ""

    r = esc.client.get(reverse("notificacion-canales"))

    assert r.data == {"push": False, "email": True, "whatsapp": False}
    settings.N8N_URL_EVENTOS, settings.N8N_SECRETO = "http://n8n:5678/webhook/x", "secreto"
    assert esc.client.get(reverse("notificacion-canales")).data["whatsapp"] is True


# ── Recordatorios de partido (idempotentes) ───────────────────────────────────

def _partido_en_curso(horas):
    esc = crear_escenario(equipos=2, canchas=1)
    (partido,) = FixtureGenerator(esc.campeonato.pk).generar()
    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=Campeonato.Estado.EN_CURSO)
    partido.fecha_hora = timezone.now() + timedelta(hours=horas)
    partido.save()
    return esc, partido


def test_recordatorio_de_24h_llega_a_los_dos_delegados_y_no_se_repite():
    esc, partido = _partido_en_curso(20)

    primero = tasks.enviar_recordatorios()
    segundo = tasks.enviar_recordatorios()

    assert primero == {"enviados": 1} and segundo == {"enviados": 0}
    assert {m.to[0] for m in mail.outbox} == {e.delegado.email for e in esc.equipos} or \
        sorted(a for m in mail.outbox for a in m.to) == sorted(e.delegado.email for e in esc.equipos)
    registro = RecordatorioEnviado.objects.get(partido=partido)
    assert registro.tipo == "24H" and registro.destinatarios == 2
    assert "Recordatorio de partido" in mail.outbox[0].subject


def test_recordatorio_de_2h_es_distinto_y_sale_aparte():
    _, partido = _partido_en_curso(20)
    tasks.enviar_recordatorios()
    partido.fecha_hora = timezone.now() + timedelta(hours=1)
    partido.save()

    r = tasks.enviar_recordatorios()
    repetido = tasks.enviar_recordatorios()

    assert r == {"enviados": 1} and repetido == {"enviados": 0}
    assert sorted(RecordatorioEnviado.objects.values_list("tipo", flat=True)) == ["24H", "2H"]
    assert any("2 horas" in m.subject for m in mail.outbox)


def test_un_partido_con_menos_de_2h_no_recibe_tambien_el_de_24h():
    _, partido = _partido_en_curso(1)

    tasks.enviar_recordatorios()

    assert list(RecordatorioEnviado.objects.values_list("tipo", flat=True)) == ["2H"]


@pytest.mark.parametrize("horas", [30, -1])
def test_no_hay_recordatorio_si_falta_mas_de_24h_o_ya_empezo(horas):
    _partido_en_curso(horas)

    assert tasks.enviar_recordatorios() == {"enviados": 0} and not mail.outbox


def test_no_se_recuerda_un_fixture_en_borrador_ni_un_partido_ya_resuelto():
    esc, partido = _partido_en_curso(10)
    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=Campeonato.Estado.INSCRIPCION_CERRADA)
    assert tasks.enviar_recordatorios() == {"enviados": 0}          # borrador: aún no es público

    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=Campeonato.Estado.EN_CURSO)
    Partido.objects.filter(pk=partido.pk).update(estado=Partido.Estado.SUSPENDIDO)
    assert tasks.enviar_recordatorios() == {"enviados": 0}


def test_el_recordatorio_advierte_si_hay_riesgo_climatico_alto():
    _, partido = _partido_en_curso(10)
    RiesgoClimatico.objects.create(partido=partido, nivel_riesgo="ALTO", fuente_api="Open-Meteo")

    tasks.enviar_recordatorios()

    assert "riesgo climático" in mail.outbox[0].body.lower()


def test_la_tarea_esta_programada_en_el_calendario_de_celery(settings):
    tareas = {v["task"] for v in settings.CELERY_BEAT_SCHEDULE.values()}
    assert tareas == {"notificaciones.enviar_recordatorios", "ml.actualizar_riesgo_climatico",
                      "fixture.reconstruir_historial", "ml.reentrenar_modelos", "agente.expirar_acciones",
                      "fixture.purgar_operaciones_idempotentes", "ml.revisar_resultados_atipicos",
                      "integraciones.despachar_eventos", "integraciones.purgar_eventos",
                      "notificaciones.purgar_bandeja"}
