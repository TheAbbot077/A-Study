from rest_framework.routers import DefaultRouter

from apps.assessment_review.api.views import (
    AssessmentReviewAnalyticsViewSet,
    AssessmentReviewViewSet,
    DifficultyCalibrationViewSet,
    QuestionReviewViewSet,
    ReviewerAssignmentViewSet,
)

router = DefaultRouter()
router.register("assessment-reviews", AssessmentReviewViewSet, basename="assessment-review")
router.register("question-reviews", QuestionReviewViewSet, basename="question-review")
router.register("reviewer-assignments", ReviewerAssignmentViewSet, basename="reviewer-assignment")
router.register("calibrations", DifficultyCalibrationViewSet, basename="difficulty-calibration")
router.register("analytics", AssessmentReviewAnalyticsViewSet, basename="assessment-review-analytics")

urlpatterns = router.urls
