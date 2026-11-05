from django.urls import path
from .views import ReportePDFView, ReporteExcelView
from .equipo_jugador import (
    ReporteEquipoView, ReporteEquipoExcelView, ReporteJugadorView, ReporteJugadorExcelView, ReporteFacultadView, ReporteFacultadExcelView, EstadisticasFacultadView,
)

urlpatterns = [
    path("campeonato/<int:campeonato_id>/pdf/",   ReportePDFView.as_view(),   name="reporte-pdf"),
    path("campeonato/<int:campeonato_id>/excel/",  ReporteExcelView.as_view(), name="reporte-excel"),
    path("equipo/<int:equipo_id>/pdf/",            ReporteEquipoView.as_view(),       name="reporte-equipo-pdf"),
    path("equipo/<int:equipo_id>/excel/",          ReporteEquipoExcelView.as_view(),  name="reporte-equipo-excel"),
    path("jugador/<int:jugador_id>/pdf/",          ReporteJugadorView.as_view(),      name="reporte-jugador-pdf"),
    path("jugador/<int:jugador_id>/excel/",        ReporteJugadorExcelView.as_view(), name="reporte-jugador-excel"),
    path("facultad/<int:facultad_id>/",            EstadisticasFacultadView.as_view(),   name="estadisticas-facultad"),
    path("facultad/<int:facultad_id>/pdf/",        ReporteFacultadView.as_view(),        name="reporte-facultad-pdf"),
    path("facultad/<int:facultad_id>/excel/",      ReporteFacultadExcelView.as_view(),   name="reporte-facultad-excel"),
]
