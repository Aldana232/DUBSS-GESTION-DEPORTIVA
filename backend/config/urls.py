"""
config/urls.py
Rutas principales del proyecto DUBSS.
"""
from django.contrib import admin
from django.urls import path, include

from config.health import salud
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

# ─── Prefijo de API ───────────────────────────────────────────────────────────
API_V1 = "api/v1/"

urlpatterns = [
    # Salud del sistema (Docker y monitores)
    path("api/health/", salud, name="salud"),

    # Admin Django (la ruta sale de ADMIN_URL)
    path(settings.ADMIN_URL, admin.site.urls),

    # ── Módulos de la API ────────────────────────────────────────────────────
    path(API_V1 + "auth/",           include("apps.users.urls.auth_urls")),
    path(API_V1,                    include("apps.users.urls.root_urls")),
    path(API_V1 + "usuarios/",       include("apps.users.urls.user_urls")),
    path(API_V1 + "deportes/",       include("apps.deportes.urls")),
    path(API_V1 + "instalaciones/",  include("apps.instalaciones.urls")),
    path(API_V1 + "fixture/",        include("apps.fixture.urls")),
    path(API_V1 + "auditoria/",     include("apps.auditoria.urls")),
    path(API_V1 + "ml/",             include("apps.ml.urls")),
    path(API_V1 + "notificaciones/", include("apps.notificaciones.urls")),
    path(API_V1 + "reportes/",       include("apps.reportes.urls")),
    path(API_V1 + "quejas/",         include("apps.quejas.urls")),
    path(API_V1 + "asistente/",      include("apps.asistente.urls")),
    path(API_V1 + "agente/",         include("apps.agente.urls")),
    path(API_V1 + "integraciones/",  include("apps.integraciones.urls")),
    path(API_V1 + "legal/",          include("apps.legal.urls")),


]

# ── Esquema OpenAPI, Swagger y ReDoc (apagados en producción salvo API_DOCS_ENABLED=true) ──
if settings.API_DOCS_ENABLED:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(),                     name="schema"),
        path("api/docs/",   SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
        path("api/redoc/",  SpectacularRedocView.as_view(url_name="schema"),   name="redoc"),
    ]

# Archivos media en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    # Debug Toolbar
    import debug_toolbar
    urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
