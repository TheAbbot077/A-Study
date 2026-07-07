from django.contrib import admin

from apps.academic.domain.models import (
    ContentConcept,
    ContentSection,
    Curriculum,
    CurriculumUnit,
    LearningResource,
    ResourceIngestionJob,
    Subject,
)
from apps.academic.services import (
    AcademicStructureService,
    ContentReviewService,
    CurriculumService,
    LearningResourceService,
    ManualAuthoringService,
)


READONLY_AUDIT_FIELDS = ("id", "created_at", "updated_at")


class AcademicModelAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


def _message_count(modeladmin, request, count: int, label: str) -> None:
    modeladmin.message_user(request, f"{count} {label}.")


@admin.register(Subject)
class SubjectAdmin(AcademicModelAdmin):
    list_display = ("code", "name", "institution", "is_active", "created_at", "updated_at")
    list_filter = ("institution", "is_active", "created_at", "updated_at")
    search_fields = ("code", "name", "description")
    readonly_fields = READONLY_AUDIT_FIELDS
    actions = ("archive_selected_subjects",)

    def save_model(self, request, obj, form, change):
        service = AcademicStructureService()
        if change:
            service.update_subject(obj, **form.cleaned_data)
            return

        created = service.create_subject(**form.cleaned_data)
        obj.id = created.id

    @admin.action(description="Archive selected subjects")
    def archive_selected_subjects(self, request, queryset):
        service = AcademicStructureService()
        for subject in queryset:
            service.archive_subject(subject)
        _message_count(self, request, queryset.count(), "subjects archived")


@admin.register(Curriculum)
class CurriculumAdmin(AcademicModelAdmin):
    list_display = ("name", "subject", "institution", "version", "is_active", "created_at", "updated_at")
    list_filter = ("institution", "subject", "is_active", "created_at", "updated_at")
    search_fields = ("name", "description", "subject__code", "subject__name")
    readonly_fields = READONLY_AUDIT_FIELDS
    actions = ("archive_selected_curricula",)

    def save_model(self, request, obj, form, change):
        service = CurriculumService()
        if change:
            service.update_curriculum(obj, **form.cleaned_data)
            return

        created = service.create_curriculum(**form.cleaned_data)
        obj.id = created.id

    @admin.action(description="Archive selected curricula")
    def archive_selected_curricula(self, request, queryset):
        service = CurriculumService()
        for curriculum in queryset:
            service.archive_curriculum(curriculum)
        _message_count(self, request, queryset.count(), "curricula archived")


@admin.register(CurriculumUnit)
class CurriculumUnitAdmin(AcademicModelAdmin):
    list_display = ("title", "curriculum", "sequence_number", "is_active", "created_at", "updated_at")
    list_filter = ("curriculum", "is_active", "created_at", "updated_at")
    search_fields = ("title", "description", "curriculum__name")
    readonly_fields = READONLY_AUDIT_FIELDS
    actions = ("archive_selected_curriculum_units",)

    def save_model(self, request, obj, form, change):
        service = CurriculumService()
        if change:
            service.update_unit(obj, **form.cleaned_data)
            return

        created = service.create_unit(**form.cleaned_data)
        obj.id = created.id

    @admin.action(description="Archive selected curriculum units")
    def archive_selected_curriculum_units(self, request, queryset):
        service = CurriculumService()
        for unit in queryset:
            service.archive_unit(unit)
        _message_count(self, request, queryset.count(), "curriculum units archived")


@admin.register(LearningResource)
class LearningResourceAdmin(AcademicModelAdmin):
    list_display = ("title", "subject", "curriculum", "curriculum_unit", "resource_type", "status", "created_at", "updated_at")
    list_filter = ("institution", "subject", "curriculum", "curriculum_unit", "resource_type", "status", "created_at", "updated_at")
    search_fields = ("title", "description", "source_label", "subject__code", "subject__name")
    readonly_fields = READONLY_AUDIT_FIELDS
    actions = ("archive_selected_learning_resources",)

    def save_model(self, request, obj, form, change):
        service = LearningResourceService()
        if change:
            service.update_resource(obj, **form.cleaned_data)
            return

        created = service.create_resource(**form.cleaned_data)
        obj.id = created.id

    @admin.action(description="Archive selected learning resources")
    def archive_selected_learning_resources(self, request, queryset):
        service = LearningResourceService()
        for resource in queryset:
            service.archive_resource(resource)
        _message_count(self, request, queryset.count(), "learning resources archived")


@admin.register(ContentSection)
class ContentSectionAdmin(AcademicModelAdmin):
    list_display = (
        "title",
        "learning_resource",
        "sequence_number",
        "review_status",
        "quality_status",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("learning_resource", "review_status", "quality_status", "is_active", "created_at", "updated_at")
    search_fields = ("title", "description", "learning_resource__title")
    readonly_fields = READONLY_AUDIT_FIELDS + ("approved_at",)
    actions = (
        "archive_selected_content_sections",
        "submit_selected_sections_for_review",
        "approve_selected_sections",
        "reject_selected_sections",
    )

    def save_model(self, request, obj, form, change):
        service = ManualAuthoringService()
        if change:
            service.update_section(obj, **form.cleaned_data)
            return

        created = service.create_section(**form.cleaned_data)
        obj.id = created.id

    @admin.action(description="Archive selected content sections")
    def archive_selected_content_sections(self, request, queryset):
        service = ManualAuthoringService()
        for section in queryset:
            service.archive_section(section)
        _message_count(self, request, queryset.count(), "content sections archived")

    @admin.action(description="Submit selected sections for review")
    def submit_selected_sections_for_review(self, request, queryset):
        service = ContentReviewService()
        for section in queryset:
            service.submit_section_for_review(section, submitted_by=request.user)
        _message_count(self, request, queryset.count(), "content sections submitted for review")

    @admin.action(description="Approve selected sections")
    def approve_selected_sections(self, request, queryset):
        service = ContentReviewService()
        for section in queryset:
            service.approve_section(section, approved_by=request.user)
        _message_count(self, request, queryset.count(), "content sections approved")

    @admin.action(description="Reject selected sections")
    def reject_selected_sections(self, request, queryset):
        service = ContentReviewService()
        for section in queryset:
            service.reject_section(section, rejected_by=request.user)
        _message_count(self, request, queryset.count(), "content sections rejected")


@admin.register(ContentConcept)
class ContentConceptAdmin(AcademicModelAdmin):
    list_display = (
        "title",
        "content_section",
        "sequence_number",
        "review_status",
        "quality_status",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("content_section", "review_status", "quality_status", "is_active", "created_at", "updated_at")
    search_fields = ("title", "description", "learning_objective", "content_section__title")
    readonly_fields = READONLY_AUDIT_FIELDS + ("approved_at",)
    actions = (
        "archive_selected_content_concepts",
        "submit_selected_concepts_for_review",
        "approve_selected_concepts",
        "reject_selected_concepts",
    )

    def save_model(self, request, obj, form, change):
        service = ManualAuthoringService()
        if change:
            service.update_concept(obj, **form.cleaned_data)
            return

        created = service.create_concept(**form.cleaned_data)
        obj.id = created.id

    @admin.action(description="Archive selected content concepts")
    def archive_selected_content_concepts(self, request, queryset):
        service = ManualAuthoringService()
        for concept in queryset:
            service.archive_concept(concept)
        _message_count(self, request, queryset.count(), "content concepts archived")

    @admin.action(description="Submit selected concepts for review")
    def submit_selected_concepts_for_review(self, request, queryset):
        service = ContentReviewService()
        for concept in queryset:
            service.submit_concept_for_review(concept, submitted_by=request.user)
        _message_count(self, request, queryset.count(), "content concepts submitted for review")

    @admin.action(description="Approve selected concepts")
    def approve_selected_concepts(self, request, queryset):
        service = ContentReviewService()
        for concept in queryset:
            service.approve_concept(concept, approved_by=request.user)
        _message_count(self, request, queryset.count(), "content concepts approved")

    @admin.action(description="Reject selected concepts")
    def reject_selected_concepts(self, request, queryset):
        service = ContentReviewService()
        for concept in queryset:
            service.reject_concept(concept, rejected_by=request.user)
        _message_count(self, request, queryset.count(), "content concepts rejected")


@admin.register(ResourceIngestionJob)
class ResourceIngestionJobAdmin(AcademicModelAdmin):
    list_display = ("learning_resource", "status", "source_type", "requested_by", "started_at", "completed_at", "created_at", "updated_at")
    list_filter = ("status", "source_type", "learning_resource", "created_at", "updated_at")
    search_fields = ("learning_resource__title", "error_message")
    readonly_fields = READONLY_AUDIT_FIELDS + ("started_at", "completed_at")

    def has_add_permission(self, request):
        return False

    def save_model(self, request, obj, form, change):
        return None

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return tuple(field.name for field in self.model._meta.fields)
        return super().get_readonly_fields(request, obj)
