from django.urls import path

from .views import AceptarView, EstadoView, HistorialView, VersionView

urlpatterns = [
    path("version/", VersionView.as_view(), name="legal-version"),
    path("estado/", EstadoView.as_view(), name="legal-estado"),
    path("aceptar/", AceptarView.as_view(), name="legal-aceptar"),
    path("historial/", HistorialView.as_view(), name="legal-historial"),
]
