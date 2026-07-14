from rest_framework.routers import DefaultRouter

from apps.learning.api.views import PedagogicalSessionViewSet

router = DefaultRouter()
router.register("pedagogical-sessions", PedagogicalSessionViewSet, basename="learning-pedagogical-session")

urlpatterns = router.urls
