from django.contrib import admin

from apps.educational_organization.domain.models import (
    AcademicPeriod,
    AcademicUnit,
    ClassGroup,
    CourseOffering,
    EducationalOrganization,
    Programme,
    TeachingAssignment,
    UserCapability,
)


@admin.register(EducationalOrganization)
class EducationalOrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "organization_type", "status", "parent", "version", "archived_at"]
    list_filter = ["institution", "status", "organization_type"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]
    fieldsets = [
        ("Identity", {"fields": ["id", "institution", "parent"]}),
        ("Organization", {"fields": ["name", "slug", "organization_type", "status"]}),
        ("Metadata", {"fields": ["metadata", "version", "archived_at"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(AcademicUnit)
class AcademicUnitAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "educational_organization", "unit_type", "status", "version", "archived_at"]
    list_filter = ["institution", "educational_organization", "status", "unit_type"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]
    fieldsets = [
        ("Identity", {"fields": ["id", "institution", "educational_organization", "parent"]}),
        ("Unit", {"fields": ["name", "slug", "unit_type", "status"]}),
        ("Metadata", {"fields": ["metadata", "version", "archived_at"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "academic_unit", "qualification", "status", "version", "archived_at"]
    list_filter = ["institution", "educational_organization", "academic_unit", "status"]
    search_fields = ["name", "slug", "qualification"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]
    fieldsets = [
        ("Identity", {"fields": ["id", "institution", "educational_organization", "academic_unit"]}),
        ("Programme", {"fields": ["name", "slug", "qualification", "description", "status"]}),
        ("Metadata", {"fields": ["metadata", "version", "archived_at"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(AcademicPeriod)
class AcademicPeriodAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "educational_organization", "period_type", "status", "starts_at", "ends_at", "version", "archived_at"]
    list_filter = ["institution", "educational_organization", "status", "period_type"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]
    fieldsets = [
        ("Identity", {"fields": ["id", "institution", "educational_organization"]}),
        ("Period", {"fields": ["name", "slug", "period_type", "status", "starts_at", "ends_at"]}),
        ("Metadata", {"fields": ["metadata", "version", "archived_at"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(CourseOffering)
class CourseOfferingAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "programme", "academic_period", "subject", "status", "version", "archived_at"]
    list_filter = ["institution", "educational_organization", "programme", "academic_period", "status"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]
    fieldsets = [
        ("Identity", {"fields": ["id", "institution", "educational_organization", "academic_unit", "programme", "academic_period", "subject"]}),
        ("Offering", {"fields": ["name", "slug", "description", "status"]}),
        ("Metadata", {"fields": ["metadata", "version", "archived_at"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(ClassGroup)
class ClassGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "institution", "course_offering", "status", "version", "archived_at"]
    list_filter = ["institution", "educational_organization", "course_offering", "status"]
    search_fields = ["name", "slug"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]
    fieldsets = [
        ("Identity", {"fields": ["id", "institution", "educational_organization", "academic_unit", "course_offering"]}),
        ("Class Group", {"fields": ["name", "slug", "description", "status"]}),
        ("Metadata", {"fields": ["metadata", "version", "archived_at"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(TeachingAssignment)
class TeachingAssignmentAdmin(admin.ModelAdmin):
    list_display = ["teacher", "class_group", "course_offering", "subject", "status", "effective_from", "effective_until", "version"]
    list_filter = ["institution", "status", "effective_from"]
    search_fields = ["teacher__email", "class_group__name", "course_offering__name"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]
    fieldsets = [
        ("Identity", {"fields": ["id", "institution", "teacher", "class_group", "course_offering", "subject"]}),
        ("Assignment", {"fields": ["effective_from", "effective_until", "status"]}),
        ("Metadata", {"fields": ["metadata", "version"]}),
        ("Timestamps", {"fields": ["created_at", "updated_at"]}),
    ]


@admin.register(UserCapability)
class UserCapabilityAdmin(admin.ModelAdmin):
    list_display = ["user", "institution", "capability_code", "granted_at", "expires_at", "is_active"]
    list_filter = ["institution", "capability_code"]
    search_fields = ["user__email", "capability_code"]
    readonly_fields = ["id", "granted_at"]
    fieldsets = [
        ("Identity", {"fields": ["id", "user", "institution", "capability_code"]}),
        ("Grant", {"fields": ["granted_by", "granted_at", "expires_at"]}),
        ("Metadata", {"fields": ["metadata"]}),
    ]