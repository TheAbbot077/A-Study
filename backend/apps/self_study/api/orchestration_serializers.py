from rest_framework import serializers

from ..orchestration_models import (
    SelfStudyTeachingSession, TeachingContextSnapshot, TeachingOrchestrationRun,
    TeachingSessionFinding, TeachingSessionNode, TeachingTransition, TeachingTurn,
    TeachingTurnCitation,
)


class CreateTeachingSessionSerializer(serializers.Serializer):
    preparation_manifest_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class ExpectedVersionSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)


class LearnerTurnSerializer(ExpectedVersionSerializer):
    text = serializers.CharField(allow_blank=False, max_length=12000)
    idempotency_key = serializers.CharField(allow_blank=False, max_length=128)


class RevisitNodeSerializer(ExpectedVersionSerializer):
    bridge_node_id = serializers.UUIDField()


class PauseSerializer(ExpectedVersionSerializer):
    reason = serializers.CharField(required=False, default="LEARNER_PAUSED", max_length=96)


class InvalidateSerializer(ExpectedVersionSerializer):
    reason = serializers.CharField(required=False, default="TEACHING_SESSION_INVALIDATED", max_length=96)


class TeachingSessionSerializer(serializers.ModelSerializer):
    current_node_id = serializers.UUIDField(source="current_session_node_id", read_only=True, allow_null=True)

    class Meta:
        model = SelfStudyTeachingSession
        fields = ["id", "tenant_id", "learner_id", "intent_id", "bridge_plan_id", "preparation_manifest_id", "current_node_id", "state", "session_fingerprint", "privacy_policy_version", "disclosure_policy_version", "current_turn_sequence", "cancellation_reason", "version", "started_at", "paused_at", "completed_at", "created_at", "updated_at"]


class TeachingSessionNodeSerializer(serializers.ModelSerializer):
    stable_key = serializers.CharField(source="graph_node.stable_key", read_only=True)
    title = serializers.CharField(source="graph_node.title", read_only=True)

    class Meta:
        model = TeachingSessionNode
        fields = ["id", "bridge_node_id", "graph_node_id", "stable_key", "title", "teaching_pack_id", "graph_version_id", "plan_ordinal", "topological_layer", "bridge_disposition", "permitted_roles", "state", "context_fingerprint", "transition_metadata", "created_at"]


class TeachingTurnSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingTurn
        fields = ["id", "session_id", "session_node_id", "sequence_number", "actor", "action", "learner_input_reference", "generated_response_reference", "context_snapshot_id", "response_text", "provider_version", "model_version", "prompt_policy_version", "generation_fingerprint", "safety_status", "failure_code", "interruption_code", "created_at"]


class TeachingTurnCitationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingTurnCitation
        fields = ["id", "turn_id", "teaching_pack_resource_id", "evidence_unit_id", "resource_id", "extraction_provenance", "mapping_classification", "teaching_role", "retrieval_record_identity", "citation", "citation_fingerprint"]


class TeachingSessionFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingSessionFinding
        fields = ["id", "session_id", "session_node_id", "code", "severity", "blocking", "scope", "affected_identities", "details", "policy_version", "created_at"]


class TeachingContextSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingContextSnapshot
        fields = ["id", "session_id", "session_node_id", "graph_version_id", "bridge_plan_fingerprint", "preparation_fingerprint", "retrieval_fingerprint", "permitted_roles", "prior_turn_references", "retrieval_filters", "safety_policy_version", "disclosure_policy_version", "model_version", "prompt_policy_version", "context_snapshot", "context_fingerprint", "created_at"]


class TeachingTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingTransition
        fields = ["id", "session_id", "source_state", "target_state", "source_node_id", "target_node_id", "transition_type", "actor_id", "authority", "reason_code", "expected_version", "transition_fingerprint", "created_at"]


class TeachingOrchestrationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingOrchestrationRun
        fields = ["id", "tenant_id", "learner_id", "intent_id", "session_id", "bridge_plan_id", "preparation_manifest_id", "graph_version_id", "retrieval_manifest_id", "orchestration_version", "model_version", "prompt_policy_version", "run_fingerprint", "status", "stage", "failure_code", "failure_detail", "predecessor_id", "created_at", "completed_at"]
