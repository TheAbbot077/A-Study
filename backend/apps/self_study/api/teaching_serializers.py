from rest_framework import serializers

from ..teaching_models import (
    NodeTeachingPack, TeachingPackResource, TeachingPreparationManifest,
    TeachingPreparationRun, TeachingReadinessEvaluation, TeachingReadinessFinding,
    TeachingRetrievalManifest,
)


class CreateTeachingPreparationRunSerializer(serializers.Serializer):
    bridge_plan_id = serializers.UUIDField()
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class TeachingPreparationRunSerializer(serializers.ModelSerializer):
    manifest_id = serializers.UUIDField(source="manifest.id", read_only=True, allow_null=True)

    class Meta:
        model = TeachingPreparationRun
        fields = ["id", "intent_id", "bridge_plan_id", "graph_version_id", "coverage_evaluation_id", "bridge_plan_fingerprint", "coverage_fingerprint", "mapping_set_fingerprint", "run_fingerprint", "algorithm_version", "policy_version", "role_policy_version", "retrieval_schema_version", "readiness_policy_version", "status", "stage", "failure_code", "failure_detail", "predecessor_id", "version", "manifest_id", "created_at", "completed_at"]


class TeachingPreparationManifestSerializer(serializers.ModelSerializer):
    input_current = serializers.SerializerMethodField()
    readiness_state = serializers.SerializerMethodField()
    retrieval_status = serializers.SerializerMethodField()

    class Meta:
        model = TeachingPreparationManifest
        fields = ["id", "run_id", "intent_id", "bridge_plan_id", "graph_version_id", "coverage_evaluation_id", "status", "manifest_fingerprint", "pack_set_fingerprint", "assignment_set_fingerprint", "citation_set_fingerprint", "retrieval_manifest_fingerprint", "readiness_fingerprint", "algorithm_version", "policy_version", "role_policy_version", "approved_by_id", "approved_at", "approval_reason", "published_at", "rejected_by_id", "rejected_at", "rejection_reason", "predecessor_id", "version", "created_at", "input_current", "readiness_state", "retrieval_status"]

    def get_input_current(self, obj):
        from ..application.teaching_services import _currentness
        return not _currentness(obj.run)

    def get_readiness_state(self, obj):
        evaluation = obj.readiness_evaluations.order_by("-created_at").first()
        return evaluation.state if evaluation else "NOT_EVALUATED"

    def get_retrieval_status(self, obj):
        return obj.retrieval_manifest.status if hasattr(obj, "retrieval_manifest") else "NOT_PUBLISHED"


class NodeTeachingPackSerializer(serializers.ModelSerializer):
    stable_key = serializers.CharField(source="graph_node.stable_key", read_only=True)
    title = serializers.CharField(source="graph_node.title", read_only=True)

    class Meta:
        model = NodeTeachingPack
        fields = ["id", "bridge_node_id", "graph_node_id", "stable_key", "title", "node_type", "ordinal", "topological_layer", "bridge_disposition", "material_feasibility", "coverage_state", "status", "role_policy_snapshot", "required_role_count", "satisfied_role_count", "assignment_count", "distinct_source_count", "duplicate_cluster_count", "blocker_count", "pack_fingerprint"]


class TeachingPackResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingPackResource
        fields = ["id", "pack_id", "accepted_mapping_id", "evidence_unit_id", "resource_id", "source_input_id", "source_block_id", "classification", "role", "rank", "diversity_key", "duplicate_cluster", "licence_disposition", "safety_disposition", "citation_snapshot", "rationale_codes", "policy_version", "assignment_fingerprint"]


class TeachingRetrievalManifestSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingRetrievalManifest
        fields = ["id", "manifest_id", "bridge_plan_id", "status", "expected_assignment_count", "published_assignment_count", "expected_assignment_identities", "published_assignment_identities", "metadata_filters", "manifest_fingerprint", "verification_fingerprint", "retrieval_schema_version", "index_version", "verified_at", "created_at"]


class TeachingReadinessEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingReadinessEvaluation
        fields = ["id", "manifest_id", "retrieval_manifest_id", "state", "node_results", "blocker_count", "warning_count", "evaluation_fingerprint", "policy_version", "created_at"]


class TeachingReadinessFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeachingReadinessFinding
        fields = ["id", "pack_id", "code", "severity", "blocking", "scope", "affected_identities", "details", "policy_version", "created_at"]


class DecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False, max_length=2000)
    expected_version = serializers.IntegerField(min_value=1)


class ExpectedVersionSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)


class InvalidateSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, default="TEACHING_PREPARATION_INVALIDATED", max_length=96)
    expected_version = serializers.IntegerField(min_value=1)
