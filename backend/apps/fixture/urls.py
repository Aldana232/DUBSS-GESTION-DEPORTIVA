from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PartidoViewSet, GenerarFixtureView, TablaPosicionesView, EstadisticasView, CalidadFixtureView
from .planilla import PaquetePlanillaView

router = DefaultRouter()
router.register(r"partidos", PartidoViewSet, basename="partido")

urlpatterns = [
    path("", include(router.urls)),
    path("generar/",          GenerarFixtureView.as_view(),   name="fixture-generar"),
    path("tabla-posiciones/", TablaPosicionesView.as_view(),  name="fixture-tabla"),
    path("calidad/",          CalidadFixtureView.as_view(),   name="fixture-calidad"),
    path("estadisticas/",     EstadisticasView.as_view(),     name="fixture-estadisticas"),
    path("planilla/paquete/", PaquetePlanillaView.as_view(),  name="fixture-planilla-paquete"),
]
