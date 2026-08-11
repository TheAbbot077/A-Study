from rest_framework import serializers

from apps.study_lab.domain.enums import (
    ArtefactTransformationRequestStatus,
    InstrumentFamily,
    ProviderContext,
    StudyArtefactOrigin,
    StudyArtefactLifecycle,
    StudyArtefactVisibility,
    StudyToolManifestStatus,
    StudyArtefactType,
    StudyScaffoldGenerationStatus,
    StudyScaffoldGenerationType,
    WorkspaceToolSessionStatus,
    NoteStatus,
    WorkspaceStatus,
    WorkspaceType,
)
from apps.study_lab.domain.models import (
    ArtefactTransformationRequest,
    LearnerWorkspaceNote,
    StudyArtefact,
    StudyArtefactLineage,
    StudyToolDefinition,
    StudyToolManifest,
    StudyWorkspace,
    WorkspaceToolSession,
    StudyScaffoldGenerationRequest,
)


class StudyWorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyWorkspace
        fields = ["id", "learner", "tenant", "workspace_type", "status", "title", "created_at", "updated_at", "last_opened_at", "version"]
        read_only_fields = fields


class StudyWorkspaceCreateSerializer(serializers.Serializer):
    workspace_type = serializers.ChoiceField(choices=WorkspaceType.choices)
    title = serializers.CharField(max_length=255)
    tenant = serializers.UUIDField(required=False, allow_null=True)


class StudyArtefactCreateSerializer(serializers.Serializer):
    artefact_type = serializers.CharField()
    title = serializers.CharField(required=False, allow_blank=True, default="")
    summary = serializers.CharField(required=False, allow_blank=True, default="")
    provider_context = serializers.CharField(required=False, allow_blank=True, allow_null=True, default=None)
    provider_reference = serializers.CharField(required=False, allow_blank=True, default="")
    visibility = serializers.CharField(required=False, default=StudyArtefactVisibility.PRIVATE.value)
    schema_version = serializers.CharField(required=False, default="1")
    creation_source = serializers.CharField(required=False, default=StudyArtefactOrigin.NATIVE.value)
    native_payload = serializers.JSONField(required=False, default=dict)

    def validate(self, attrs):
        artefact_type = attrs.get("artefact_type")
        if hasattr(artefact_type, "value"):
            artefact_type = artefact_type.value
        if artefact_type not in StudyArtefactType.values:
            raise serializers.ValidationError({"artefact_type": "Invalid artefact type."})
        attrs["artefact_type"] = artefact_type

        provider_context = attrs.get("provider_context")
        if hasattr(provider_context, "value"):
            provider_context = provider_context.value
        if provider_context not in {None, ""} and provider_context not in ProviderContext.values:
            raise serializers.ValidationError({"provider_context": "Invalid provider context."})
        attrs["provider_context"] = provider_context or None

        visibility = attrs.get("visibility", StudyArtefactVisibility.PRIVATE.value)
        if hasattr(visibility, "value"):
            visibility = visibility.value
        if visibility not in StudyArtefactVisibility.values:
            raise serializers.ValidationError({"visibility": "Invalid visibility."})
        attrs["visibility"] = visibility

        creation_source = attrs.get("creation_source", StudyArtefactOrigin.NATIVE.value)
        if hasattr(creation_source, "value"):
            creation_source = creation_source.value
        if creation_source not in StudyArtefactOrigin.values:
            raise serializers.ValidationError({"creation_source": "Invalid creation source."})
        attrs["creation_source"] = creation_source
        return attrs


class LearnerWorkspaceNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearnerWorkspaceNote
        fields = ["id", "workspace", "learner", "subject_id", "concept_id", "session_reference", "title", "status", "created_at", "updated_at", "deleted_at", "version"]
        read_only_fields = ["id", "workspace", "learner", "created_at", "updated_at", "deleted_at", "version"]


class LearnerWorkspaceNoteCreateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, default="")
    content = serializers.CharField(required=False, allow_blank=True, default="")
    subject_id = serializers.UUIDField(required=False, allow_null=True)
    concept_id = serializers.UUIDField(required=False, allow_null=True)
    session_reference = serializers.CharField(required=False, allow_blank=True, default="")


class StudyToolDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyToolDefinition
        fields = [
            "id",
            "tool_key",
            "display_name",
            "description",
            "provider_context",
            "instrument_family",
            "input_artefact_types",
            "output_artefact_types",
            "supported_workspace_types",
            "schema_versions",
            "supports_transform",
            "supports_import",
            "supports_export",
            "requires_runtime",
            "runtime_provider",
            "offline_capable",
            "status",
            "version",
            "created_at",
            "updated_at",
        ]


class StudyToolManifestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyToolManifest
        fields = [
            "id",
            "tool_definition",
            "manifest_version",
            "supported_artefact_inputs",
            "supported_artefact_outputs",
            "supported_schema_versions",
            "supports_resume",
            "supports_transformation",
            "supports_import",
            "supports_export",
            "status",
            "version",
        ]


class WorkspaceToolSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkspaceToolSession
        fields = ["id", "workspace", "learner", "tool_definition", "provider_context", "provider_reference", "resume_reference", "status", "opened_at", "suspended_at", "completed_at", "failed_at", "version"]


class StudyArtefactSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyArtefact
        fields = ["id", "workspace", "learner", "tenant", "artefact_type", "provider_context", "provider_reference", "title", "summary", "version", "visibility", "lifecycle", "schema_version", "creation_source", "invocation_reference", "created_at", "updated_at", "archived_at"]


class StudyArtefactLineageSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyArtefactLineage
        fields = ["id", "workspace", "source_artefact", "target_artefact", "relation_type", "provider_context", "provider_reference", "created_at", "version"]


class ArtefactTransformationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtefactTransformationRequest
        fields = ["id", "workspace", "learner", "definition", "source_artefact", "output_artefact", "status", "failure_reason", "requested_at", "validating_at", "ready_at", "processing_at", "completed_at", "failed_at", "cancelled_at", "version"]


class StudyScaffoldGenerationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudyScaffoldGenerationRequest
        fields = [
            "id",
            "workspace",
            "learner",
            "generation_type",
            "requested_artefact_type",
            "provider_context",
            "provider_reference",
            "policy_version",
            "idempotency_key",
            "request_checksum",
            "status",
            "failure_code",
            "failure_detail",
            "requested_at",
            "validating_at",
            "ready_at",
            "processing_at",
            "completed_at",
            "failed_at",
            "cancelled_at",
            "version",
            "result_artefact",
        ]


class LearnerWorkspaceNoteUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True)
    content = serializers.CharField(required=False, allow_blank=True)
    version = serializers.IntegerField(required=False)
