from rest_framework.routers import DefaultRouter

from apps.storage.api.views import StoredFileViewSet

router = DefaultRouter()
router.register("files", StoredFileViewSet, basename="storage-file")

urlpatterns = router.urls
