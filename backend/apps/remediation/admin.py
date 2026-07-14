from django.contrib import admin

from apps.remediation.domain.models import (
    RemediationActivity,
    RemediationAttempt,
    RemediationOutcome,
    RemediationPlan,
    RemediationRecommendation,
)


READONLY_FIELDS = ("id", "created_at", "updated_at")


class RemediationModelAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RemediationPlan)
class RemediationPlanAdmin(RemediationModelAdmin):
    list_display = ("learner", "content_concept", "status", "created_at", "updated_at")
    list_filter = ("status", "content_concept", "created_at", "updated_at")
    ordering = ("-created_at",)
    list_select_related = ("learner", "content_concept")
    search_fields = (
        "learner__email",
        "content_concept__title",
        "content_concept__content_section__learning_resource__title",
        "rationale",
    )
    readonly_fields = READONLY_FIELDS + ("started_at", "completed_at", "escalated_at", "cancelled_at", "closed_at")


@admin.register(RemediationRecommendation)
class RemediationRecommendationAdmin(RemediationModelAdmin):
    list_display = ("title", "plan", "recommendation_type", "priority", "created_at")
    list_filter = ("recommendation_type", "priority", "created_at")
    ordering = ("priority", "created_at")
    list_select_related = ("plan",)
    search_fields = ("title", "rationale", "plan__learner__email", "plan__content_concept__title")
    readonly_fields = READONLY_FIELDS


@admin.register(RemediationActivity)
class RemediationActivityAdmin(RemediationModelAdmin):
    list_display = ("title", "plan", "activity_type", "status", "resource", "created_at")
    list_filter = ("activity_type", "status", "resource", "created_at")
    ordering = ("created_at",)
    list_select_related = ("plan", "resource")
    search_fields = ("title", "instructions", "plan__learner__email", "plan__content_concept__title", "resource__title")
    readonly_fields = READONLY_FIELDS


@admin.register(RemediationAttempt)
class RemediationAttemptAdmin(RemediationModelAdmin):
    list_display = ("activity", "learner", "status", "started_at", "completed_at")
    list_filter = ("status", "started_at", "completed_at")
    ordering = ("-created_at",)
    list_select_related = ("activity", "learner")
    search_fields = ("learner__email", "activity__title")
    readonly_fields = READONLY_FIELDS


@admin.register(RemediationOutcome)
class RemediationOutcomeAdmin(RemediationModelAdmin):
    list_display = ("plan", "activity", "outcome", "recorded_at")
    list_filter = ("outcome", "recorded_at")
    ordering = ("-recorded_at",)
    list_select_related = ("plan", "activity")
    search_fields = ("plan__learner__email", "plan__content_concept__title", "activity__title", "notes")
    readonly_fields = ("id", "created_at")
