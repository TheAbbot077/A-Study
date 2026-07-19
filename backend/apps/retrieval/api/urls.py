from rest_framework.routers import DefaultRouter
from .views import RetrievalIndexJobViewSet, RetrievalReadinessViewSet, RetrievalSynchronizationRunViewSet

router = DefaultRouter()
router.register("readiness", RetrievalReadinessViewSet, basename="retrieval-readiness")
router.register("index-jobs", RetrievalIndexJobViewSet, basename="retrieval-index-job")
router.register("synchronization-runs", RetrievalSynchronizationRunViewSet, basename="retrieval-synchronization-run")
urlpatterns = router.urls
