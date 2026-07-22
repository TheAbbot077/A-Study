from celery import shared_task

from ...application.curriculum_services import ResolveCurriculumAttemptService
from ...application.graph_services import BuildCurriculumGraphService, ValidateCurriculumGraphService
from ...application.diagnostic_services import BuildDiagnosticBlueprintService,FinalizeDiagnosticPlacementService
from ...application.evidence_services import BuildContentEvidenceService,EvaluateCurriculumCoverageService,FailEvidenceMappingRunService,GenerateEvidenceMappingCandidatesService
from ...application.bridge_services import CreateBridgePlanService, FailBridgePlanningRunService, FinalizeBridgePlanService
from ...application.teaching_services import AssembleTeachingPreparationService, EvaluateTeachingReadinessService, FailTeachingPreparationRunService, VerifyTeachingRetrievalPublicationService
from ...application.orchestration_services import AdvanceTeachingSessionService, GenerateTeachingTurnService, RequestEvidenceEvaluationService


@shared_task(name="self_study.resolve_curriculum")
def resolve_curriculum_task(attempt_id: str) -> None:
    ResolveCurriculumAttemptService().execute(attempt_id)


@shared_task(name="self_study.build_curriculum_graph")
def build_curriculum_graph_task(graph_version_id: str) -> None:
    BuildCurriculumGraphService().execute(graph_version_id)


@shared_task(name="self_study.validate_curriculum_graph")
def validate_curriculum_graph_task(graph_version_id: str) -> None:
    ValidateCurriculumGraphService().execute(graph_version_id)

@shared_task(name="self_study.build_diagnostic_blueprint")
def build_diagnostic_blueprint_task(graph_version_id: str, actor_id: str) -> None:
    from apps.users.models import User
    BuildDiagnosticBlueprintService().execute(graph_version_id,User.objects.get(id=actor_id))

@shared_task(name="self_study.finalize_diagnostic_placement")
def finalize_diagnostic_placement_task(diagnostic_id: str) -> None:
    FinalizeDiagnosticPlacementService().execute(diagnostic_id)

@shared_task(name="self_study.build_content_evidence")
def build_content_evidence_task(run_id: str) -> None:
    try:BuildContentEvidenceService().execute(run_id)
    except Exception:
        FailEvidenceMappingRunService().execute(run_id,"MAPPING_EVIDENCE_BUILD_FAILED");raise
@shared_task(name="self_study.generate_evidence_mapping_candidates")
def generate_evidence_candidates_task(run_id: str) -> None:
    try:GenerateEvidenceMappingCandidatesService().execute(run_id)
    except Exception:
        FailEvidenceMappingRunService().execute(run_id,"MAPPING_CANDIDATE_GENERATION_FAILED");raise
@shared_task(name="self_study.evaluate_curriculum_coverage")
def evaluate_curriculum_coverage_task(run_id: str) -> None:
    try:EvaluateCurriculumCoverageService().execute(run_id)
    except Exception:
        FailEvidenceMappingRunService().execute(run_id,"COVERAGE_EVALUATION_FAILED");raise


@shared_task(name="self_study.create_bridge_plan")
def create_bridge_plan_task(run_id: str) -> None:
    try:
        CreateBridgePlanService().execute(run_id)
    except Exception as exc:
        FailBridgePlanningRunService().execute(run_id, "BRIDGE_PLAN_GENERATION_FAILED", str(exc))
        raise


@shared_task(name="self_study.finalize_bridge_plan")
def finalize_bridge_plan_task(run_id: str) -> None:
    try:
        FinalizeBridgePlanService().execute(run_id)
    except Exception as exc:
        FailBridgePlanningRunService().execute(run_id, "BRIDGE_PLAN_FINALIZATION_FAILED", str(exc))
        raise


@shared_task(name="self_study.assemble_teaching_preparation")
def assemble_teaching_preparation_task(run_id: str) -> None:
    try:
        AssembleTeachingPreparationService().execute(run_id)
    except Exception as exc:
        FailTeachingPreparationRunService().execute(run_id, "TEACHING_PREPARATION_ASSEMBLY_FAILED", str(exc))
        raise


@shared_task(name="self_study.publish_teaching_retrieval")
def publish_teaching_retrieval_task(retrieval_manifest_id: str) -> None:
    VerifyTeachingRetrievalPublicationService().execute(retrieval_manifest_id)


@shared_task(name="self_study.evaluate_teaching_readiness")
def evaluate_teaching_readiness_task(manifest_id: str) -> None:
    try:
        EvaluateTeachingReadinessService().execute(manifest_id)
    except Exception as exc:
        manifest = __import__("apps.self_study.teaching_models", fromlist=["TeachingPreparationManifest"]).TeachingPreparationManifest.objects.filter(id=manifest_id).select_related("run").first()
        if manifest:
            FailTeachingPreparationRunService().execute(manifest.run_id, "TEACHING_READINESS_EVALUATION_FAILED", str(exc))
        raise


@shared_task(name="self_study.prepare_teaching_turn")
def prepare_teaching_turn_task(session_id: str) -> None:
    GenerateTeachingTurnService().execute(session_id)


@shared_task(name="self_study.generate_teaching_turn")
def generate_teaching_turn_task(session_id: str) -> None:
    GenerateTeachingTurnService().execute(session_id)


@shared_task(name="self_study.record_teaching_evidence")
def record_teaching_evidence_task(session_id: str) -> None:
    # Identifier-only handoff to the existing evidence/mastery boundary. The
    # session remains awaiting governed evaluation; no mastery is written here.
    session = __import__("apps.self_study.orchestration_models", fromlist=["SelfStudyTeachingSession"]).SelfStudyTeachingSession.objects.get(id=session_id)
    RequestEvidenceEvaluationService().execute(session_id, session.learner, expected_version=session.version)


@shared_task(name="self_study.advance_teaching_session")
def advance_teaching_session_task(session_id: str) -> None:
    AdvanceTeachingSessionService().execute(session_id)
