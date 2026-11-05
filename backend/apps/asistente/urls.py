from django.urls import path

from .views import EjecutarView, EstadoAsistenteView, InterpretarView, TranscribirView

urlpatterns = [
    path("estado/",      EstadoAsistenteView.as_view(), name="asistente-estado"),
    path("transcribir/", TranscribirView.as_view(),     name="asistente-transcribir"),
    path("interpretar/", InterpretarView.as_view(),     name="asistente-interpretar"),
    path("ejecutar/",    EjecutarView.as_view(),        name="asistente-ejecutar"),
]
