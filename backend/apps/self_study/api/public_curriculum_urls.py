from rest_framework.routers import DefaultRouter

from .curriculum_views import PublicCurriculumViewSet

router = DefaultRouter()
router.register("", PublicCurriculumViewSet, basename="public-curriculum")

urlpatterns = router.urls
