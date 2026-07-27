from rest_framework.routers import DefaultRouter

from .views import LearningIdentityProfileViewSet

router = DefaultRouter()
router.register("profiles", LearningIdentityProfileViewSet, basename="learning-identity-profile")

urlpatterns = router.urls
