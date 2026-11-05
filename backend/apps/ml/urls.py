from django.urls import path
from .views import (
    ModeloAsignacionView,
    TableroPrediccionesView,
    PrediccionPartidoView,
    RiesgoClimaticoView,
    PrediccionAsistenciaView,
    RecomendacionesView,
    EntrenarModeloView,
)
from .views_analisis import AtipicosView, CabezasDeSerieView, RevisarAtipicoView

urlpatterns = [
    # CU14
    path("tablero/",                              TableroPrediccionesView.as_view(),  name="ml-tablero"),
    # CU15
    path("riesgo-climatico/<int:partido_id>/",    RiesgoClimaticoView.as_view(),      name="ml-riesgo"),
    # CU16
    path("prediccion-partido/<int:partido_id>/",  PrediccionPartidoView.as_view(),    name="ml-prediccion"),
    # CU18
    path("recomendaciones/",                      RecomendacionesView.as_view(),      name="ml-recomendaciones"),
    # CU20
    path("asistencia/<int:partido_id>/",          PrediccionAsistenciaView.as_view(), name="ml-asistencia"),
    # Entrenamiento
    path("asignacion/",                           ModeloAsignacionView.as_view(),     name="ml-asignacion"),
    path("entrenar/",                             EntrenarModeloView.as_view(),       name="ml-entrenar"),
    # F7-07 / F7-08
    path("cabezas-de-serie/",                     CabezasDeSerieView.as_view(),       name="ml-cabezas-de-serie"),
    path("atipicos/",                             AtipicosView.as_view(),             name="ml-atipicos"),
    path("atipicos/<int:pk>/revisar/",            RevisarAtipicoView.as_view(),       name="ml-atipico-revisar"),
]
