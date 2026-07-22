from __future__ import annotations

from rest_framework import serializers

from apps.academic.models import LearningResource
from apps.content_processing.models import ContentProcessingJob
from apps.users.models import Institution

from ..workspace_models import SelfStudyWorkspace, SelfStudyWorkspaceMaterial


class SelfStudyWorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SelfStudyWorkspace
        fields = [
            "id",
            "tenant_id",
            "learner_id",
            "display_name",
            "description",
            "status",
            "intent_id",
            "curriculum_resolution_id",
            "published_graph_id",
            "active_diagnostic_id",
            "latest_coverage_evaluation_id",
            "active_bridge_plan_id",
            "active_teaching_preparation_id",
            "active_teaching_session_id",
            "created_at",
            "updated_at",
            "archived_at",
            "version",
        ]
        read_only_fields = fields


class CreateWorkspaceSerializer(serializers.Serializer):
    tenant_id = serializers.PrimaryKeyRelatedField(queryset=Institution.objects.all(), source="tenant", required=False)
    display_name = serializers.CharField(max_length=160)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128, default="")


class UpdateWorkspaceSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    display_name = serializers.CharField(max_length=160, required=False)
    description = serializers.CharField(required=False, allow_blank=True)


class WorkspaceVersionCommandSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)


class AttachIntentSerializer(serializers.Serializer):
    intent_id = serializers.UUIDField()
    expected_version = serializers.IntegerField(min_value=1)


class AttachWorkspaceMaterialSerializer(serializers.Serializer):
    resource_id = serializers.PrimaryKeyRelatedField(queryset=LearningResource.objects.all(), source="resource")
    content_processing_job_id = serializers.PrimaryKeyRelatedField(
        queryset=ContentProcessingJob.objects.all(),
        source="content_processing_job",
        required=False,
        allow_null=True,
    )
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128, default="")


class WorkspaceMaterialSerializer(serializers.ModelSerializer):
    resource_title = serializers.CharField(source="resource.title", read_only=True)
    resource_status = serializers.CharField(source="resource.status", read_only=True)
    processing_job_id = serializers.UUIDField(source="content_processing_job_id", read_only=True)
    processing_status = serializers.CharField(source="content_processing_job.status", read_only=True, allow_null=True)

    class Meta:
        model = SelfStudyWorkspaceMaterial
        fields = [
            "id",
            "workspace_id",
            "resource_id",
            "resource_title",
            "resource_status",
            "processing_job_id",
            "processing_status",
            "status",
            "blocker_codes",
            "safe_status_summary",
            "created_at",
            "updated_at",
            "retired_at",
            "version",
        ]
        read_only_fields = fields


class DiagnosticStartSerializer(serializers.Serializer):
    purpose_acknowledged = serializers.BooleanField()
