from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InstalacionViewSet,
    CanchaViewSet,
    BloqueoViewSet,
    HorarioCanchaViewSet,
)

router = DefaultRouter()
router.register(r"instalaciones", InstalacionViewSet, basename="instalacion")
router.register(r"canchas",       CanchaViewSet,      basename="cancha")
router.register(r"bloqueos",      BloqueoViewSet,     basename="bloqueo")
router.register(r"horarios",      HorarioCanchaViewSet, basename="horario-cancha")

urlpatterns = [path("", include(router.urls))]
