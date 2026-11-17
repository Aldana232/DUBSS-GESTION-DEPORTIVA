"""
config/settings/production.py
Configuración de PRODUCCIÓN: Django corre detrás de Caddy (que pone el HTTPS y redirige HTTP -> HTTPS).
Todo lo que cambia entre instalaciones viene de variables de entorno (ver deploy/.env.production.example).
"""
from .base import *  # noqa: F401,F403
import environ

env = environ.Env()

DEBUG = False

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")                         # obligatorio: sin él no arranca
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])      # ej.: https://dubss.ejemplo.bo

# ── Detrás del proxy ──────────────────────────────────────────────────────────
# Caddy envía X-Forwarded-Proto: sin esta línea Django cree que todo es http y, con SECURE_SSL_REDIRECT,
# redirige sin parar (bucle infinito).
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
# Caddy ya redirige HTTP -> HTTPS; Django no necesita repetirlo (y las comprobaciones internas de Docker van por http).
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)

# ── HTTPS ─────────────────────────────────────────────────────────────────────
# USAR_HTTPS=false solo para PROBAR en una PC por http://localhost. En un servidor real SIEMPRE true.
USAR_HTTPS = env.bool("USAR_HTTPS", default=True)
SESSION_COOKIE_SECURE = USAR_HTTPS
CSRF_COOKIE_SECURE = USAR_HTTPS
SECURE_HSTS_SECONDS = 31536000 if USAR_HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False      # no afectar a otros subdominios del mismo dominio
SECURE_HSTS_PRELOAD = False

# Avisos de «check --deploy» que son decisiones deliberadas, no olvidos:
#  W008: la redirección a HTTPS la hace Caddy.  W005/W021: HSTS sin subdominios ni lista «preload» a propósito
#  (afectarían a otros sitios del mismo dominio y es difícil de revertir).
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W008", "security.W021"]

# ── Cabeceras de seguridad ────────────────────────────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# ── API solo JSON (sin la interfaz navegable de DRF) y documentación apagada por defecto ──
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"]}  # noqa: F405
API_DOCS_ENABLED = env.bool("API_DOCS_ENABLED", default=False)

# ── Logging en JSON (a la salida estándar: lo recoge Docker) ──────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "json"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
