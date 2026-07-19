from django.contrib import admin

from apps.academic_review.domain.models import (
    AcademicPopulationRun, ConceptPopulationMapping, SectionPopulationMapping,
)


class ImmutablePopulationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(AcademicPopulationRun)
class AcademicPopulationRunAdmin(ImmutablePopulationAdmin):
    list_display = ("id", "approved_projection", "resource", "subject", "requested_by", "status", "created_section_count", "created_concept_count", "failure_code", "created_at", "completed_at")
    list_filter = ("status", "subject", "resource", "failure_code", "created_at", "completed_at")
    search_fields = ("id", "approved_projection__id", "resource__id", "idempotency_key", "requested_by__email")


@admin.register(SectionPopulationMapping)
class SectionPopulationMappingAdmin(ImmutablePopulationAdmin):
    list_display = ("population_run", "approved_section", "academic_section_id", "outcome", "sequence_number", "populated_at")
    list_filter = ("outcome", "populated_at")
    search_fields = ("population_run__id", "approved_section__id", "academic_section_id", "stable_source_key")


@admin.register(ConceptPopulationMapping)
class ConceptPopulationMappingAdmin(ImmutablePopulationAdmin):
    list_display = ("population_run", "approved_concept", "academic_concept_id", "academic_section_id", "outcome", "sequence_number", "populated_at")
    list_filter = ("outcome", "populated_at")
    search_fields = ("population_run__id", "approved_concept__id", "academic_concept_id", "stable_source_key")
