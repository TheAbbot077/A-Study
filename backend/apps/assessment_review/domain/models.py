import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.assessments.domain.models import Assessment, ItemBankEntry, ItemDifficulty
from apps.core.exceptions import LifecycleTransitionError


class ReviewStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_REVIEW = "pending_review", "Pending Review"
    IN_REVIEW = "in_review", "In Review"
    APPROVED = "approved", "Approved"
    NEEDS_REVISION = "needs_revision", "Needs Revision"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


class ReviewDecisionValue(models.TextChoices):
    APPROVED = "approved", "Approved"
    NEEDS_REVISION = "needs_revision", "Needs Revision"
    REJECTED = "rejected", "Rejected"
    ARCHIVED = "archived", "Archived"


class FindingSeverity(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class ReviewerAssignmentStatus(models.TextChoices):
    ASSIGNED = "assigned", "Assigned"
    REASSIGNED = "reassigned", "Reassigned"
    COMPLETED = "completed", "Completed"
    CANCELLED = "cancelled", "Cancelled"


class CalibrationDirection(models.TextChoices):
    EASIER_THAN_EXPECTED = "easier_than_expected", "Easier Than Expected"
    AS_EXPECTED = "as_expected", "As Expected"
    HARDER_THAN_EXPECTED = "harder_than_expected", "Harder Than Expected"
    INSUFFICIENT_DATA = "insufficient_data", "Insufficient Data"


class ReviewLifecycleMixin:
    VALID_TRANSITIONS = {
        ReviewStatus.DRAFT: {ReviewStatus.PENDING_REVIEW, ReviewStatus.ARCHIVED},
        ReviewStatus.PENDING_REVIEW: {ReviewStatus.IN_REVIEW, ReviewStatus.ARCHIVED},
        ReviewStatus.IN_REVIEW: {ReviewStatus.APPROVED, ReviewStatus.NEEDS_REVISION, ReviewStatus.REJECTED, ReviewStatus.ARCHIVED},
        ReviewStatus.NEEDS_REVISION: {ReviewStatus.PENDING_REVIEW, ReviewStatus.ARCHIVED},
        ReviewStatus.APPROVED: {ReviewStatus.ARCHIVED},
        ReviewStatus.REJECTED: {ReviewStatus.ARCHIVED},
        ReviewStatus.ARCHIVED: set(),
    }

    def transition_to(self, status: str) -> None:
        if status not in self.VALID_TRANSITIONS.get(self.status, set()):
            raise LifecycleTransitionError(f"Cannot transition review from {self.status} to {status}.")
        self.status = status
        if status == ReviewStatus.IN_REVIEW:
            self.started_at = self.started_at or timezone.now()
        if status in {ReviewStatus.APPROVED, ReviewStatus.NEEDS_REVISION, ReviewStatus.REJECTED, ReviewStatus.ARCHIVED}:
            self.completed_at = timezone.now()


class AssessmentReview(ReviewLifecycleMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="reviews")
    status = models.CharField(max_length=50, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="opened_assessment_reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_assessment_reviews")
    opened_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assessment_review"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["assessment"], name="assess_review_assess_idx"),
            models.Index(fields=["status"], name="assess_review_status_idx"),
            models.Index(fields=["reviewer"], name="assess_review_reviewer_idx"),
        ]


class QuestionReview(ReviewLifecycleMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_bank_entry = models.ForeignKey(ItemBankEntry, on_delete=models.CASCADE, related_name="question_reviews")
    status = models.CharField(max_length=50, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    opened_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="opened_question_reviews")
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_question_reviews")
    opened_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "question_review"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["item_bank_entry"], name="question_review_item_idx"),
            models.Index(fields=["status"], name="question_review_status_idx"),
            models.Index(fields=["reviewer"], name="question_review_reviewer_idx"),
        ]


class QualityFinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment_review = models.ForeignKey(AssessmentReview, on_delete=models.CASCADE, null=True, blank=True, related_name="findings")
    question_review = models.ForeignKey(QuestionReview, on_delete=models.CASCADE, null=True, blank=True, related_name="findings")
    finding_type = models.CharField(max_length=100)
    severity = models.CharField(max_length=50, choices=FindingSeverity.choices, default=FindingSeverity.MEDIUM)
    description = models.TextField()
    resolved = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "quality_finding"
        ordering = ["-created_at"]

    def clean(self) -> None:
        super().clean()
        linked_count = int(self.assessment_review is not None) + int(self.question_review is not None)
        if linked_count != 1:
            raise ValidationError("QualityFinding must be linked to exactly one review.")

    def resolve(self) -> None:
        self.resolved = True


class ReviewDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment_review = models.ForeignKey(AssessmentReview, on_delete=models.CASCADE, null=True, blank=True, related_name="decisions")
    question_review = models.ForeignKey(QuestionReview, on_delete=models.CASCADE, null=True, blank=True, related_name="decisions")
    decision = models.CharField(max_length=50, choices=ReviewDecisionValue.choices)
    rationale = models.TextField(blank=True)
    decided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assessment_review_decisions")
    metadata = models.JSONField(default=dict, blank=True)
    decided_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "review_decision"
        ordering = ["-decided_at"]

    def clean(self) -> None:
        super().clean()
        linked_count = int(self.assessment_review is not None) + int(self.question_review is not None)
        if linked_count != 1:
            raise ValidationError("ReviewDecision must be linked to exactly one review.")


class DifficultyCalibration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, null=True, blank=True, related_name="difficulty_calibrations")
    item_bank_entry = models.ForeignKey(ItemBankEntry, on_delete=models.CASCADE, null=True, blank=True, related_name="difficulty_calibrations")
    expected_difficulty = models.CharField(max_length=50, choices=ItemDifficulty.choices, default=ItemDifficulty.UNKNOWN)
    observed_success_rate = models.FloatField(null=True, blank=True)
    sample_size = models.PositiveIntegerField(default=0)
    calibrated_difficulty = models.CharField(max_length=50, choices=ItemDifficulty.choices, default=ItemDifficulty.UNKNOWN)
    direction = models.CharField(max_length=50, choices=CalibrationDirection.choices, default=CalibrationDirection.INSUFFICIENT_DATA)
    calibration_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "difficulty_calibration"
        ordering = ["-created_at"]


class ReviewerAssignment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reviewer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_review_assignments")
    assessment_review = models.ForeignKey(AssessmentReview, on_delete=models.CASCADE, null=True, blank=True, related_name="assignments")
    question_review = models.ForeignKey(QuestionReview, on_delete=models.CASCADE, null=True, blank=True, related_name="assignments")
    status = models.CharField(max_length=50, choices=ReviewerAssignmentStatus.choices, default=ReviewerAssignmentStatus.ASSIGNED)
    assigned_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviewer_assignment"
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["reviewer"], name="review_assign_reviewer_idx"),
            models.Index(fields=["status"], name="review_assign_status_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        linked_count = int(self.assessment_review is not None) + int(self.question_review is not None)
        if linked_count != 1:
            raise ValidationError("ReviewerAssignment must target exactly one review.")

    def reassign(self, reviewer) -> None:
        self.reviewer = reviewer
        self.status = ReviewerAssignmentStatus.REASSIGNED
        self.assigned_at = timezone.now()

    def complete(self) -> None:
        self.status = ReviewerAssignmentStatus.COMPLETED
        self.completed_at = timezone.now()


__all__ = [
    "AssessmentReview",
    "QuestionReview",
    "DifficultyCalibration",
    "QualityFinding",
    "ReviewDecision",
    "ReviewerAssignment",
    "ReviewStatus",
    "ReviewDecisionValue",
    "FindingSeverity",
    "ReviewerAssignmentStatus",
    "CalibrationDirection",
]
