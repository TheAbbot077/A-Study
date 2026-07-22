from rest_framework.routers import DefaultRouter

from apps.content_processing.api.views import ContentProcessingJobViewSet, TeachingReadinessEvaluationViewSet

router = DefaultRouter()
router.register("jobs", ContentProcessingJobViewSet, basename="content-processing-job")
router.register("teaching-readiness/evaluations", TeachingReadinessEvaluationViewSet, basename="teaching-readiness-evaluation")

urlpatterns = router.urls
