from __future__ import annotations

from django.contrib import admin, messages

from .application.services import LearningJourneyLifecycleService, SynchronizeLearningJourneyService
from .domain.models import (
    LearningJourney,
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
    inlines = [LearningJourneySourceBindingInline, LearningJourneySubjectBindingInline]
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
