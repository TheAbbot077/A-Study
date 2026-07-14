from rest_framework import serializers

from apps.academic.domain.models import (
    ContentConcept,
    ContentSection,
    Curriculum,
    CurriculumUnit,
    LearningResource,
    ResourceIngestionJob,
    Subject,
)
from apps.users.domain.models import Institution


class SubjectSerializer(serializers.ModelSerializer):
    institution = serializers.PrimaryKeyRelatedField(required=False, allow_null=True, queryset=Institution.objects.all())

    class Meta:
        model = Subject
        fields = ["id", "institution", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        validators = []


class CurriculumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curriculum
        fields = ["id", "subject", "institution", "name", "description", "version", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CurriculumUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurriculumUnit
        fields = ["id", "curriculum", "title", "description", "sequence_number", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class LearningResourceSerializer(serializers.ModelSerializer):
    resource_ready_for_learning = serializers.SerializerMethodField()

    class Meta:
        model = LearningResource
        fields = [
            "id",
            "institution",
            "subject",
            "curriculum",
            "curriculum_unit",
            "stored_file",
            "title",
            "description",
            "resource_type",
            "status",
            "source_label",
            "resource_ready_for_learning",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_resource_ready_for_learning(self, obj):
        latest_job = obj.content_import_jobs.order_by("-created_at").first()
        if latest_job is None or latest_job.status != "completed":
            return False
        return obj.content_sections.exists() and ContentConcept.objects.filter(content_section__learning_resource=obj).exists()


class ContentSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentSection
        fields = [
            "id",
            "learning_resource",
            "title",
            "description",
            "sequence_number",
            "review_status",
            "quality_status",
            "review_notes",
            "approved_at",
            "approved_by",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "review_status",
            "quality_status",
            "review_notes",
            "approved_at",
            "approved_by",
            "created_at",
            "updated_at",
        ]


class ContentConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentConcept
        fields = [
            "id",
            "content_section",
            "title",
            "description",
            "learning_objective",
            "sequence_number",
            "review_status",
            "quality_status",
            "review_notes",
            "approved_at",
            "approved_by",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "review_status",
            "quality_status",
            "review_notes",
            "approved_at",
            "approved_by",
            "created_at",
            "updated_at",
        ]


class ResourceIngestionJobSerializer(serializers.ModelSerializer):
    learning_resource = serializers.PrimaryKeyRelatedField(
        queryset=LearningResource.objects.all(),
        pk_field=serializers.UUIDField(format="hex_verbose"),
    )

    class Meta:
        model = ResourceIngestionJob
        fields = [
            "id",
            "learning_resource",
            "stored_file",
            "status",
            "source_type",
            "requested_by",
            "error_message",
            "metadata",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "requested_by", "error_message", "started_at", "completed_at", "created_at", "updated_at"]


class ReviewActionSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default=None)


class QualityMarkSerializer(serializers.Serializer):
    quality_status = serializers.ChoiceField(choices=ContentSection.QualityStatus.choices)
    notes = serializers.CharField(required=False, allow_blank=True, default=None)


class IngestionFailureSerializer(serializers.Serializer):
    error_message = serializers.CharField(required=True, allow_blank=False)
