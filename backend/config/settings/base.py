"""
config/settings/base.py
Configuración base compartida entre todos los entornos.
"""
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Lee variables desde .env
env = environ.Env()
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")

# ─── Aplicaciones ─────────────────────────────────────────────────────────────
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
]

LOCAL_APPS = [
    "apps.users",
    "apps.deportes",
    "apps.instalaciones",
    "apps.fixture",
    "apps.ml",
    "apps.auditoria",
    "apps.notificaciones",
    "apps.reportes",
    "apps.quejas",
    "apps.asistente",
    "apps.agente",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ─── Middleware ────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─── Base de datos ─────────────────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE":   "django.db.backends.postgresql",
        "NAME":     env("POSTGRES_DB"),
        "USER":     env("POSTGRES_USER"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST":     env("POSTGRES_HOST", default="db"),
        "PORT":     env("POSTGRES_PORT", default="5432"),
        "OPTIONS":  {"connect_timeout": 10},
    }
}

# ─── Auth / Password ──────────────────────────────────────────────────────────
AUTH_USER_MODEL = "users.Usuario"
LOGIN_MAX_INTENTOS = env.int("LOGIN_MAX_INTENTOS", default=5)
LOGIN_BLOQUEO_MINUTOS = env.int("LOGIN_BLOQUEO_MINUTOS", default=15)

# ─── Reglas deportivas (Fase 3) ───────────────────────────────────────────────
SANCION_PARTIDOS_ROJA = env.int("SANCION_PARTIDOS_ROJA", default=1)
AMARILLAS_PARA_SANCION = env.int("AMARILLAS_PARA_SANCION", default=3)
WALKOVER_GOLES_GANADOR = env.int("WALKOVER_GOLES_GANADOR", default=3)

# ─── Fixture asistido por ML (Fase 5b) ────────────────────────────────────────
FIXTURE_DESCANSO_MIN_HORAS = env.int("FIXTURE_DESCANSO_MIN_HORAS", default=24)
ML_FIXTURE_MAX_SEGUNDOS = env.float("ML_FIXTURE_MAX_SEGUNDOS", default=8.0)
ML_CANDIDATOS_POR_PARTIDO = env.int("ML_CANDIDATOS_POR_PARTIDO", default=40)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ─── Internacionalización ──────────────────────────────────────────────────────
LANGUAGE_CODE = "es-bo"
TIME_ZONE     = "America/La_Paz"
USE_I18N      = True
USE_TZ        = True

# ─── Archivos estáticos y media ───────────────────────────────────────────────
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL   = "/media/"
MEDIA_ROOT  = BASE_DIR / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── Django REST Framework ────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": env("LOGIN_THROTTLE_RATE", default="10/min"),
    },
    "EXCEPTION_HANDLER": "config.exception_handler.exception_handler",
    # 0 = conexión directa (desarrollo); 1 cuando hay un proxy delante (nginx en producción).
    "NUM_PROXIES": env.int("NUM_PROXIES", default=0),
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "config.pagination.PaginacionEstandar",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ─── JWT ─────────────────────────────────────────────────────────────────────
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(minutes=env.int("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", default=60)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_TOKEN_LIFETIME_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS":  True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD":     "id",
    "USER_ID_CLAIM":     "user_id",
}

# ─── Swagger (drf-spectacular) ────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE":       "DUBSS API",
    "DESCRIPTION": "Sistema de Gestión Deportiva DUBSS - UAGRM. API REST documentada con OpenAPI 3.0.",
    "VERSION":     "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "CONTACT": {"name": "Equipo DUBSS", "email": "dubss@uagrm.edu.bo"},
    "LICENSE": {"name": "MIT"},
    "TAGS": [
        {"name": "auth",           "description": "Autenticación y tokens JWT"},
        {"name": "usuarios",       "description": "Gestión de usuarios y perfiles"},
        {"name": "deportes",       "description": "Deportes, categorías y campeonatos"},
        {"name": "equipos",        "description": "Equipos y jugadores"},
        {"name": "instalaciones",  "description": "Canchas y horarios"},
        {"name": "fixture",        "description": "Generación y gestión de fixture"},
        {"name": "resultados",     "description": "Resultados e incidencias"},
        {"name": "ml",             "description": "Predicciones con Machine Learning"},
        {"name": "notificaciones", "description": "Envío de notificaciones"},
        {"name": "reportes",       "description": "Exportación de reportes"},
        {"name": "asistente",      "description": "Reportes por voz y órdenes en lenguaje natural"},
        {"name": "agente",         "description": "Agente del organizador: herramientas, propuestas y confirmación"},
    ],
}

# ─── CORS ─────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000"],
)
CORS_ALLOW_CREDENTIALS = True

# ─── Email ────────────────────────────────────────────────────────────────────
EMAIL_BACKEND      = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST         = env("EMAIL_HOST",          default="smtp.gmail.com")
EMAIL_PORT         = env.int("EMAIL_PORT",      default=587)
EMAIL_USE_TLS      = env.bool("EMAIL_USE_TLS",  default=True)
EMAIL_HOST_USER    = env("EMAIL_HOST_USER",     default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_TIMEOUT      = 10   # un servidor de correo caído no debe colgar el envío

# ─── Celery (tareas asíncronas) ───────────────────────────────────────────────
CELERY_BROKER_URL        = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND    = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_ACCEPT_CONTENT    = ["json"]
CELERY_TASK_SERIALIZER   = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE          = TIME_ZONE
CELERY_TASK_TIME_LIMIT   = 600           # ninguna tarea puede quedar colgada más de 10 minutos
CELERY_TASK_SOFT_TIME_LIMIT = 540
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# Tareas programadas (F6-03). Todas son idempotentes: repetirlas no duplica avisos ni datos.
from celery.schedules import crontab  # noqa: E402

CELERY_BEAT_SCHEDULE = {
    "resultados-atipicos": {
        "task": "ml.revisar_resultados_atipicos", "schedule": crontab(minute=20),
    },
    "purgar-claves-de-idempotencia": {
        "task": "fixture.purgar_operaciones_idempotentes", "schedule": crontab(hour=3, minute=30),
    },
    "expirar-acciones-del-agente": {
        "task": "agente.expirar_acciones", "schedule": crontab(minute="*/10"),
    },
    "recordatorios-de-partidos": {
        "task": "notificaciones.enviar_recordatorios", "schedule": crontab(minute="*/15"),
    },
    "actualizar-riesgo-climatico": {
        "task": "ml.actualizar_riesgo_climatico", "schedule": crontab(minute=5, hour="*/3"),
    },
    "reconstruir-historial-de-posiciones": {
        "task": "fixture.reconstruir_historial", "schedule": crontab(minute=30, hour=2),
    },
    "reentrenar-modelos": {
        "task": "ml.reentrenar_modelos", "schedule": crontab(minute=0, hour=3, day_of_week="sunday"),
    },
}

# ─── APIs externas ────────────────────────────────────────────────────────────
GROQ_API_KEY         = env("GROQ_API_KEY",         default="")
# Clima: Open-Meteo no necesita clave; solo las coordenadas del campus (Santa Cruz de la Sierra).
CLIMA_LATITUD  = env.float("CLIMA_LATITUD",  default=-17.7833)
CLIMA_LONGITUD = env.float("CLIMA_LONGITUD", default=-63.1821)

# Push (FCM HTTP v1): ruta del JSON de la cuenta de servicio de Firebase. Sin él, solo se envía correo.
FCM_CREDENTIALS_FILE = env("FCM_CREDENTIALS_FILE", default="")

# IA del asistente (F6-06). Groq ofrece Whisper (voz a texto) y Llama (interpretar órdenes) con plan gratuito.
LLM_PROVIDER = env("LLM_PROVIDER", default="groq")          # groq | ollama | reglas
LLM_MODEL    = env("LLM_MODEL", default="openai/gpt-oss-20b")
OLLAMA_URL   = env("OLLAMA_URL", default="http://host.docker.internal:11434")
STT_PROVIDER = env("STT_PROVIDER", default="groq")          # groq | ninguno
STT_MODEL    = env("STT_MODEL", default="whisper-large-v3-turbo")
ASISTENTE_AUDIO_MAX_MB = env.int("ASISTENTE_AUDIO_MAX_MB", default=10)

# F7-A — Agente del organizador (LLM con herramientas). Groq con un modelo que soporta function calling.
AGENTE_PROVIDER = env("AGENTE_PROVIDER", default="groq")
AGENTE_MODEL = env("AGENTE_MODEL", default="openai/gpt-oss-120b")
AGENTE_MAX_PASOS = env.int("AGENTE_MAX_PASOS", default=5)               # vueltas al LLM por petición
AGENTE_MAX_HERRAMIENTAS = env.int("AGENTE_MAX_HERRAMIENTAS", default=8)  # llamadas a herramientas por petición
AGENTE_TIMEOUT_SEG = env.int("AGENTE_TIMEOUT_SEG", default=60)           # tiempo total por petición
AGENTE_MENSAJES_HORA = env.int("AGENTE_MENSAJES_HORA", default=60)       # tope de mensajes por usuario y hora
AGENTE_ACCION_MINUTOS = env.int("AGENTE_ACCION_MINUTOS", default=30)     # vigencia de una acción pendiente
AGENTE_ANTELACION_HORAS = env.int("AGENTE_ANTELACION_HORAS", default=2)  # no se reprograma a menos de N horas
