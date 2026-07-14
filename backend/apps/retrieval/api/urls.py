from rest_framework.routers import DefaultRouter
from .views import RetrievalIndexJobViewSet, RetrievalReadinessViewSet

router = DefaultRouter()
router.register("readiness", RetrievalReadinessViewSet, basename="retrieval-readiness")
router.register("index-jobs", RetrievalIndexJobViewSet, basename="retrieval-index-job")
urlpatterns = router.urls

