from rest_framework import serializers

from ..bridge_models import BridgePlan, BridgePlanDependency, BridgePlanFinding, BridgePlanNode, BridgePlanningRun


class CreateBridgePlanningRunSerializer(serializers.Serializer):
    intent_id = serializers.UUIDField()
    target_node_ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class BridgePlanningRunSerializer(serializers.ModelSerializer):
    plan_id = serializers.UUIDField(source="plan.id", read_only=True, allow_null=True)

    class Meta:
        model = BridgePlanningRun
        fields = ["id", "intent_id", "selection_decision_id", "graph_version_id", "diagnostic_profile_id", "coverage_evaluation_id", "target_manifest", "run_fingerprint", "algorithm_version", "policy_version", "status", "stage", "failure_code", "failure_detail", "predecessor_id", "version", "plan_id", "created_at", "completed_at"]


class BridgePlanSerializer(serializers.ModelSerializer):
    current = serializers.SerializerMethodField()
    input_current = serializers.SerializerMethodField()

    class Meta:
        model = BridgePlan
        fields = ["id", "run_id", "intent_id", "graph_version_id", "target_set_snapshot", "target_set_fingerprint", "node_set_fingerprint", "dependency_set_fingerprint", "blocker_set_fingerprint", "plan_fingerprint", "algorithm_version", "policy_version", "status", "generated_at", "approved_by_id", "approved_at", "approval_reason", "activated_by_id", "activated_at", "predecessor_id", "version", "current", "input_current"]

    def get_current(self, obj):
        return obj.status == "ACTIVE"

    def get_input_current(self, obj):
        from ..application.bridge_services import _currentness
        return not _currentness(obj.run)


class BridgePlanNodeSerializer(serializers.ModelSerializer):
    stable_key = serializers.CharField(source="graph_node.stable_key", read_only=True)
    title = serializers.CharField(source="graph_node.title", read_only=True)

    class Meta:
        model = BridgePlanNode
        fields = ["id", "graph_node_id", "stable_key", "title", "node_type", "ordinal", "topological_layer", "learner_disposition", "requirement_type", "inclusion_rationale", "placement_band", "coverage_id", "coverage_state", "material_feasibility", "is_target", "is_entry", "is_required", "blocker_count", "dependency_count", "coverage_citations", "fingerprint"]


class BridgePlanDependencySerializer(serializers.ModelSerializer):
    predecessor_graph_node_id = serializers.UUIDField(source="predecessor_node.graph_node_id", read_only=True)
    successor_graph_node_id = serializers.UUIDField(source="successor_node.graph_node_id", read_only=True)

    class Meta:
        model = BridgePlanDependency
        fields = ["id", "predecessor_node_id", "successor_node_id", "predecessor_graph_node_id", "successor_graph_node_id", "graph_edge_id", "edge_type", "requirement_type", "affects_ordering", "rationale", "fingerprint"]


class BridgePlanFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = BridgePlanFinding
        fields = ["id", "code", "severity", "blocking", "scope", "affected_identities", "details", "algorithm_version", "policy_version", "created_at"]


class DecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False, max_length=2000)
    expected_version = serializers.IntegerField(min_value=1)


class ActivateSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)


class InvalidateSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, default="BRIDGE_PLAN_INVALIDATED", max_length=96)
    expected_version = serializers.IntegerField(min_value=1)
