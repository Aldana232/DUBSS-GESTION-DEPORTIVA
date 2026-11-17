"""n8n + WhatsApp: firma, consentimiento, cola de salida con reintentos y consultas entrantes."""
import json
import time
from datetime import timedelta

import pytest
import requests
from django.core.cache import cache
from django.utils import timezone

from apps.auditoria.models import Bitacora
from apps.deportes.models import Campeonato
from apps.fixture.models import Partido, Resultado
from apps.fixture.services.fixture_generator import FixtureGenerator
from apps.fixture.tests.helpers import cliente_de, crear_escenario, crear_usuario
from apps.integraciones import entrante, servicios, tasks
from apps.integraciones.firma import TOLERANCIA_SEGUNDOS, firmar, verificar
from apps.integraciones.models import EventoSaliente
from apps.integraciones.telefono import normalizar_whatsapp
from apps.notificaciones.services import notificar_usuarios
from apps.users.models import Usuario

pytestmark = pytest.mark.django_db
SECRETO = "secreto-de-prueba-0123456789"
URL = "http://n8n:5678/webhook/dubss-eventos"
E = EventoSaliente.Estado


@pytest.fixture(autouse=True)
def limpiar_cache():
    cache.clear()


@pytest.fixture
def n8n(settings):
    settings.N8N_URL_EVENTOS, settings.N8N_SECRETO = URL, SECRETO
    return settings


def con_whatsapp(rol=Usuario.Rol.DELEGADO, numero="59170000001", acepta=True, **kw):
    u = crear_usuario(rol, **kw)
    u.whatsapp, u.acepta_whatsapp = numero, acepta
    u.save(update_fields=["whatsapp", "acepta_whatsapp"])
    return u


class Resp:
    def __init__(self, codigo=200):
        self.status_code = codigo


# ─── Firma ────────────────────────────────────────────────────────────────────

def test_firma_valida_y_se_rechaza_si_se_altera_el_cuerpo_o_la_marca():
    marca, cuerpo = int(time.time()), b'{"a":1}'
    f = firmar(SECRETO, marca, cuerpo)
    assert f.startswith("sha256=")
    assert verificar(SECRETO, str(marca), f, cuerpo)
    assert not verificar(SECRETO, str(marca), f, b'{"a":2}')                    # cuerpo alterado
    assert not verificar(SECRETO, str(marca + 1), f, cuerpo)                    # marca alterada
    assert not verificar("otro-secreto", str(marca), f, cuerpo)                 # otro secreto


def test_firma_vieja_se_rechaza_aunque_sea_autentica():
    vieja = int(time.time()) - TOLERANCIA_SEGUNDOS - 5
    assert not verificar(SECRETO, str(vieja), firmar(SECRETO, vieja, b"x"), b"x")


@pytest.mark.parametrize("marca,firma,secreto", [(None, "sha256=a", SECRETO), ("1", None, SECRETO), ("abc", "sha256=a", SECRETO), ("1", "sha256=a", "")])
def test_firma_incompleta_se_rechaza(marca, firma, secreto):
    assert not verificar(secreto, marca, firma, b"x")


# ─── Número de WhatsApp ───────────────────────────────────────────────────────

@pytest.mark.parametrize("entrada,esperado", [
    ("70012345", "59170012345"), ("+591 700-12345", "59170012345"), ("59170012345", "59170012345"),
    ("0059170012345", "59170012345"), ("+54 9 11 5555 1234", "5491155551234"), ("", ""), ("   ", ""),
])
def test_normaliza_numeros(entrada, esperado):
    assert normalizar_whatsapp(entrada) == esperado


@pytest.mark.parametrize("entrada", ["abc", "123", "+0123456789", "1234567890123456", "7001-2345 ext 9"])
def test_numeros_invalidos(entrada):
    with pytest.raises(ValueError):
        normalizar_whatsapp(entrada)


# ─── Perfil: número y consentimiento ──────────────────────────────────────────

def _patch(usuario, **datos):
    return cliente_de(usuario).patch("/api/v1/usuarios/perfil/", datos, format="json")


def test_el_perfil_normaliza_el_numero_y_registra_el_consentimiento():
    u = crear_usuario(Usuario.Rol.DELEGADO)
    r = _patch(u, whatsapp="700 12345", acepta_whatsapp=True)
    assert r.status_code == 200, r.content
    u.refresh_from_db()
    assert (u.whatsapp, u.acepta_whatsapp) == ("59170012345", True)
    assert u.whatsapp_aceptado_en is not None


def test_no_se_puede_aceptar_sin_numero():
    u = crear_usuario(Usuario.Rol.DELEGADO)
    r = _patch(u, acepta_whatsapp=True)
    assert r.status_code == 400 and "whatsapp" in r.json()


def test_numero_invalido_o_repetido_da_400():
    otro = con_whatsapp(numero="59170000002")
    u = crear_usuario(Usuario.Rol.DELEGADO)
    assert _patch(u, whatsapp="abc").status_code == 400
    r = _patch(u, whatsapp="59170000002")
    assert r.status_code == 400 and "otra cuenta" in str(r.json())
    assert Usuario.objects.get(pk=otro.pk).whatsapp == "59170000002"


def test_cambiar_de_numero_sin_reconfirmar_quita_el_consentimiento():
    u = con_whatsapp(numero="59170000003")
    assert _patch(u, whatsapp="59170000004").status_code == 200
    u.refresh_from_db()
    assert u.whatsapp == "59170000004" and u.acepta_whatsapp is False and u.whatsapp_aceptado_en is None


def test_borrar_el_numero_quita_el_consentimiento():
    u = con_whatsapp(numero="59170000005")
    assert _patch(u, whatsapp="").status_code == 200
    u.refresh_from_db()
    assert (u.whatsapp, u.acepta_whatsapp) == ("", False)


def test_un_administrador_no_puede_dar_el_consentimiento_por_otra_persona():
    admin = crear_usuario(Usuario.Rol.ADMIN_DUBSS)
    u = crear_usuario(Usuario.Rol.ORGANIZADOR)
    r = cliente_de(admin).patch(f"/api/v1/usuarios/{u.pk}/", {"whatsapp": "59170000009", "acepta_whatsapp": True}, format="json")
    assert r.status_code == 200
    u.refresh_from_db()
    assert (u.whatsapp, u.acepta_whatsapp) == ("", False)


# ─── Encolar avisos ───────────────────────────────────────────────────────────

def test_sin_configurar_no_se_guarda_ningun_evento(settings):
    settings.N8N_URL_EVENTOS = settings.N8N_SECRETO = ""
    u = con_whatsapp()
    assert notificar_usuarios([u], "T", "M")["whatsapp"] == 0
    assert EventoSaliente.objects.count() == 0


def test_solo_reciben_los_activos_que_aceptaron_y_sin_duplicados(n8n):
    si = con_whatsapp(numero="59170000010")
    no_acepta = con_whatsapp(numero="59170000011", acepta=False)
    sin_numero = crear_usuario(Usuario.Rol.DELEGADO)
    inactivo = con_whatsapp(numero="59170000012")
    Usuario.objects.filter(pk=inactivo.pk).update(is_active=False)
    inactivo.refresh_from_db()

    r = notificar_usuarios([si, si, no_acepta, sin_numero, inactivo], "Título", "Mensaje")

    assert r["whatsapp"] == 1 and r["whatsapp_configurado"] is True
    (ev,) = EventoSaliente.objects.all()
    assert ev.tipo == "aviso" and ev.estado == E.PENDIENTE
    assert ev.payload["destinatarios"] == [{"nombre": si.nombre, "whatsapp": "59170000010"}]
    assert "email" not in json.dumps(ev.payload) and si.email not in json.dumps(ev.payload)   # mínimo necesario


def test_los_destinatarios_se_reparten_en_eventos_de_hasta_50(n8n):
    usuarios = [con_whatsapp(numero=f"5917{i:07d}") for i in range(1, 121)]
    assert servicios.encolar_aviso(usuarios, "T", "M") == 120
    assert sorted(len(e.payload["destinatarios"]) for e in EventoSaliente.objects.all()) == [20, 50, 50]


def test_un_fallo_al_encolar_no_rompe_el_resto_de_los_canales(n8n, monkeypatch):
    def falla(*a, **k):
        raise RuntimeError("base caída")
    monkeypatch.setattr(servicios, "encolar_aviso", falla)
    u = con_whatsapp()
    r = notificar_usuarios([u], "T", "M")
    assert r["usuarios"] == 1 and r["whatsapp"] == 0


# ─── Entrega a n8n ────────────────────────────────────────────────────────────

def _una_entrega(monkeypatch, respuesta):
    capturado = {}

    def post(url, data=None, headers=None, timeout=None):
        capturado.update(url=url, data=data, headers=headers, timeout=timeout)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta
    monkeypatch.setattr(requests, "post", post)
    return capturado


def test_entrega_firmada_y_marca_como_entregado(n8n, monkeypatch):
    u = con_whatsapp()
    notificar_usuarios([u], "Partido", "Hoy 18:00")
    capturado = _una_entrega(monkeypatch, Resp(200))
    # El evento «ya venció»: no depende de que el reloj del contenedor avance entre crearlo y despacharlo.
    EventoSaliente.objects.update(proximo_intento=timezone.now() - timedelta(seconds=1))

    assert servicios.despachar() == {"entregados": 1, "reintentos": 0, "fallidos": 0}

    ev = EventoSaliente.objects.get()
    assert ev.estado == E.ENTREGADO and ev.entregado_en and ev.intentos == 1
    h = capturado["headers"]
    assert capturado["url"] == URL and capturado["timeout"] == servicios.TIMEOUT_SEG
    assert verificar(SECRETO, h["X-DUBSS-Timestamp"], h["X-DUBSS-Signature"], capturado["data"])   # n8n puede verificarla
    sobre = json.loads(capturado["data"])
    assert sobre["id"] == str(ev.id) == h["X-DUBSS-Event-Id"] and sobre["tipo"] == "aviso" and sobre["version"] == 1
    assert sobre["datos"]["mensaje"] == "Hoy 18:00"


@pytest.mark.parametrize("respuesta,texto", [(Resp(500), "HTTP 500"), (requests.ConnectionError("x"), "Sin conexión")])
def test_si_n8n_falla_se_reintenta_con_espera_creciente(n8n, monkeypatch, respuesta, texto):
    notificar_usuarios([con_whatsapp()], "T", "M")
    _una_entrega(monkeypatch, respuesta)
    ahora = timezone.now()

    assert servicios.despachar() == {"entregados": 0, "reintentos": 1, "fallidos": 0}

    ev = EventoSaliente.objects.get()
    assert ev.estado == E.PENDIENTE and ev.intentos == 1 and texto in ev.ultimo_error
    assert timedelta(seconds=50) < ev.proximo_intento - ahora < timedelta(minutes=2)       # 1.er reintento: ~1 min
    assert servicios.despachar() == {"entregados": 0, "reintentos": 0, "fallidos": 0}      # aún no toca


def test_agotados_los_reintentos_queda_fallido(n8n, monkeypatch):
    notificar_usuarios([con_whatsapp()], "T", "M")
    _una_entrega(monkeypatch, Resp(502))
    for _ in range(len(n8n.INTEGRACION_REINTENTOS_MINUTOS) + 1):
        EventoSaliente.objects.filter(estado=E.PENDIENTE).update(proximo_intento=timezone.now() - timedelta(seconds=1))
        servicios.despachar()
    ev = EventoSaliente.objects.get()
    assert ev.estado == E.FALLIDO and ev.intentos == len(n8n.INTEGRACION_REINTENTOS_MINUTOS) + 1
    assert servicios.despachar() == {"entregados": 0, "reintentos": 0, "fallidos": 0}


def test_un_evento_en_envio_no_lo_toma_otro_worker(n8n, monkeypatch):
    notificar_usuarios([con_whatsapp()], "T", "M")
    reservados = servicios._reservar(10)
    assert len(reservados) == 1
    assert servicios._reservar(10) == []                       # arrendado: el segundo worker no lo ve
    assert EventoSaliente.objects.get().intentos == 1


def test_recupera_un_evento_cuyo_worker_murio_a_mitad(n8n, monkeypatch):
    notificar_usuarios([con_whatsapp()], "T", "M")
    servicios._reservar(10)                                    # el worker «murió» sin guardar el resultado
    EventoSaliente.objects.update(proximo_intento=timezone.now() - timedelta(seconds=1))
    _una_entrega(monkeypatch, Resp(200))
    assert servicios.despachar()["entregados"] == 1


def test_despachar_sin_configurar_no_hace_nada(settings):
    settings.N8N_URL_EVENTOS = settings.N8N_SECRETO = ""
    assert servicios.despachar() == {"entregados": 0, "reintentos": 0, "fallidos": 0}


def test_purga_de_eventos_viejos(n8n):
    a = EventoSaliente.objects.create(tipo="aviso", estado=E.ENTREGADO)
    b = EventoSaliente.objects.create(tipo="aviso", estado=E.ENTREGADO)
    c = EventoSaliente.objects.create(tipo="aviso", estado=E.FALLIDO)
    d = EventoSaliente.objects.create(tipo="aviso", estado=E.PENDIENTE)
    EventoSaliente.objects.filter(pk=a.pk).update(creado=timezone.now() - timedelta(days=31))
    EventoSaliente.objects.filter(pk=c.pk).update(creado=timezone.now() - timedelta(days=91))
    EventoSaliente.objects.filter(pk=d.pk).update(creado=timezone.now() - timedelta(days=400))
    assert tasks.purgar_eventos() == {"entregados": 1, "fallidos": 1}
    assert set(EventoSaliente.objects.values_list("pk", flat=True)) == {b.pk, d.pk}      # el pendiente nunca se purga


# ─── Estado y prueba (administración) ─────────────────────────────────────────

def test_estado_solo_para_administradores(n8n):
    for rol in (Usuario.Rol.ORGANIZADOR, Usuario.Rol.DELEGADO, Usuario.Rol.JUGADOR):
        assert cliente_de(crear_usuario(rol)).get("/api/v1/integraciones/estado/").status_code == 403
    assert cliente_de(crear_usuario(Usuario.Rol.ADMIN_DUBSS)).get("/api/v1/integraciones/estado/").status_code == 200


def test_estado_resume_la_cola_sin_exponer_el_secreto(n8n):
    con_whatsapp(numero="59170000020")
    EventoSaliente.objects.create(tipo="aviso", estado=E.PENDIENTE)
    EventoSaliente.objects.create(tipo="aviso", estado=E.ENTREGADO)
    EventoSaliente.objects.create(tipo="aviso", estado=E.FALLIDO, ultimo_error="n8n respondió HTTP 500.")
    r = cliente_de(crear_usuario(Usuario.Rol.SUPERADMIN)).get("/api/v1/integraciones/estado/")
    d = r.json()
    assert d["configurado"] is True and d["destino"] == "n8n:5678"
    assert (d["pendientes"], d["entregados_24h"], d["fallidos"], d["usuarios_con_whatsapp"]) == (1, 1, 1, 1)
    assert SECRETO not in r.content.decode() and "webhook" not in r.content.decode()      # ni secreto ni ruta


def test_prueba_envia_el_evento_y_queda_en_bitacora(n8n, monkeypatch):
    capturado = _una_entrega(monkeypatch, Resp(200))
    admin = con_whatsapp(Usuario.Rol.ADMIN_DUBSS, numero="59170000030")
    r = cliente_de(admin).post("/api/v1/integraciones/prueba/", {"mensaje": "Hola"}, format="json")
    assert r.status_code == 200 and r.json() == {"entregado": True, "error": "", "recibira_whatsapp": True}
    assert json.loads(capturado["data"])["datos"]["destinatarios"] == [{"nombre": admin.nombre, "whatsapp": "59170000030"}]
    assert Bitacora.objects.filter(modulo="integraciones", resultado="OK").exists()


def test_prueba_con_n8n_caido_da_502_y_no_se_reintenta(n8n, monkeypatch):
    _una_entrega(monkeypatch, requests.ConnectionError("x"))
    r = cliente_de(crear_usuario(Usuario.Rol.ADMIN_DUBSS)).post("/api/v1/integraciones/prueba/", {}, format="json")
    assert r.status_code == 502 and r.json()["entregado"] is False
    assert EventoSaliente.objects.get().estado == E.FALLIDO
    assert Bitacora.objects.filter(modulo="integraciones", resultado="ERROR").exists()


def test_prueba_sin_configurar_da_400(settings):
    settings.N8N_URL_EVENTOS = settings.N8N_SECRETO = ""
    assert cliente_de(crear_usuario(Usuario.Rol.ADMIN_DUBSS)).post("/api/v1/integraciones/prueba/", {}, format="json").status_code == 400


# ─── Mensajes entrantes ───────────────────────────────────────────────────────

def _entrante(cliente, numero, texto, *, secreto=SECRETO, marca=None, cuerpo=None):
    cuerpo = cuerpo if cuerpo is not None else json.dumps({"whatsapp": numero, "texto": texto}).encode()
    marca = int(time.time()) if marca is None else marca
    return cliente.post("/api/v1/integraciones/whatsapp/mensaje/", data=cuerpo, content_type="application/json",
                        HTTP_X_DUBSS_TIMESTAMP=str(marca), HTTP_X_DUBSS_SIGNATURE=firmar(secreto, marca, cuerpo))


@pytest.fixture
def http():
    from django.test import Client
    return Client()


def test_entrante_sin_firma_o_con_firma_mala_da_401(n8n, http):
    cuerpo = json.dumps({"whatsapp": "59170000040", "texto": "partidos"}).encode()
    assert http.post("/api/v1/integraciones/whatsapp/mensaje/", data=cuerpo, content_type="application/json").status_code == 401
    assert _entrante(http, "59170000040", "partidos", secreto="otro").status_code == 401
    assert _entrante(http, "59170000040", "partidos", marca=int(time.time()) - 3600).status_code == 401   # repetido tarde


def test_entrante_sin_secreto_configurado_se_rechaza_siempre(settings, http):
    settings.N8N_SECRETO = ""
    assert _entrante(http, "59170000040", "hola", secreto="").status_code == 401


def test_entrante_cuerpo_gigante_se_rechaza(n8n, http):
    cuerpo = json.dumps({"whatsapp": "59170000040", "texto": "x" * 5000}).encode()
    assert _entrante(http, "", "", cuerpo=cuerpo).status_code == 401


def test_numero_no_registrado_o_sin_consentimiento_recibe_instrucciones(n8n, http):
    con_whatsapp(numero="59170000041", acepta=False)
    for numero in ("59170000099", "59170000041"):
        r = _entrante(http, numero, "partidos")
        assert r.status_code == 200 and r.json()["intencion"] == "no_registrado"
        assert "activa" in r.json()["respuesta"]


def test_ayuda_y_mensaje_desconocido(n8n, http):
    con_whatsapp(numero="59170000042")
    assert _entrante(http, "59170000042", "Hola").json()["intencion"] == "ayuda"
    r = _entrante(http, "59170000042", "borra todos los partidos").json()
    assert r["intencion"] == "desconocido" and "PARTIDOS" in r["respuesta"]            # sin acciones: solo ayuda


def test_el_delegado_solo_ve_sus_partidos_y_resultados(n8n, http):
    esc = crear_escenario(equipos=4, canchas=2)
    FixtureGenerator(esc.campeonato.pk).generar()
    Campeonato.objects.filter(pk=esc.campeonato.pk).update(estado=Campeonato.Estado.EN_CURSO)
    for i, p in enumerate(Partido.objects.order_by("pk")):            # días distintos: sin choques de cancha ni de equipo
        inicio = timezone.now() + timedelta(days=i + 1)
        Partido.objects.filter(pk=p.pk).update(fecha_hora=inicio, fecha_hora_fin=inicio + timedelta(hours=2))
    mio = esc.equipos[0]
    Usuario.objects.filter(pk=mio.delegado.pk).update(whatsapp="59170000043", acepta_whatsapp=True)

    texto = _entrante(http, "59170000043", "PARTIDOS").json()["respuesta"]
    mis = Partido.objects.filter(equipo_local=mio) | Partido.objects.filter(equipo_visitante=mio)
    assert texto.startswith("Próximos partidos:") and len(texto.splitlines()) - 1 == mis.count()
    assert mio.nombre in texto and "Facultad" not in texto        # nombres cortos: es un mensaje de celular

    propio = mis.first()
    Partido.objects.filter(pk=propio.pk).update(estado=Partido.Estado.FINALIZADO)
    ajeno = Partido.objects.exclude(pk__in=mis.values("pk")).first()
    Resultado.objects.create(partido=propio, goles_local=2, goles_visitante=1)
    Resultado.objects.create(partido=ajeno, goles_local=5, goles_visitante=5)
    res = _entrante(http, "59170000043", "resultados").json()["respuesta"]
    assert f"{propio.equipo_local.nombre} 2 - 1 {propio.equipo_visitante.nombre}" in res and "5 - 5" not in res


def test_sin_partidos_responde_con_naturalidad(n8n, http):
    con_whatsapp(numero="59170000044")
    assert "No hay partidos" in _entrante(http, "59170000044", "partidos").json()["respuesta"]
    assert "no hay resultados" in _entrante(http, "59170000044", "resultados").json()["respuesta"].lower()


def test_baja_desactiva_el_consentimiento_y_queda_en_bitacora(n8n, http):
    u = con_whatsapp(numero="59170000045")
    r = _entrante(http, "59170000045", " BAJA ").json()
    assert r["intencion"] == "baja"
    u.refresh_from_db()
    assert u.acepta_whatsapp is False and u.whatsapp == "59170000045"
    assert notificar_usuarios([u], "T", "M")["whatsapp"] == 0                      # ya no recibe avisos
    assert Bitacora.objects.filter(usuario=u, modulo="integraciones").exists()
    assert _entrante(http, "59170000045", "partidos").json()["intencion"] == "no_registrado"


def test_un_simple_no_no_da_de_baja(n8n, http):
    u = con_whatsapp(numero="59170000046")
    assert _entrante(http, "59170000046", "no").json()["intencion"] == "desconocido"
    u.refresh_from_db()
    assert u.acepta_whatsapp is True


def test_limite_de_mensajes_por_numero(n8n, http):
    con_whatsapp(numero="59170000047")
    codigos = [_entrante(http, "59170000047", "ayuda").status_code for _ in range(22)]
    assert codigos[:20] == [200] * 20 and codigos[20:] == [429, 429]


def test_numero_invalido_en_el_mensaje_da_400(n8n, http):
    assert _entrante(http, "abc", "hola").status_code == 400


def test_limpieza_de_texto_entrante():
    assert entrante._limpio("  ÑANDÚ   Baja ") == "nandu baja"
    assert len(entrante._limpio("x" * 1000)) == entrante.MAX_TEXTO
