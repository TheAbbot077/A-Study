from rest_framework.routers import DefaultRouter

from apps.assessments.api.views import AssessmentExperienceViewSet, MasteryCheckViewSet

router = DefaultRouter()
router.register("mastery-check", MasteryCheckViewSet, basename="assessment-mastery-check")
router.register("experiences", AssessmentExperienceViewSet, basename="assessment-experience")

urlpatterns = router.urls
