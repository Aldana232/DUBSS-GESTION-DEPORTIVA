from django.urls import path

from .views import BitacoraListView


urlpatterns = [
    path("bitacora/", BitacoraListView.as_view(), name="auditoria-bitacora"),
]
