"""Bandeja de notificaciones dentro de la app y propiedad del token de push."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.fixture.tests.helpers import cliente_de, crear_usuario
from apps.notificaciones import tasks
from apps.notificaciones.models import Notificacion
from apps.notificaciones.services import notificar_usuarios
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
R = Usuario.Rol
MIS = "/api/v1/notificaciones/mis/"


# ─── La bandeja se llena sola ─────────────────────────────────────────────────

def test_cada_destinatario_activo_recibe_su_notificacion_aunque_no_haya_ningun_canal_externo(settings):
    settings.N8N_URL_EVENTOS = settings.N8N_SECRETO = ""
    a, b = crear_usuario(R.DELEGADO), crear_usuario(R.ORGANIZADOR)
    inactivo = crear_usuario(R.DELEGADO)
    Usuario.objects.filter(pk=inactivo.pk).update(is_active=False)
    inactivo.refresh_from_db()

    r = notificar_usuarios([a, b, a, inactivo, None], "Partido mañana", "A vs B a las 18:00", {"partido_id": 7})

    assert r["bandeja"] == 2
    assert sorted(Notificacion.objects.values_list("usuario_id", flat=True)) == sorted([a.pk, b.pk])
    n = Notificacion.objects.get(usuario=a)
    assert (n.titulo, n.mensaje, n.datos, n.leida_en) == ("Partido mañana", "A vs B a las 18:00", {"partido_id": 7}, None)


def test_titulo_y_mensaje_largos_se_recortan_sin_romper_el_aviso():
    u = crear_usuario(R.DELEGADO)
    notificar_usuarios([u], "T" * 300, "M" * 900)
    n = Notificacion.objects.get()
    assert len(n.titulo) == 100 and len(n.mensaje) == 500


def test_un_fallo_al_guardar_la_bandeja_no_impide_el_resto_de_los_canales(monkeypatch, mailoutbox):
    def falla(*a, **k):
        raise RuntimeError("base caída")
    monkeypatch.setattr(Notificacion.objects, "bulk_create", falla)
    u = crear_usuario(R.DELEGADO)
    r = notificar_usuarios([u], "T", "M")
    assert r["bandeja"] == 0 and r["email"] == 1 and len(mailoutbox) == 1


# ─── Leer la bandeja ──────────────────────────────────────────────────────────

def test_solo_veo_mis_notificaciones_las_mas_nuevas_primero():
    yo, otro = crear_usuario(R.DELEGADO), crear_usuario(R.DELEGADO)
    notificar_usuarios([yo], "Primera", "1")
    notificar_usuarios([otro], "Ajena", "x")
    notificar_usuarios([yo], "Segunda", "2")
    r = cliente_de(yo).get(MIS)
    assert r.status_code == 200
    assert [n["titulo"] for n in r.json()["results"]] == ["Segunda", "Primera"]
    assert r.json()["results"][0]["leida"] is False


def test_filtro_de_no_leidas_y_resumen():
    yo = crear_usuario(R.ORGANIZADOR)
    for i in range(3):
        notificar_usuarios([yo], f"N{i}", "m")
    c = cliente_de(yo)
    primera = c.get(MIS).json()["results"][0]["id"]
    assert c.post(f"{MIS}{primera}/leer/").status_code == 200

    assert c.get("/api/v1/notificaciones/mis/resumen/").json() == {"no_leidas": 2}
    assert len(c.get(MIS, {"no_leidas": "1"}).json()["results"]) == 2
    assert len(c.get(MIS).json()["results"]) == 3


def test_leer_es_idempotente_y_conserva_la_primera_hora_de_lectura():
    yo = crear_usuario(R.DELEGADO)
    notificar_usuarios([yo], "T", "M")
    n = Notificacion.objects.get()
    c = cliente_de(yo)
    c.post(f"{MIS}{n.pk}/leer/")
    primera = Notificacion.objects.get().leida_en
    c.post(f"{MIS}{n.pk}/leer/")
    assert Notificacion.objects.get().leida_en == primera and primera is not None


def test_no_se_puede_leer_la_notificacion_de_otro_usuario():
    yo, otro = crear_usuario(R.DELEGADO), crear_usuario(R.DELEGADO)
    notificar_usuarios([otro], "Privada", "m")
    n = Notificacion.objects.get()
    assert cliente_de(yo).post(f"{MIS}{n.pk}/leer/").status_code == 404
    assert Notificacion.objects.get().leida_en is None


def test_marcar_todas_solo_afecta_las_mias():
    yo, otro = crear_usuario(R.DELEGADO), crear_usuario(R.DELEGADO)
    notificar_usuarios([yo, yo.__class__.objects.get(pk=otro.pk)], "A", "m")
    notificar_usuarios([yo], "B", "m")
    r = cliente_de(yo).post("/api/v1/notificaciones/mis/leer-todas/")
    assert r.json() == {"marcadas": 2}
    assert Notificacion.objects.filter(usuario=otro, leida_en__isnull=True).count() == 1


def test_sin_sesion_no_hay_bandeja():
    assert APIClient().get(MIS).status_code == 401
    assert APIClient().get("/api/v1/notificaciones/mis/resumen/").status_code == 401


@pytest.mark.parametrize("rol", [R.ADMIN_DUBSS, R.ORGANIZADOR, R.DELEGADO, R.JUGADOR, R.SUPERADMIN])
def test_todo_rol_con_panel_tiene_su_bandeja(rol):
    u = crear_usuario(rol)
    assert cliente_de(u).get(MIS).status_code == 200


# ─── Limpieza ─────────────────────────────────────────────────────────────────

def test_purga_de_la_bandeja():
    u = crear_usuario(R.DELEGADO)
    ahora = timezone.now()
    vieja_leida = Notificacion.objects.create(usuario=u, titulo="a", mensaje="m", leida_en=ahora)
    vieja_sin_leer = Notificacion.objects.create(usuario=u, titulo="b", mensaje="m")
    muy_vieja = Notificacion.objects.create(usuario=u, titulo="c", mensaje="m")
    reciente = Notificacion.objects.create(usuario=u, titulo="d", mensaje="m", leida_en=ahora)
    Notificacion.objects.filter(pk=vieja_leida.pk).update(creada=ahora - timedelta(days=31))
    Notificacion.objects.filter(pk=vieja_sin_leer.pk).update(creada=ahora - timedelta(days=45))
    Notificacion.objects.filter(pk=muy_vieja.pk).update(creada=ahora - timedelta(days=91))
    assert tasks.purgar_bandeja() == {"leidas": 1, "viejas": 1}
    assert set(Notificacion.objects.values_list("pk", flat=True)) == {vieja_sin_leer.pk, reciente.pk}


def test_los_recordatorios_tambien_llegan_a_la_bandeja_de_los_delegados():
    from apps.notificaciones.tests.test_notificaciones import _partido_en_curso
    esc, partido = _partido_en_curso(20)
    tasks.enviar_recordatorios()
    for e in esc.equipos:
        n = Notificacion.objects.get(usuario=e.delegado)
        assert n.datos["partido_id"] == partido.pk and "vs" in n.mensaje


# ─── Token de push: un celular, una cuenta ────────────────────────────────────

TOKEN = "/api/v1/usuarios/fcm-token/"


def test_registrar_el_token_lo_guarda_y_lo_retira_de_otra_cuenta():
    a, b = crear_usuario(R.DELEGADO), crear_usuario(R.ORGANIZADOR)
    assert cliente_de(a).post(TOKEN, {"fcm_token": "tok-celular-1"}, format="json").status_code == 200
    assert Usuario.objects.get(pk=a.pk).fcm_token == "tok-celular-1"
    # b inicia sesión en el mismo celular: el token pasa a b y a deja de recibir avisos allí
    assert cliente_de(b).post(TOKEN, {"fcm_token": "tok-celular-1"}, format="json").status_code == 200
    assert Usuario.objects.get(pk=b.pk).fcm_token == "tok-celular-1"
    assert Usuario.objects.get(pk=a.pk).fcm_token == ""


def test_token_vacio_o_enorme_es_400_y_no_cambia_nada():
    a = crear_usuario(R.DELEGADO)
    Usuario.objects.filter(pk=a.pk).update(fcm_token="previo")
    c = cliente_de(a)
    assert c.post(TOKEN, {"fcm_token": "  "}, format="json").status_code == 400
    assert c.post(TOKEN, {}, format="json").status_code == 400
    assert c.post(TOKEN, {"fcm_token": "x" * 300}, format="json").status_code == 400
    assert Usuario.objects.get(pk=a.pk).fcm_token == "previo"


def test_quitar_el_token():
    a = crear_usuario(R.DELEGADO)
    Usuario.objects.filter(pk=a.pk).update(fcm_token="tok")
    assert cliente_de(a).delete(TOKEN).status_code == 204
    assert Usuario.objects.get(pk=a.pk).fcm_token == ""


def test_el_jugador_es_de_solo_lectura_y_no_registra_push_pero_si_tiene_bandeja():
    j = crear_usuario(R.JUGADOR)
    assert cliente_de(j).post(TOKEN, {"fcm_token": "tok-j"}, format="json").status_code == 403
    assert cliente_de(j).get(MIS).status_code == 200


def test_sin_sesion_no_se_registra_token():
    assert APIClient().post(TOKEN, {"fcm_token": "t"}, format="json").status_code == 401


def test_cerrar_sesion_retira_el_token_del_celular():
    a = crear_usuario(R.DELEGADO)
    Usuario.objects.filter(pk=a.pk).update(fcm_token="tok-a")
    refresh = str(RefreshToken.for_user(a))
    r = cliente_de(a).post("/api/v1/auth/logout/", {"refresh": refresh}, format="json")
    assert r.status_code == 200
    assert Usuario.objects.get(pk=a.pk).fcm_token == ""
