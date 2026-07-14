from django.contrib import admin

from apps.assessment_review.domain.models import (
    AssessmentReview,
    DifficultyCalibration,
    QualityFinding,
    QuestionReview,
    ReviewDecision,
    ReviewerAssignment,
)


READONLY_FIELDS = ("id", "created_at", "updated_at")


class AssessmentReviewModelAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AssessmentReview)
class AssessmentReviewAdmin(AssessmentReviewModelAdmin):
    list_display = ("assessment", "status", "reviewer", "opened_at", "completed_at")
    list_filter = ("status", "reviewer", "opened_at", "completed_at")
    ordering = ("-created_at",)
    list_select_related = ("assessment", "reviewer", "opened_by")
    search_fields = ("assessment__title", "assessment__content_concept__title", "reviewer__email")
    readonly_fields = READONLY_FIELDS + ("opened_at", "started_at", "completed_at")


@admin.register(QuestionReview)
class QuestionReviewAdmin(AssessmentReviewModelAdmin):
    list_display = ("item_bank_entry", "status", "reviewer", "opened_at", "completed_at")
    list_filter = ("status", "reviewer", "opened_at", "completed_at")
    ordering = ("-created_at",)
    list_select_related = ("item_bank_entry", "reviewer", "opened_by")
    search_fields = ("item_bank_entry__prompt", "item_bank_entry__content_concept__title", "reviewer__email")
    readonly_fields = READONLY_FIELDS + ("opened_at", "started_at", "completed_at")


@admin.register(QualityFinding)
class QualityFindingAdmin(AssessmentReviewModelAdmin):
    list_display = ("finding_type", "severity", "resolved", "assessment_review", "question_review", "created_at")
    list_filter = ("severity", "resolved", "created_at")
    ordering = ("-created_at",)
    list_select_related = ("assessment_review", "question_review")
    search_fields = ("finding_type", "description", "assessment_review__assessment__title", "question_review__item_bank_entry__prompt")
    readonly_fields = READONLY_FIELDS


@admin.register(ReviewDecision)
class ReviewDecisionAdmin(AssessmentReviewModelAdmin):
    list_display = ("decision", "assessment_review", "question_review", "decided_by", "decided_at")
    list_filter = ("decision", "decided_by", "decided_at")
    ordering = ("-decided_at",)
    list_select_related = ("assessment_review", "question_review", "decided_by")
    search_fields = ("rationale", "assessment_review__assessment__title", "question_review__item_bank_entry__prompt", "decided_by__email")
    readonly_fields = ("id", "decided_at", "created_at")


@admin.register(DifficultyCalibration)
class DifficultyCalibrationAdmin(AssessmentReviewModelAdmin):
    list_display = ("item_bank_entry", "assessment", "expected_difficulty", "calibrated_difficulty", "direction", "created_at")
    list_filter = ("expected_difficulty", "calibrated_difficulty", "direction", "created_at")
    ordering = ("-created_at",)
    list_select_related = ("item_bank_entry", "assessment")
    search_fields = ("item_bank_entry__prompt", "assessment__title", "calibration_reason")
    readonly_fields = ("id", "created_at")


@admin.register(ReviewerAssignment)
class ReviewerAssignmentAdmin(AssessmentReviewModelAdmin):
    list_display = ("reviewer", "assessment_review", "question_review", "status", "assigned_at", "completed_at")
    list_filter = ("reviewer", "status", "assigned_at", "completed_at")
    ordering = ("-assigned_at",)
    list_select_related = ("reviewer", "assessment_review", "question_review")
    search_fields = ("reviewer__email", "assessment_review__assessment__title", "question_review__item_bank_entry__prompt")
    readonly_fields = READONLY_FIELDS + ("assigned_at", "completed_at")
