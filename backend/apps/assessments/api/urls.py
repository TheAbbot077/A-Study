from rest_framework.routers import DefaultRouter

from apps.assessments.api.views import MasteryCheckViewSet

router = DefaultRouter()
router.register("mastery-check", MasteryCheckViewSet, basename="assessment-mastery-check")

urlpatterns = router.urls
