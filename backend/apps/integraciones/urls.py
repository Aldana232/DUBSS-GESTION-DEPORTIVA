from django.urls import path

from .views import EstadoView, MensajeEntranteView, PruebaView

urlpatterns = [
    path("estado/", EstadoView.as_view(), name="integraciones-estado"),
    path("prueba/", PruebaView.as_view(), name="integraciones-prueba"),
    path("whatsapp/mensaje/", MensajeEntranteView.as_view(), name="integraciones-whatsapp-mensaje"),
]
