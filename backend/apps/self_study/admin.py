from django.contrib import admin
from .evidence_models import ContentEvidenceUnit,CoverageFinding,CurriculumCoverageEvaluation,CurriculumEvidenceMapping,CurriculumNodeCoverage,EvidenceMappingCandidate,EvidenceMappingRun
from .bridge_models import BridgePlan, BridgePlanDependency, BridgePlanFinding, BridgePlanNode, BridgePlanningRun
from .teaching_models import NodeTeachingPack, TeachingPackResource, TeachingPreparationManifest, TeachingPreparationRun, TeachingReadinessEvaluation, TeachingReadinessFinding, TeachingRetrievalManifest
from .orchestration_models import SelfStudyTeachingSession, TeachingContextSnapshot, TeachingOrchestrationRun, TeachingSessionFinding, TeachingSessionNode, TeachingTransition, TeachingTurn, TeachingTurnCitation
from .workspace_models import SelfStudyWorkspace, SelfStudyWorkspaceMaterial

@admin.register(EvidenceMappingRun)
class EvidenceMappingRunAdmin(admin.ModelAdmin):
 list_display=("id","tenant","intent","status","stage","created_at","completed_at");list_filter=("status","stage");search_fields=("id","run_fingerprint")
@admin.register(ContentEvidenceUnit)
class ContentEvidenceUnitAdmin(admin.ModelAdmin):list_display=("id","run","ordinal","evidence_type","is_substantive");list_filter=("evidence_type","is_substantive")
@admin.register(EvidenceMappingCandidate)
class EvidenceMappingCandidateAdmin(admin.ModelAdmin):list_display=("id","run","graph_node","method","rank","combined_score")
@admin.register(CurriculumEvidenceMapping)
class CurriculumEvidenceMappingAdmin(admin.ModelAdmin):list_display=("id","run","graph_node","classification","status","confidence_band");list_filter=("classification","status")
@admin.register(CurriculumCoverageEvaluation)
class CurriculumCoverageEvaluationAdmin(admin.ModelAdmin):list_display=("id","run","status","gap_set_fingerprint","completed_at")
@admin.register(CurriculumNodeCoverage)
class CurriculumNodeCoverageAdmin(admin.ModelAdmin):list_display=("evaluation","graph_node","node_type","state","blocker_count");list_filter=("node_type","state")
@admin.register(CoverageFinding)
class CoverageFindingAdmin(admin.ModelAdmin):list_display=("evaluation","code","severity","blocking","scope_type");list_filter=("severity","blocking")

@admin.register(BridgePlanningRun)
class BridgePlanningRunAdmin(admin.ModelAdmin):
 list_display=("id","tenant","intent","status","stage","created_at","completed_at");list_filter=("status","stage");search_fields=("id","run_fingerprint")
@admin.register(BridgePlan)
class BridgePlanAdmin(admin.ModelAdmin):
 list_display=("id","intent","status","generated_at","approved_at","activated_at");list_filter=("status",);search_fields=("id","plan_fingerprint")
@admin.register(BridgePlanNode)
class BridgePlanNodeAdmin(admin.ModelAdmin):
 list_display=("plan","graph_node","topological_layer","learner_disposition","material_feasibility");list_filter=("learner_disposition","material_feasibility")
@admin.register(BridgePlanDependency)
class BridgePlanDependencyAdmin(admin.ModelAdmin):
 list_display=("plan","graph_edge","predecessor_node","successor_node","requirement_type")
@admin.register(BridgePlanFinding)
class BridgePlanFindingAdmin(admin.ModelAdmin):
 list_display=("plan","code","severity","blocking","scope");list_filter=("severity","blocking")

@admin.register(TeachingPreparationRun)
class TeachingPreparationRunAdmin(admin.ModelAdmin):
 list_display=("id","tenant","intent","bridge_plan","status","stage","created_at","completed_at");list_filter=("status","stage");search_fields=("id","run_fingerprint")
@admin.register(TeachingPreparationManifest)
class TeachingPreparationManifestAdmin(admin.ModelAdmin):
 list_display=("id","intent","bridge_plan","status","approved_at","published_at","created_at");list_filter=("status",);search_fields=("id","manifest_fingerprint")
@admin.register(NodeTeachingPack)
class NodeTeachingPackAdmin(admin.ModelAdmin):
 list_display=("manifest","graph_node","topological_layer","status","bridge_disposition","material_feasibility");list_filter=("status","node_type")
@admin.register(TeachingPackResource)
class TeachingPackResourceAdmin(admin.ModelAdmin):
 list_display=("pack","accepted_mapping","resource","role","rank");list_filter=("role","classification")
@admin.register(TeachingRetrievalManifest)
class TeachingRetrievalManifestAdmin(admin.ModelAdmin):
 list_display=("id","manifest","status","expected_assignment_count","published_assignment_count","verified_at");list_filter=("status",)
@admin.register(TeachingReadinessEvaluation)
class TeachingReadinessEvaluationAdmin(admin.ModelAdmin):
 list_display=("id","manifest","state","blocker_count","warning_count","created_at");list_filter=("state",)
@admin.register(TeachingReadinessFinding)
class TeachingReadinessFindingAdmin(admin.ModelAdmin):
 list_display=("manifest","code","severity","blocking","scope");list_filter=("severity","blocking")

@admin.register(SelfStudyTeachingSession)
class SelfStudyTeachingSessionAdmin(admin.ModelAdmin):
 list_display=("id","intent","learner","state","current_turn_sequence","created_at");list_filter=("state",);search_fields=("id","session_fingerprint")
@admin.register(TeachingSessionNode)
class TeachingSessionNodeAdmin(admin.ModelAdmin):
 list_display=("session","graph_node","topological_layer","plan_ordinal","state");list_filter=("state",)
@admin.register(TeachingOrchestrationRun)
class TeachingOrchestrationRunAdmin(admin.ModelAdmin):
 list_display=("id","session","status","stage","created_at","completed_at");list_filter=("status","stage");search_fields=("id","run_fingerprint")
@admin.register(TeachingContextSnapshot)
class TeachingContextSnapshotAdmin(admin.ModelAdmin):
 list_display=("id","session","session_node","created_at");search_fields=("context_fingerprint",)
@admin.register(TeachingTurn)
class TeachingTurnAdmin(admin.ModelAdmin):
 list_display=("session","sequence_number","actor","action","safety_status","created_at");list_filter=("actor","action","safety_status")
@admin.register(TeachingTurnCitation)
class TeachingTurnCitationAdmin(admin.ModelAdmin):
 list_display=("turn","teaching_pack_resource","teaching_role","resource")
@admin.register(TeachingTransition)
class TeachingTransitionAdmin(admin.ModelAdmin):
 list_display=("session","transition_type","source_state","target_state","created_at");list_filter=("transition_type",)
@admin.register(TeachingSessionFinding)
class TeachingSessionFindingAdmin(admin.ModelAdmin):
 list_display=("session","code","severity","blocking","scope");list_filter=("severity","blocking")

@admin.register(SelfStudyWorkspace)
class SelfStudyWorkspaceAdmin(admin.ModelAdmin):
 list_display=("id","display_name","learner","tenant","status","updated_at");list_filter=("status",);search_fields=("id","display_name")
@admin.register(SelfStudyWorkspaceMaterial)
class SelfStudyWorkspaceMaterialAdmin(admin.ModelAdmin):
 list_display=("workspace","resource","status","content_processing_job","created_at");list_filter=("status",)
