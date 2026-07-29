from __future__ import annotations

from django.contrib import admin, messages

from .application.institutional_services import InstitutionalCompletionService, InstitutionalInterventionService
from .application.services import LearningJourneyLifecycleService, SynchronizeLearningJourneyService
from .domain.models import (
    InstitutionalInterventionRecommendation,
    InstitutionalLearningAssignment,
    LearningCompetencyProgress,
    LearningCompetencyProgressHistory,
    LearningJourney,
    LearningJourneyActionReceipt,
    LearningJourneyCapabilityReferences,
    LearningJourneySourceBinding,
    LearningJourneySubjectBinding,
)


class LearningJourneySourceBindingInline(admin.TabularInline):
    model = LearningJourneySourceBinding
    extra = 0
    can_delete = False
    readonly_fields = [field.name for field in LearningJourneySourceBinding._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


class LearningJourneySubjectBindingInline(admin.TabularInline):
    model = LearningJourneySubjectBinding
    extra = 0
    can_delete = False
    readonly_fields = [field.name for field in LearningJourneySubjectBinding._meta.fields]

    def has_add_permission(self, request, obj=None):
        return False


class LearningJourneyActionReceiptInline(admin.TabularInline):
    model = LearningJourneyActionReceipt
    extra = 0
    can_delete = False
    readonly_fields = [field.name for field in LearningJourneyActionReceipt._meta.fields]
    fields = ("id", "action_code", "actor", "status", "source_capability", "failure_code", "started_at", "completed_at")

    def has_add_permission(self, request, obj=None):
        return False


class LearningCompetencyProgressInline(admin.TabularInline):
    model = LearningCompetencyProgress
    extra = 0
    can_delete = False
    readonly_fields = [field.name for field in LearningCompetencyProgress._meta.fields]
    fields = ("id", "competency", "state", "unlock_state", "latest_mastery_decision", "last_progressed_at", "updated_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LearningJourney)
class LearningJourneyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "learner",
        "journey_type",
        "institution",
        "status",
        "status_reason_code",
        "current_step_code",
        "last_synchronized_at",
        "updated_at",
    )
    list_filter = ("journey_type", "status", "status_reason_code")
    search_fields = ("id", "learner__email", "institution__name")
    readonly_fields = [field.name for field in LearningJourney._meta.fields]
    inlines = [
        LearningJourneySourceBindingInline,
        LearningJourneySubjectBindingInline,
        LearningJourneyActionReceiptInline,
        LearningCompetencyProgressInline,
    ]
    actions = ["synchronize_selected_journeys", "pause_selected_journeys", "resume_selected_journeys", "archive_selected_journeys"]

    def has_add_permission(self, request):
        return False

    def synchronize_selected_journeys(self, request, queryset):
        service = SynchronizeLearningJourneyService()
        success = 0
        for journey in queryset:
            try:
                service.execute(journey_id=journey.id, actor=request.user)
                success += 1
            except Exception as exc:  # pragma: no cover - admin feedback path
                self.message_user(request, f"{journey.id}: {exc}", level=messages.ERROR)
        self.message_user(request, f"Synchronized {success} learning journey(s).", level=messages.SUCCESS)

    synchronize_selected_journeys.short_description = "Synchronize selected journeys"

    def pause_selected_journeys(self, request, queryset):
        self._lifecycle_action(request, queryset, "pause", "Paused")

    pause_selected_journeys.short_description = "Pause selected journeys"

    def resume_selected_journeys(self, request, queryset):
        self._lifecycle_action(request, queryset, "resume", "Resumed")

    resume_selected_journeys.short_description = "Resume selected journeys"

    def archive_selected_journeys(self, request, queryset):
        self._lifecycle_action(request, queryset, "archive", "Archived")

    archive_selected_journeys.short_description = "Archive eligible journeys"

    def _lifecycle_action(self, request, queryset, command: str, label: str):
        service = LearningJourneyLifecycleService()
        success = 0
        for journey in queryset:
            try:
                getattr(service, command)(journey_id=journey.id, actor=request.user, expected_version=journey.version)
                success += 1
            except Exception as exc:  # pragma: no cover - admin feedback path
                self.message_user(request, f"{journey.id}: {exc}", level=messages.ERROR)
        self.message_user(request, f"{label} {success} learning journey(s).", level=messages.SUCCESS)


@admin.register(LearningJourneySourceBinding)
class LearningJourneySourceBindingAdmin(admin.ModelAdmin):
    list_display = ("id", "journey", "source_type", "source_id", "source_version", "bound_at")
    list_filter = ("source_type",)
    readonly_fields = [field.name for field in LearningJourneySourceBinding._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(LearningJourneySubjectBinding)
class LearningJourneySubjectBindingAdmin(admin.ModelAdmin):
    list_display = ("id", "journey", "subject", "curriculum_reference", "binding_source", "status", "bound_at", "superseded_at")
    list_filter = ("binding_source", "status")
    readonly_fields = [field.name for field in LearningJourneySubjectBinding._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(LearningJourneyCapabilityReferences)
class LearningJourneyCapabilityReferencesAdmin(admin.ModelAdmin):
    list_display = ("id", "journey", "intent_id", "diagnostic_id", "bridge_plan_id", "teaching_preparation_id", "updated_at")
    readonly_fields = [field.name for field in LearningJourneyCapabilityReferences._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(LearningJourneyActionReceipt)
class LearningJourneyActionReceiptAdmin(admin.ModelAdmin):
    list_display = ("id", "journey", "action_code", "actor", "status", "source_capability", "failure_code", "started_at", "completed_at")
    list_filter = ("action_code", "status", "source_capability")
    search_fields = ("id", "journey__id", "actor__email", "idempotency_key", "failure_code")
    readonly_fields = [field.name for field in LearningJourneyActionReceipt._meta.fields]

    def has_add_permission(self, request):
        return False


@admin.register(LearningCompetencyProgress)
class LearningCompetencyProgressAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "journey",
        "competency",
        "state",
        "unlock_state",
        "latest_mastery_decision",
        "last_progressed_at",
        "updated_at",
    )
    list_filter = ("state", "unlock_state")
    search_fields = ("id", "journey__id", "competency__title", "competency__stable_key")
    readonly_fields = [field.name for field in LearningCompetencyProgress._meta.fields]
    actions = ["synchronize_progress_projection"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def synchronize_progress_projection(self, request, queryset):
        service = SynchronizeLearningJourneyService()
        success = 0
        journey_ids = set(queryset.values_list("journey_id", flat=True))
        for journey_id in journey_ids:
            try:
                service.execute(journey_id=journey_id, actor=request.user)
                success += 1
            except Exception as exc:  # pragma: no cover - admin feedback path
                self.message_user(request, f"{journey_id}: {exc}", level=messages.ERROR)
        self.message_user(request, f"Synchronized {success} journey projection(s).", level=messages.SUCCESS)

    synchronize_progress_projection.short_description = "Synchronize progression projection"


@admin.register(LearningCompetencyProgressHistory)
class LearningCompetencyProgressHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "journey", "competency", "old_state", "new_state", "reason", "actor", "created_at")
    list_filter = ("new_state", "reason")
    search_fields = ("id", "journey__id", "competency__title", "competency__stable_key", "actor__email")
    readonly_fields = [field.name for field in LearningCompetencyProgressHistory._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(InstitutionalLearningAssignment)
class InstitutionalLearningAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "journey",
        "institution",
        "learner",
        "subject",
        "assignment_state",
        "completion_state",
        "updated_at",
    )
    list_filter = ("assignment_state", "completion_state", "acceptance_mode", "institution")
    search_fields = ("id", "journey__id", "learner__email", "institution__name", "programme_label", "course_label")
    readonly_fields = [field.name for field in InstitutionalLearningAssignment._meta.fields]
    actions = ["synchronize_journeys", "evaluate_completion", "generate_intervention_recommendations"]

    def has_add_permission(self, request):
        return False

    def synchronize_journeys(self, request, queryset):
        service = SynchronizeLearningJourneyService()
        success = 0
        for assignment in queryset:
            try:
                service.execute(journey_id=assignment.journey_id, actor=request.user)
                success += 1
            except Exception as exc:  # pragma: no cover - admin feedback path
                self.message_user(request, f"{assignment.id}: {exc}", level=messages.ERROR)
        self.message_user(request, f"Synchronized {success} institutional journey(s).", level=messages.SUCCESS)

    synchronize_journeys.short_description = "Synchronize journey"

    def evaluate_completion(self, request, queryset):
        service = InstitutionalCompletionService()
        success = 0
        for assignment in queryset:
            try:
                service.evaluate(journey_id=assignment.journey_id, actor=request.user)
                success += 1
            except Exception as exc:  # pragma: no cover - admin feedback path
                self.message_user(request, f"{assignment.id}: {exc}", level=messages.ERROR)
        self.message_user(request, f"Evaluated completion for {success} assignment(s).", level=messages.SUCCESS)

    evaluate_completion.short_description = "Evaluate completion"

    def generate_intervention_recommendations(self, request, queryset):
        service = InstitutionalInterventionService()
        success = 0
        for assignment in queryset:
            for progress in assignment.journey.competency_progress.all():
                if service.evaluate_for_progress(progress=progress, actor=request.user):
                    success += 1
        self.message_user(request, f"Generated or found {success} intervention recommendation(s).", level=messages.SUCCESS)

    generate_intervention_recommendations.short_description = "Generate intervention recommendations"


@admin.register(InstitutionalInterventionRecommendation)
class InstitutionalInterventionRecommendationAdmin(admin.ModelAdmin):
    list_display = ("id", "journey", "institution", "learner", "reason", "severity", "status", "created_at", "resolved_at")
    list_filter = ("reason", "severity", "status", "institution")
    search_fields = ("id", "journey__id", "learner__email", "institution__name", "recommended_action")
    readonly_fields = [field.name for field in InstitutionalInterventionRecommendation._meta.fields]
    actions = ["resolve_recommendations", "dismiss_recommendations"]

    def has_add_permission(self, request):
        return False

    def resolve_recommendations(self, request, queryset):
        self._resolve(request, queryset, "RESOLVED")

    resolve_recommendations.short_description = "Resolve recommendations"

    def dismiss_recommendations(self, request, queryset):
        self._resolve(request, queryset, "DISMISSED")

    dismiss_recommendations.short_description = "Dismiss recommendations"

    def _resolve(self, request, queryset, status: str):
        service = InstitutionalInterventionService()
        success = 0
        for recommendation in queryset:
            try:
                service.resolve(recommendation_id=recommendation.id, actor=request.user, status=status)
                success += 1
            except Exception as exc:  # pragma: no cover - admin feedback path
                self.message_user(request, f"{recommendation.id}: {exc}", level=messages.ERROR)
        self.message_user(request, f"{status.title()} {success} recommendation(s).", level=messages.SUCCESS)
