from django.urls import path

from apps.quejas.views import MisQuejasView
from ..views.user_views import MiEquipoView, MiUsuarioView


urlpatterns = [
    path("me/", MiUsuarioView.as_view(), name="usuario-me"),
    path("mi-equipo/", MiEquipoView.as_view(), name="usuario-mi-equipo"),
    path("mis-quejas/", MisQuejasView.as_view(), name="mis-quejas"),
]
