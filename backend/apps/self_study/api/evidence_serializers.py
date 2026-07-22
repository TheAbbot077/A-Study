from rest_framework import serializers
from ..evidence_models import *
class CreateMappingRunSerializer(serializers.Serializer):resource_ids=serializers.ListField(child=serializers.UUIDField(),allow_empty=False)
class MappingRunSerializer(serializers.ModelSerializer):
 class Meta:model=EvidenceMappingRun;fields=["id","intent_id","graph_version_id","status","stage","run_fingerprint","algorithm_versions","policy_version","failure_code","version","created_at","completed_at"]
class EvidenceUnitSerializer(serializers.ModelSerializer):
 class Meta:model=ContentEvidenceUnit;fields=["id","ordinal","evidence_type","structural_role","page_reference","original_language","normalized_language","extraction_confidence","citation_snapshot","licence_disposition","safety_disposition","duplicate_cluster","identity_fingerprint","is_substantive"]
class CandidateSerializer(serializers.ModelSerializer):
 class Meta:model=EvidenceMappingCandidate;fields=["id","evidence_unit_id","graph_node_id","graph_node_type","method","lexical_score","semantic_score","structural_score","combined_score","rank","rationale_codes","disposition","algorithm_version"]
class MappingSerializer(serializers.ModelSerializer):
 class Meta:model=CurriculumEvidenceMapping;fields=["id","evidence_unit_id","graph_node_id","graph_node_type","classification","status","confidence_band","scores","rule_codes","rationale_codes","citation_snapshot","algorithm_version","policy_version","decided_at"]
class NodeCoverageSerializer(serializers.ModelSerializer):
 class Meta:model=CurriculumNodeCoverage;fields=["graph_node_id","node_type","state","sufficiency_score","direct_count","supporting_count","prerequisite_count","assessment_count","conflicting_count","distinct_source_count","accepted_mapping_count","excluded_count","rationale_codes","blocker_count","citation_set_fingerprint"]
class FindingSerializer(serializers.ModelSerializer):
 class Meta:model=CoverageFinding;fields=["code","severity","blocking","scope_type","scope_identifier","graph_node_id","details","algorithm_version","policy_version","created_at"]
