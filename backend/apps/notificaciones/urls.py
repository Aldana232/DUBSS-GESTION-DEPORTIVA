from django.urls import path
from .views import CanalesView, EnviarNotificacionView

urlpatterns = [
    path("enviar/",  EnviarNotificacionView.as_view(), name="notificacion-enviar"),
    path("canales/", CanalesView.as_view(),            name="notificacion-canales"),
]
