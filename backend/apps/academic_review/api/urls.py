from rest_framework.routers import DefaultRouter

from apps.academic_review.api.views import AcademicPopulationRunViewSet, ApprovedProposalProjectionViewSet, ProposalReviewSessionViewSet

router = DefaultRouter()
router.register("sessions", ProposalReviewSessionViewSet, basename="academic-review-session")
router.register("projections", ApprovedProposalProjectionViewSet, basename="approved-proposal-projection")
router.register("population-runs", AcademicPopulationRunViewSet, basename="academic-population-run")
urlpatterns = router.urls
