"""Configuración de producción: salud, superficie pública y ajustes detrás del proxy."""
import os
import subprocess
import sys

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


# ─── Endpoint de salud ────────────────────────────────────────────────────────

def test_salud_responde_sin_sesion_y_no_expone_datos_internos():
    r = Client().get("/api/health/")
    assert r.status_code == 200
    d = r.json()
    assert d["estado"] in ("ok", "degradado") and d["base_de_datos"] is True and set(d) == {"estado", "base_de_datos", "redis"}


def test_si_la_base_de_datos_cae_responde_503(monkeypatch):
    monkeypatch.setattr("config.health._base_de_datos", lambda: False)
    r = Client().get("/api/health/")
    assert r.status_code == 503 and r.json()["estado"] == "caido"


def test_si_solo_cae_redis_responde_200_degradado(monkeypatch):
    monkeypatch.setattr("config.health._redis", lambda: False)
    r = Client().get("/api/health/")
    assert r.status_code == 200 and r.json() == {"estado": "degradado", "base_de_datos": True, "redis": False}


# ─── Ajustes de producción (se cargan en un proceso aparte: no contaminan estas pruebas) ───

def _ajustes_de_produccion(**entorno) -> dict:
    base = {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings.production", "DJANGO_ALLOWED_HOSTS": "dubss.ejemplo.bo", **entorno}
    codigo = (
        "import json, django; django.setup(); from django.conf import settings as s;"
        "print(json.dumps({k: getattr(s, k) for k in ['DEBUG','SECURE_PROXY_SSL_HEADER','SECURE_SSL_REDIRECT','SESSION_COOKIE_SECURE',"
        "'CSRF_COOKIE_SECURE','SECURE_HSTS_SECONDS','API_DOCS_ENABLED','ADMIN_URL','X_FRAME_OPTIONS','ALLOWED_HOSTS','REST_FRAMEWORK']}, default=str))"
    )
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True, env=base, cwd=os.getcwd())
    assert r.returncode == 0, r.stderr[-800:]
    import json
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_produccion_evita_el_bucle_de_redireccion_https_y_endurece_las_cookies():
    s = _ajustes_de_produccion()
    assert s["DEBUG"] is False
    assert s["SECURE_PROXY_SSL_HEADER"] == ["HTTP_X_FORWARDED_PROTO", "https"]     # sin esto, SSL_REDIRECT haría un bucle
    assert s["SECURE_SSL_REDIRECT"] is False                                         # el redireccionamiento lo hace Caddy
    assert s["SESSION_COOKIE_SECURE"] is True and s["CSRF_COOKIE_SECURE"] is True
    assert s["SECURE_HSTS_SECONDS"] == 31536000 and s["X_FRAME_OPTIONS"] == "DENY"
    assert s["ALLOWED_HOSTS"] == ["dubss.ejemplo.bo"]


def test_produccion_apaga_la_documentacion_y_la_interfaz_navegable_de_la_api():
    s = _ajustes_de_produccion()
    assert s["API_DOCS_ENABLED"] is False
    assert s["REST_FRAMEWORK"]["DEFAULT_RENDERER_CLASSES"] == ["rest_framework.renderers.JSONRenderer"]
    assert _ajustes_de_produccion(API_DOCS_ENABLED="true")["API_DOCS_ENABLED"] is True


def test_produccion_permite_cambiar_la_ruta_del_admin_y_probar_por_http():
    s = _ajustes_de_produccion(ADMIN_URL="/panel-9f3c2a", USAR_HTTPS="false")
    assert s["ADMIN_URL"] == "panel-9f3c2a/"
    assert s["SESSION_COOKIE_SECURE"] is False and s["SECURE_HSTS_SECONDS"] == 0


def test_produccion_no_arranca_sin_hosts_permitidos():
    env = {k: v for k, v in os.environ.items() if k != "DJANGO_ALLOWED_HOSTS"}
    env["DJANGO_SETTINGS_MODULE"] = "config.settings.production"
    r = subprocess.run([sys.executable, "-c", "import django; django.setup()"], capture_output=True, text=True, env=env, cwd=os.getcwd())
    assert r.returncode != 0 and "DJANGO_ALLOWED_HOSTS" in r.stderr


# ─── Rutas según los interruptores ────────────────────────────────────────────

def test_en_desarrollo_la_documentacion_y_el_admin_existen():
    c = Client()
    assert c.get("/api/docs/").status_code == 200
    assert c.get("/api/schema/").status_code == 200
    assert c.get("/admin/login/").status_code == 200
