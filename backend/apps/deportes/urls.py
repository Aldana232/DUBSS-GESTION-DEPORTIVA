from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FacultadViewSet, RestriccionHorarioFacultadViewSet, DeporteViewSet, CategoriaViewSet,
    CampeonatoViewSet, EquipoViewSet, InscripcionViewSet, FichaJugadorViewSet,
)

router = DefaultRouter()
router.register(r"facultades", FacultadViewSet, basename="facultad")
router.register(
    r"restricciones-horario",
    RestriccionHorarioFacultadViewSet,
    basename="restriccion-horario",
)
router.register(r"deportes",    DeporteViewSet,      basename="deporte")
router.register(r"categorias",  CategoriaViewSet,    basename="categoria")
router.register(r"campeonatos", CampeonatoViewSet,   basename="campeonato")
router.register(r"equipos",     EquipoViewSet,       basename="equipo")
router.register(r"inscripciones", InscripcionViewSet, basename="inscripcion")
router.register(r"jugadores",   FichaJugadorViewSet, basename="jugador")

from .mi_ficha import MiFichaView

urlpatterns = [
    path("mi-ficha/", MiFichaView.as_view(), name="mi-ficha"),
    path("", include(router.urls)),
]
