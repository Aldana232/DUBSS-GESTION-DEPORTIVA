from rest_framework.routers import DefaultRouter

from .views import QuejaViewSet

router = DefaultRouter()
router.register("quejas", QuejaViewSet, basename="queja")

urlpatterns = router.urls
