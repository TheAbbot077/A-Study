from rest_framework.routers import DefaultRouter

from apps.academic.api.views import (
    ContentConceptViewSet,
    ContentSectionViewSet,
    CurriculumUnitViewSet,
    CurriculumViewSet,
    LearningResourceViewSet,
    ResourceIngestionJobViewSet,
    SubjectViewSet,
)

router = DefaultRouter()
router.register("subjects", SubjectViewSet, basename="academic-subject")
router.register("curricula", CurriculumViewSet, basename="academic-curriculum")
router.register("curriculum-units", CurriculumUnitViewSet, basename="academic-curriculum-unit")
router.register("learning-resources", LearningResourceViewSet, basename="academic-learning-resource")
router.register("content-sections", ContentSectionViewSet, basename="academic-content-section")
router.register("content-concepts", ContentConceptViewSet, basename="academic-content-concept")
router.register("ingestion-jobs", ResourceIngestionJobViewSet, basename="academic-ingestion-job")

urlpatterns = router.urls
