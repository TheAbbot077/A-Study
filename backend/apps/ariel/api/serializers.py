from rest_framework import serializers

from apps.ariel.domain.models import (
    ArielConstitution,
    ArielCorrectionRecord,
    ArielIdentity,
    ArielKnowledgeUnit,
    ArielMemoryRecord,
    ArielMisconception,
    ArielRelationship,
    ArielReinforcementRecord,
    ArielTeachBackInteraction,
    ArielTeachingSession,
    ArielTeachingTurn,
    ArielUserCapability,
)


class ArielConstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielConstitution
        fields = ["id", "version", "rules", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ArielIdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielIdentity
        fields = [
            "id", "learner_id", "institution_id", "constitution_id",
            "status", "display_name", "metadata", "version",
            "created_at", "updated_at", "activated_at", "suspended_at", "archived_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class ArielRelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielRelationship
        fields = [
            "id", "identity_id", "learner_id", "consent_state",
            "institutional_visibility", "status", "privacy_policy", "retention_policy",
            "version", "created_at", "updated_at", "consent_granted_at", "consent_withdrawn_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class ArielTeachingSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielTeachingSession
        fields = [
            "id", "identity_id", "learner_id", "constitution_id",
            "learning_journey_id", "subject_id", "concept_reference",
            "status", "metadata", "version", "created_at", "updated_at", "completed_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class ArielTeachingTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielTeachingTurn
        fields = [
            "id", "session_id", "actor", "content", "sequence_number",
            "disposition", "provenance", "resulting_memory_effect", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ArielTeachBackInteractionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielTeachBackInteraction
        fields = [
            "id",
            "identity_id",
            "teaching_session_id",
            "learner_id",
            "workspace_id",
            "learning_journey_id",
            "subject_id",
            "concept_reference",
            "source_memory_unit_id",
            "learner_response_turn_id",
            "interaction_type",
            "status",
            "strategy_reason_code",
            "intensity",
            "prompt_template_key",
            "prompt_template_version",
            "input_provenance",
            "requires_artefact",
            "required_artefact_type",
            "version",
            "created_at",
            "updated_at",
            "presented_at",
            "responded_at",
            "resolved_at",
            "skipped_at",
            "cancelled_at",
            "expires_at",
        ]
        read_only_fields = [
            "id",
            "learner_id",
            "identity_id",
            "teaching_session_id",
            "status",
            "strategy_reason_code",
            "intensity",
            "prompt_template_key",
            "prompt_template_version",
            "version",
            "created_at",
            "updated_at",
            "presented_at",
            "responded_at",
            "resolved_at",
            "skipped_at",
            "cancelled_at",
            "expires_at",
        ]


class ArielKnowledgeUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielKnowledgeUnit
        fields = [
            "id", "identity_id", "learner_id", "teaching_turn_id", "session_id",
            "normalized_statement", "confidence", "memory_state", "provenance",
            "subject_id", "concept_reference", "superseded_by_id",
            "forgetting_metadata", "metadata", "version",
            "created_at", "updated_at", "superseded_at", "forgotten_at", "retracted_at",
        ]
        read_only_fields = ["id", "version", "created_at", "updated_at"]


class ArielMemoryRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielMemoryRecord
        fields = [
            "id", "identity_id", "knowledge_unit_id", "learner_id",
            "previous_state", "new_state", "previous_confidence", "new_confidence",
            "transition_reason", "provenance", "metadata", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ArielMisconceptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielMisconception
        fields = [
            "id", "identity_id", "knowledge_unit_id", "learner_id",
            "original_explanation", "resulting_belief", "contradiction_history",
            "correction_history", "current_state", "metadata", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ArielCorrectionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielCorrectionRecord
        fields = [
            "id", "identity_id", "learner_id", "superseded_knowledge_id",
            "replacement_knowledge_id", "teaching_turn_id", "correction_reason",
            "metadata", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ArielReinforcementRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielReinforcementRecord
        fields = [
            "id", "identity_id", "knowledge_unit_id", "learner_id", "teaching_turn_id",
            "previous_confidence", "updated_confidence", "previous_state", "new_state",
            "metadata", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ArielUserCapabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = ArielUserCapability
        fields = [
            "id", "user_id", "identity_id", "capability_code",
            "granted_at", "granted_by_id", "expires_at", "metadata",
        ]
        read_only_fields = ["id", "granted_at"]
