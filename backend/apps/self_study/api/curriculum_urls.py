from rest_framework.routers import DefaultRouter

from .curriculum_views import (
    CurriculumAuthorityGovernanceViewSet,
    CurriculumReferenceGovernanceViewSet,
    CurriculumVersionGovernanceViewSet,
)

router = DefaultRouter()
router.register("authorities", CurriculumAuthorityGovernanceViewSet, basename="curriculum-authority")
router.register("curricula", CurriculumReferenceGovernanceViewSet, basename="curriculum-governance")
router.register("versions", CurriculumVersionGovernanceViewSet, basename="curriculum-version-governance")

urlpatterns = router.urls

