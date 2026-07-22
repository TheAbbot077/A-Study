from rest_framework import serializers

from ..graph_models import CurriculumGraph, CurriculumGraphFinding, CurriculumGraphVersion, CurriculumNode


class GraphBuildSerializer(serializers.Serializer):
    construction_method = serializers.ChoiceField(choices=["STRUCTURED_IMPORT", "CURATED_AUTHORING", "COMPOSITE_ASSEMBLY"])


class GraphSpecificationSerializer(serializers.Serializer):
    specification = serializers.JSONField()


class GraphPublishSerializer(serializers.Serializer):
    expected_fingerprint = serializers.CharField(max_length=128)


class GraphInvalidateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=64)


class GraphVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurriculumGraphVersion
        fields = ["id", "version_number", "status", "source_selection_fingerprint", "graph_fingerprint",
                  "builder_algorithm_version", "validation_algorithm_version", "stable_key_algorithm_version",
                  "source_language", "construction_method", "node_count", "edge_count", "root_count",
                  "outcome_count", "validation_summary", "created_at", "published_at", "invalidation_reason"]


class GraphSerializer(serializers.ModelSerializer):
    current_version = GraphVersionSerializer(read_only=True)

    class Meta:
        model = CurriculumGraph
        fields = ["id", "intent_id", "selection_decision_id", "composite_proposal_id", "status",
                  "current_version", "created_at", "updated_at", "version"]


class GraphNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurriculumNode
        fields = ["id", "stable_key", "node_type", "title", "description", "ordinal", "depth",
                  "source_curriculum_version_id", "authority_namespace", "external_identifier",
                  "external_prerequisite_status", "metadata"]


class GraphFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurriculumGraphFinding
        fields = ["id", "code", "severity", "node_id", "edge_id", "related_node_id", "message", "details", "created_at"]
