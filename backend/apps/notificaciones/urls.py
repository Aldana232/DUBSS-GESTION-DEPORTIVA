from django.urls import path
from .views import (
    CanalesView, EnviarNotificacionView, LeerNotificacionView, LeerTodasView, MisNotificacionesView,
    ResumenNotificacionesView,
)

urlpatterns = [
    path("enviar/",  EnviarNotificacionView.as_view(), name="notificacion-enviar"),
    path("canales/", CanalesView.as_view(),            name="notificacion-canales"),
    path("mis/",                    MisNotificacionesView.as_view(),    name="notificacion-mis"),
    path("mis/resumen/",            ResumenNotificacionesView.as_view(), name="notificacion-resumen"),
    path("mis/leer-todas/",         LeerTodasView.as_view(),            name="notificacion-leer-todas"),
    path("mis/<int:pk>/leer/",      LeerNotificacionView.as_view(),     name="notificacion-leer"),
]
