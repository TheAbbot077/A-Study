from rest_framework.routers import DefaultRouter

from apps.content_processing.api.views import ContentProcessingJobViewSet

router = DefaultRouter()
router.register("jobs", ContentProcessingJobViewSet, basename="content-processing-job")

urlpatterns = router.urls

