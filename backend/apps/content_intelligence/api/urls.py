from rest_framework.routers import DefaultRouter

from apps.content_intelligence.api.views import ContentImportJobViewSet

router = DefaultRouter()
router.register("import-jobs", ContentImportJobViewSet, basename="content-import-job")

urlpatterns = router.urls
