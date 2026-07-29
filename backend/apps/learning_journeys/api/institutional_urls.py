from rest_framework.routers import DefaultRouter

from .institutional_views import InstitutionalLearningJourneyViewSet

router = DefaultRouter()
router.register("", InstitutionalLearningJourneyViewSet, basename="institutional-learning-journey")

urlpatterns = router.urls
