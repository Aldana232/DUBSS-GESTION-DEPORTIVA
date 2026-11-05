from django.urls import path

from apps.agente import views

urlpatterns = [
    path("estado/", views.EstadoAgenteView.as_view(), name="agente-estado"),
    path("conversaciones/", views.ConversacionesView.as_view(), name="agente-conversaciones"),
    path("conversaciones/<int:pk>/", views.ConversacionDetalleView.as_view(), name="agente-conversacion"),
    path("mensajes/", views.MensajeView.as_view(), name="agente-mensaje"),
    path("acciones/<int:pk>/", views.AccionDetalleView.as_view(), name="agente-accion"),
    path("acciones/<int:pk>/confirmar/", views.ConfirmarAccionView.as_view(), name="agente-accion-confirmar"),
    path("acciones/<int:pk>/cancelar/", views.CancelarAccionView.as_view(), name="agente-accion-cancelar"),
]
