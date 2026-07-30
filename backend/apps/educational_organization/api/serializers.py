from rest_framework import serializers

from apps.educational_organization.domain.models import (
    AcademicPeriod,
    AcademicUnit,
    ClassGroup,
    CourseOffering,
    EducationalOrganization,
    Programme,
    TeachingAssignment,
)


class EducationalOrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalOrganization
        fields = [
            "id",
            "institution_id",
            "parent_id",
            "name",
            "slug",
            "organization_type",
            "status",
            "metadata",
            "version",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class AcademicUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicUnit
        fields = [
            "id",
            "institution_id",
            "educational_organization_id",
            "parent_id",
            "name",
            "slug",
            "unit_type",
            "status",
            "metadata",
            "version",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class ProgrammeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programme
        fields = [
            "id",
            "institution_id",
            "educational_organization_id",
            "academic_unit_id",
            "name",
            "slug",
            "qualification",
            "description",
            "status",
            "metadata",
            "version",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class AcademicPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicPeriod
        fields = [
            "id",
            "institution_id",
            "educational_organization_id",
            "name",
            "slug",
            "period_type",
            "starts_at",
            "ends_at",
            "status",
            "metadata",
            "version",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class CourseOfferingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseOffering
        fields = [
            "id",
            "institution_id",
            "educational_organization_id",
            "academic_unit_id",
            "programme_id",
            "academic_period_id",
            "subject_id",
            "name",
            "slug",
            "description",
            "status",
            "metadata",
            "version",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class ClassGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClassGroup
        fields = [
            "id",
            "institution_id",
            "educational_organization_id",
            "academic_unit_id",
            "course_offering_id",
            "name",
            "slug",
            "description",
            "status",
            "metadata",
            "version",
            "archived_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class TeachingAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingAssignment
        fields = [
            "id",
            "institution_id",
            "teacher_id",
            "class_group_id",
            "course_offering_id",
            "subject_id",
            "effective_from",
            "effective_until",
            "status",
            "metadata",
            "version",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]