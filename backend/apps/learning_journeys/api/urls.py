from rest_framework.routers import DefaultRouter

from .views import LearningJourneyViewSet

router = DefaultRouter()
router.register("", LearningJourneyViewSet, basename="learning-journey")

urlpatterns = router.urls
