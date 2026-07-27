from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from ..application.diagnostic_services import CreateEntryDiagnosticService, DiagnosticDeliveryService
from ..application.orchestration_services import (
    CreateTeachingSessionService,
    GenerateTeachingTurnService,
    PauseTeachingSessionService,
    RecordLearnerTurnService,
    ResumeTeachingSessionService,
    StartTeachingSessionService,
)
from ..bridge_models import BridgePlan, BridgePlanNode, BridgePlanStatus, MaterialFeasibility
from ..diagnostic_models import DiagnosticPlacementProfile, DiagnosticStatus, ProfileNodeClassification, ProfileStatus
from ..domain.workspace import WorkspaceBlockerCode
from ..models import IntentStatus
from ..orchestration_models import (
    SelfStudyTeachingSession,
    SelfStudyTeachingSessionState,
    TeachingSessionNode,
    TeachingSessionNodeState,
    TeachingTurn,
    TeachingTurnActor,
    TeachingTurnCitation,
)
from ..teaching_models import TeachingPreparationManifestStatus
from ..workspace_models import SelfStudyWorkspace, SelfStudyWorkspaceStatus
from .workspace_services import ensure_workspace_access


class ExperienceBlockerCode:
    DIAGNOSTIC_DISCLOSURE_INCOMPLETE = "DIAGNOSTIC_DISCLOSURE_INCOMPLETE"
    DIAGNOSTIC_SESSION_NOT_FOUND = "DIAGNOSTIC_SESSION_NOT_FOUND"
    DIAGNOSTIC_SESSION_NOT_OWNED = "DIAGNOSTIC_SESSION_NOT_OWNED"
    DIAGNOSTIC_SCORING_PENDING = "DIAGNOSTIC_SCORING_PENDING"
    PLACEMENT_SUMMARY_UNAVAILABLE = "PLACEMENT_SUMMARY_UNAVAILABLE"
    PLACEMENT_RESULT_STALE = "PLACEMENT_RESULT_STALE"
    PLAN_NOT_AVAILABLE = "PLAN_NOT_AVAILABLE"
    PLAN_GENERATION_PENDING = "PLAN_GENERATION_PENDING"
    PLAN_GENERATION_FAILED = "PLAN_GENERATION_FAILED"
    PLAN_APPROVAL_REQUIRED = "PLAN_APPROVAL_REQUIRED"
    PLAN_NOT_ACTIVE = "PLAN_NOT_ACTIVE"
    PLAN_STALE = "PLAN_STALE"
    PLAN_INVALIDATED = "PLAN_INVALIDATED"
    PLAN_SUPERSEDED = "PLAN_SUPERSEDED"
    PLAN_HAS_MISSING_MATERIALS = "PLAN_HAS_MISSING_MATERIALS"
    PLAN_HAS_PARTIAL_MATERIALS = "PLAN_HAS_PARTIAL_MATERIALS"
    PLAN_HAS_CONFLICTING_MATERIALS = "PLAN_HAS_CONFLICTING_MATERIALS"
    PLAN_HAS_UNSUPPORTED_OUTCOMES = "PLAN_HAS_UNSUPPORTED_OUTCOMES"
    TEACHING_NOT_PREPARED = "TEACHING_NOT_PREPARED"
    TEACHING_RETRIEVAL_NOT_READY = "TEACHING_RETRIEVAL_NOT_READY"
    LEARNING_START_NOT_ALLOWED = "LEARNING_START_NOT_ALLOWED"
    LEARNING_STUDIO_NOT_READY = "LEARNING_STUDIO_NOT_READY"
    LEARNING_SESSION_NOT_FOUND = "LEARNING_SESSION_NOT_FOUND"
    LEARNING_SESSION_NOT_OWNED = "LEARNING_SESSION_NOT_OWNED"
    LEARNING_SESSION_STALE = "LEARNING_SESSION_STALE"
    LEARNING_SESSION_INVALIDATED = "LEARNING_SESSION_INVALIDATED"
    LEARNING_SESSION_BLOCKED = "LEARNING_SESSION_BLOCKED"
    TEACHING_TURN_PENDING = "TEACHING_TURN_PENDING"
    TEACHING_TURN_FAILED = "TEACHING_TURN_FAILED"
    TEACHING_CITATION_UNAVAILABLE = "TEACHING_CITATION_UNAVAILABLE"
    CURRENT_NODE_NOT_READY = "CURRENT_NODE_NOT_READY"
    CURRENT_NODE_BLOCKED = "CURRENT_NODE_BLOCKED"
    CURRENT_NODE_COMPLETE = "CURRENT_NODE_COMPLETE"
    CONCEPT_CHECK_REQUIRED_NEXT = "CONCEPT_CHECK_REQUIRED_NEXT"
    PLAN_NODE_ADVANCE_NOT_ALLOWED = "PLAN_NODE_ADVANCE_NOT_ALLOWED"
    TEACHING_SESSION_VERSION_CONFLICT = "TEACHING_SESSION_VERSION_CONFLICT"
    LEARNER_MESSAGE_REQUIRED = "LEARNER_MESSAGE_REQUIRED"
    LEARNER_MESSAGE_TOO_LONG = "LEARNER_MESSAGE_TOO_LONG"
    LEARNER_MESSAGE_REJECTED = "LEARNER_MESSAGE_REJECTED"
    PROMPT_INJECTION_RISK = "PROMPT_INJECTION_RISK"
    SOURCE_NOT_AVAILABLE = "SOURCE_NOT_AVAILABLE"
    SOURCE_RETIRED = "SOURCE_RETIRED"
    SOURCE_UNSAFE = "SOURCE_UNSAFE"
    SOURCE_STALE = "SOURCE_STALE"


@dataclass(frozen=True)
class DiagnosticExperience:
    workspace_id: str
    diagnostic_session_id: str
    status: str
    can_start: bool
    can_resume: bool
    can_submit: bool
    progress: dict
    disclosure_complete: bool
    privacy_notice_version: str
    next_action: str
    blocker_codes: list[str]

    def to_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PlacementSummary:
    workspace_id: str
    diagnostic_result_id: str
    summary_state: str
    placement_band: str
    ready_domains: list[str]
    needs_review_domains: list[str]
    not_yet_ready_domains: list[str]
    confidence_label: str
    generated_at: str
    privacy_warnings: list[str]

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class SelfStudyDiagnosticExperienceService:
    def _workspace(self, *, workspace_id, actor) -> SelfStudyWorkspace:
        workspace = SelfStudyWorkspace.objects.select_related("intent", "active_diagnostic").get(id=workspace_id)
        ensure_workspace_access(actor, workspace)
        return workspace

    def _diagnostic(self, workspace: SelfStudyWorkspace):
        if workspace.active_diagnostic_id:
            return workspace.active_diagnostic
        if not workspace.intent_id:
            return None
        return workspace.intent.entry_diagnostics.order_by("-created_at").first()

    def experience(self, *, workspace_id, actor) -> DiagnosticExperience:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor)
        blockers: list[str] = []
        diagnostic = self._diagnostic(workspace)
        progress = {"answered": 0, "minimum_items": 0, "maximum_items": 0}
        disclosure_complete = False
        privacy_version = ""

        if workspace.status == SelfStudyWorkspaceStatus.ARCHIVED:
            blockers.append(WorkspaceBlockerCode.WORKSPACE_ARCHIVED.value)
            status = "BLOCKED"
        elif not workspace.intent_id:
            blockers.append(WorkspaceBlockerCode.INTENT_REQUIRED.value)
            status = "NOT_READY"
        elif workspace.intent.status != IntentStatus.ACTIVE:
            blockers.append(WorkspaceBlockerCode.INTENT_INCOMPLETE.value)
            status = "NOT_READY"
        elif diagnostic is None:
            status = "READY_TO_START"
        else:
            disclosure_complete = bool(diagnostic.purpose_disclosed_at)
            privacy_version = str(diagnostic.policy_snapshot.policy_version)
            progress = {
                "answered": diagnostic.responses.count(),
                "minimum_items": diagnostic.minimum_items,
                "maximum_items": diagnostic.maximum_items,
            }
            if diagnostic.status == DiagnosticStatus.READY:
                status = "READY_TO_START"
            elif diagnostic.status == DiagnosticStatus.IN_PROGRESS:
                status = "IN_PROGRESS"
            elif diagnostic.status == DiagnosticStatus.EVALUATING:
                blockers.append(ExperienceBlockerCode.DIAGNOSTIC_SCORING_PENDING)
                status = "AWAITING_SCORING"
            elif diagnostic.status in {DiagnosticStatus.COMPLETED, DiagnosticStatus.INCONCLUSIVE, DiagnosticStatus.CHALLENGED}:
                status = "COMPLETE"
            elif diagnostic.status in {DiagnosticStatus.EXPIRED, DiagnosticStatus.SUPERSEDED}:
                blockers.append(WorkspaceBlockerCode.DIAGNOSTIC_INVALIDATED.value)
                status = "STALE"
            else:
                blockers.append(ExperienceBlockerCode.DIAGNOSTIC_SESSION_NOT_FOUND)
                status = "BLOCKED"

        return DiagnosticExperience(
            workspace_id=str(workspace.id),
            diagnostic_session_id=str(diagnostic.id) if diagnostic else "",
            status=status,
            can_start=status == "READY_TO_START" and not diagnostic,
            can_resume=bool(diagnostic and diagnostic.status in {DiagnosticStatus.READY, DiagnosticStatus.IN_PROGRESS}),
            can_submit=bool(diagnostic and diagnostic.status == DiagnosticStatus.IN_PROGRESS),
            progress=progress,
            disclosure_complete=disclosure_complete,
            privacy_notice_version=privacy_version,
            next_action="diagnostic" if status in {"READY_TO_START", "IN_PROGRESS"} else "summary" if status == "COMPLETE" else "workspace",
            blocker_codes=blockers,
        )

    @transaction.atomic
    def start(self, *, workspace_id, actor, purpose_acknowledged: bool):
        workspace = SelfStudyWorkspace.objects.select_for_update().select_related("intent").get(id=workspace_id)
        ensure_workspace_access(actor, workspace, mutate=True)
        if workspace.status == SelfStudyWorkspaceStatus.ARCHIVED:
            raise ValidationError("Archived workspaces cannot start diagnostics.", code=WorkspaceBlockerCode.WORKSPACE_ARCHIVED.value)
        if not workspace.intent_id:
            raise ValidationError("Complete the workspace intent before diagnostic launch.", code=WorkspaceBlockerCode.DIAGNOSTIC_NOT_READY.value)
        diagnostic, replayed = CreateEntryDiagnosticService().execute(
            intent_id=workspace.intent_id,
            actor=actor,
            purpose_acknowledged=purpose_acknowledged,
        )
        diagnostic = DiagnosticDeliveryService().start(diagnostic.id, actor)
        workspace.active_diagnostic = diagnostic
        workspace.version += 1
        workspace.save(update_fields=["active_diagnostic", "version", "updated_at"])
        return diagnostic, replayed

    @transaction.atomic
    def resume(self, *, workspace_id, actor):
        workspace = SelfStudyWorkspace.objects.select_for_update().select_related("intent", "active_diagnostic").get(id=workspace_id)
        ensure_workspace_access(actor, workspace, mutate=True)
        diagnostic = self._diagnostic(workspace)
        if diagnostic is None:
            raise ValidationError("No diagnostic session is available.", code=ExperienceBlockerCode.DIAGNOSTIC_SESSION_NOT_FOUND)
        if diagnostic.learner_id != workspace.learner_id or diagnostic.tenant_id != workspace.tenant_id:
            raise PermissionDenied(ExperienceBlockerCode.DIAGNOSTIC_SESSION_NOT_OWNED)
        diagnostic = DiagnosticDeliveryService().start(diagnostic.id, actor)
        workspace.active_diagnostic = diagnostic
        workspace.version += 1
        workspace.save(update_fields=["active_diagnostic", "version", "updated_at"])
        return diagnostic


class SelfStudyPlacementSummaryService:
    def execute(self, *, workspace_id, actor) -> PlacementSummary:
        workspace = SelfStudyWorkspace.objects.select_related("intent", "active_diagnostic").get(id=workspace_id)
        ensure_workspace_access(actor, workspace)
        diagnostic = workspace.active_diagnostic or (workspace.intent.entry_diagnostics.order_by("-created_at").first() if workspace.intent_id else None)
        if diagnostic is None:
            raise ValidationError("No diagnostic result is available.", code=ExperienceBlockerCode.PLACEMENT_SUMMARY_UNAVAILABLE)
        try:
            profile = diagnostic.placement_profile
        except DiagnosticPlacementProfile.DoesNotExist as exc:
            raise ValidationError("Placement summary is not available.", code=ExperienceBlockerCode.PLACEMENT_SUMMARY_UNAVAILABLE) from exc
        if profile.status in {ProfileStatus.SUPERSEDED, ProfileStatus.INVALIDATED}:
            raise ValidationError("Placement result is stale.", code=ExperienceBlockerCode.PLACEMENT_RESULT_STALE)

        ready: list[str] = []
        review: list[str] = []
        not_ready: list[str] = []
        for row in profile.classified_nodes.select_related("graph_node").order_by("graph_node__ordinal", "graph_node__stable_key"):
            label = row.graph_node.title
            if row.classification in {ProfileNodeClassification.FRONTIER, ProfileNodeClassification.DEMONSTRATED}:
                ready.append(label)
            elif row.classification == ProfileNodeClassification.GAP:
                not_ready.append(label)
            else:
                review.append(label)

        confidence = "low"
        if profile.overall_confidence >= Decimal("0.75"):
            confidence = "high"
        elif profile.overall_confidence >= Decimal("0.50"):
            confidence = "moderate"

        return PlacementSummary(
            workspace_id=str(workspace.id),
            diagnostic_result_id=str(diagnostic.id),
            summary_state=profile.status,
            placement_band="starting point identified" if profile.status == ProfileStatus.FINAL else "needs review",
            ready_domains=ready[:8],
            needs_review_domains=review[:8],
            not_yet_ready_domains=not_ready[:8],
            confidence_label=confidence,
            generated_at=profile.created_at.isoformat(),
            privacy_warnings=[
                "This is not a grade and does not award mastery.",
                "Item-level scores and adaptive routing details are private and hidden.",
            ],
        )


class SelfStudyPlanExperienceService:
    def _workspace(self, *, workspace_id, actor) -> SelfStudyWorkspace:
        workspace = SelfStudyWorkspace.objects.select_related("intent", "active_bridge_plan", "active_teaching_preparation", "active_teaching_session").get(id=workspace_id)
        ensure_workspace_access(actor, workspace)
        return workspace

    def _plan(self, workspace: SelfStudyWorkspace) -> BridgePlan | None:
        if workspace.active_bridge_plan_id:
            return workspace.active_bridge_plan
        if not workspace.intent_id:
            return None
        return workspace.intent.bridge_plans.order_by("-generated_at").first()

    def experience(self, *, workspace_id, actor) -> dict:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor)
        plan = self._plan(workspace)
        if plan is None:
            return {
                "workspace_id": str(workspace.id),
                "bridge_plan_id": "",
                "plan_status": "NOT_AVAILABLE",
                "approval_status": "NONE",
                "active": False,
                "target_scope": {},
                "estimated_node_count": 0,
                "required_node_count": 0,
                "optional_node_count": 0,
                "blocked_node_count": 0,
                "ready_node_count": 0,
                "next_plan_node_id": "",
                "can_start_learning": False,
                "blocker_codes": [ExperienceBlockerCode.PLAN_NOT_AVAILABLE],
                "findings": [],
            }

        nodes = list(plan.nodes.order_by("topological_layer", "ordinal", "graph_node_id"))
        blockers = self._plan_blockers(plan, workspace, nodes)
        next_node = next((node for node in nodes if node.is_required and not node.blocker_count), nodes[0] if nodes else None)
        findings = list(plan.findings.order_by("-blocking", "severity", "code").values("code", "severity", "blocking", "scope")[:20])
        return {
            "workspace_id": str(workspace.id),
            "bridge_plan_id": str(plan.id),
            "plan_status": plan.status,
            "approval_status": "APPROVED" if plan.approved_at else "REVIEW_REQUIRED",
            "active": plan.status == BridgePlanStatus.ACTIVE,
            "target_scope": plan.target_set_snapshot,
            "estimated_node_count": len(nodes),
            "required_node_count": sum(1 for node in nodes if node.is_required),
            "optional_node_count": sum(1 for node in nodes if not node.is_required),
            "blocked_node_count": sum(1 for node in nodes if node.blocker_count),
            "ready_node_count": sum(1 for node in nodes if not node.blocker_count and node.material_feasibility == MaterialFeasibility.FEASIBLE),
            "next_plan_node_id": str(next_node.id) if next_node else "",
            "can_start_learning": not blockers and bool(workspace.active_teaching_preparation_id),
            "blocker_codes": blockers,
            "findings": findings,
        }

    def nodes(self, *, workspace_id, actor) -> list[dict]:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor)
        plan = self._plan(workspace)
        if plan is None:
            return []
        return [self._node_summary(node, index) for index, node in enumerate(plan.nodes.select_related("graph_node").order_by("topological_layer", "ordinal", "graph_node_id"), start=1)]

    def findings(self, *, workspace_id, actor) -> list[dict]:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor)
        plan = self._plan(workspace)
        if plan is None:
            return []
        return list(plan.findings.order_by("-blocking", "severity", "code").values("id", "code", "severity", "blocking", "scope", "details"))

    def start_learning(self, *, workspace_id, actor) -> dict:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor)
        blockers = self.experience(workspace_id=workspace.id, actor=actor)["blocker_codes"]
        if blockers:
            raise ValidationError("Learning cannot start from this plan state.", code=ExperienceBlockerCode.LEARNING_START_NOT_ALLOWED)
        session = workspace.active_teaching_session or (workspace.intent.teaching_sessions.order_by("-created_at").first() if workspace.intent_id else None)
        if not session:
            raise ValidationError("No teaching session is available.", code=WorkspaceBlockerCode.LEARNING_SESSION_UNAVAILABLE.value)
        return {
            "workspace_id": str(workspace.id),
            "teaching_session_id": str(session.id),
            "state": session.state,
            "target_route": f"/dashboard/self-study/{workspace.id}/learn",
        }

    def _plan_blockers(self, plan: BridgePlan, workspace: SelfStudyWorkspace, nodes: list[BridgePlanNode]) -> list[str]:
        blockers: list[str] = []
        if workspace.status == SelfStudyWorkspaceStatus.ARCHIVED:
            blockers.append(WorkspaceBlockerCode.WORKSPACE_ARCHIVED.value)
        if plan.status == BridgePlanStatus.STALE:
            blockers.append(ExperienceBlockerCode.PLAN_STALE)
        elif plan.status == BridgePlanStatus.INVALIDATED:
            blockers.append(ExperienceBlockerCode.PLAN_INVALIDATED)
        elif plan.status == BridgePlanStatus.SUPERSEDED:
            blockers.append(ExperienceBlockerCode.PLAN_SUPERSEDED)
        elif plan.status != BridgePlanStatus.ACTIVE:
            blockers.append(ExperienceBlockerCode.PLAN_NOT_ACTIVE if plan.approved_at else ExperienceBlockerCode.PLAN_APPROVAL_REQUIRED)
        material_counts = Counter(node.material_feasibility for node in nodes if node.is_required)
        if material_counts.get(MaterialFeasibility.MATERIAL_MISSING):
            blockers.append(ExperienceBlockerCode.PLAN_HAS_MISSING_MATERIALS)
        if material_counts.get(MaterialFeasibility.PARTIALLY_FEASIBLE):
            blockers.append(ExperienceBlockerCode.PLAN_HAS_PARTIAL_MATERIALS)
        if material_counts.get(MaterialFeasibility.MATERIAL_CONFLICTING):
            blockers.append(ExperienceBlockerCode.PLAN_HAS_CONFLICTING_MATERIALS)
        if not workspace.active_teaching_preparation_id or workspace.active_teaching_preparation.status != TeachingPreparationManifestStatus.READY:
            blockers.append(ExperienceBlockerCode.TEACHING_NOT_PREPARED)
        if workspace.active_teaching_session_id and workspace.active_teaching_session.state in {SelfStudyTeachingSessionState.STALE, SelfStudyTeachingSessionState.INVALIDATED}:
            blockers.append(WorkspaceBlockerCode.LEARNING_SESSION_UNAVAILABLE.value)
        return list(dict.fromkeys(blockers))

    def _node_summary(self, node: BridgePlanNode, index: int) -> dict:
        blocker_codes: list[str] = []
        if node.material_feasibility == MaterialFeasibility.MATERIAL_MISSING:
            blocker_codes.append(ExperienceBlockerCode.PLAN_HAS_MISSING_MATERIALS)
        elif node.material_feasibility == MaterialFeasibility.PARTIALLY_FEASIBLE:
            blocker_codes.append(ExperienceBlockerCode.PLAN_HAS_PARTIAL_MATERIALS)
        elif node.material_feasibility == MaterialFeasibility.MATERIAL_CONFLICTING:
            blocker_codes.append(ExperienceBlockerCode.PLAN_HAS_CONFLICTING_MATERIALS)
        if node.blocker_count:
            blocker_codes.append(ExperienceBlockerCode.PLAN_NOT_ACTIVE)
        return {
            "plan_node_id": str(node.id),
            "curriculum_node_id": str(node.graph_node_id),
            "node_type": node.node_type,
            "title": node.graph_node.title,
            "sequence_index": index,
            "disposition": node.learner_disposition,
            "coverage_state": node.coverage_state,
            "material_status": node.material_feasibility,
            "estimated_effort_label": "standard",
            "dependency_summary": {"dependency_count": node.dependency_count, "required": node.is_required},
            "blocked": bool(node.blocker_count or blocker_codes),
            "blocker_codes": list(dict.fromkeys(blocker_codes)),
            "finding_codes": [],
        }


class LearningStudioExperienceService:
    def _workspace(self, *, workspace_id, actor, mutate: bool = False) -> SelfStudyWorkspace:
        queryset = SelfStudyWorkspace.objects.select_related(
            "intent",
            "active_bridge_plan",
            "active_teaching_preparation",
            "active_teaching_session",
        )
        if mutate:
            queryset = queryset.select_for_update()
        workspace = queryset.get(id=workspace_id)
        ensure_workspace_access(actor, workspace, mutate=mutate)
        return workspace

    def _session(self, workspace: SelfStudyWorkspace) -> SelfStudyTeachingSession | None:
        if workspace.active_teaching_session_id:
            return workspace.active_teaching_session
        if not workspace.intent_id:
            return None
        return workspace.intent.teaching_sessions.select_related("current_session_node__graph_node").order_by("-created_at").first()

    def experience(self, *, workspace_id, actor) -> dict:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor)
        session = self._session(workspace)
        blockers = self._blockers(workspace, session)
        node = session.current_session_node if session and session.current_session_node_id else None
        return {
            "workspace_id": str(workspace.id),
            "teaching_session_id": str(session.id) if session else "",
            "session_version": session.version if session else 0,
            "bridge_plan_id": str(workspace.active_bridge_plan_id) if workspace.active_bridge_plan_id else "",
            "current_plan_node_id": str(node.bridge_node_id) if node else "",
            "current_curriculum_node_id": str(node.graph_node_id) if node else "",
            "session_status": session.state if session else "NOT_STARTED",
            "node_status": node.state if node else "NOT_SELECTED",
            "can_start": not session and not blockers,
            "can_resume": bool(session and session.state in {SelfStudyTeachingSessionState.PENDING, SelfStudyTeachingSessionState.PAUSED}),
            "can_send_message": bool(session and session.state == SelfStudyTeachingSessionState.AWAITING_LEARNER and not blockers),
            "can_pause": bool(session and session.state in {SelfStudyTeachingSessionState.ACTIVE, SelfStudyTeachingSessionState.AWAITING_LEARNER}),
            "can_request_recap": bool(session and session.state == SelfStudyTeachingSessionState.AWAITING_LEARNER and not blockers),
            "can_advance": bool(session and session.state == SelfStudyTeachingSessionState.NODE_COMPLETE and not blockers),
            "can_start_concept_check": bool(session and session.state == SelfStudyTeachingSessionState.NODE_COMPLETE),
            "progress_summary": self.progress(workspace=workspace, session=session),
            "blocker_codes": blockers,
            "next_action": self._next_action(session, blockers),
        }

    @transaction.atomic
    def start(self, *, workspace_id, actor) -> dict:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor, mutate=True)
        session = self._session(workspace)
        blockers = self._blockers(workspace, session)
        if blockers and not session:
            raise ValidationError("Learning studio is not ready.", code=ExperienceBlockerCode.LEARNING_STUDIO_NOT_READY)
        if not session:
            if not workspace.active_teaching_preparation_id:
                raise ValidationError("Teaching preparation is required.", code=ExperienceBlockerCode.TEACHING_NOT_PREPARED)
            session, _created = CreateTeachingSessionService().execute(
                preparation_manifest_id=workspace.active_teaching_preparation_id,
                actor=actor,
                idempotency_key=f"workspace:{workspace.id}",
            )
            workspace.active_teaching_session = session
            workspace.version += 1
            workspace.save(update_fields=["active_teaching_session", "version", "updated_at"])
        if session.state in {SelfStudyTeachingSessionState.PENDING, SelfStudyTeachingSessionState.PAUSED}:
            service = StartTeachingSessionService() if session.state == SelfStudyTeachingSessionState.PENDING else ResumeTeachingSessionService()
            session = service.execute(session.id, actor, expected_version=session.version)
        return self.experience(workspace_id=workspace.id, actor=actor)

    @transaction.atomic
    def resume(self, *, workspace_id, actor) -> dict:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor, mutate=True)
        session = self._require_session(workspace)
        if session.state == SelfStudyTeachingSessionState.PAUSED:
            ResumeTeachingSessionService().execute(session.id, actor, expected_version=session.version)
        elif session.state == SelfStudyTeachingSessionState.PENDING:
            StartTeachingSessionService().execute(session.id, actor, expected_version=session.version)
        return self.experience(workspace_id=workspace.id, actor=actor)

    @transaction.atomic
    def pause(self, *, workspace_id, actor) -> dict:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor, mutate=True)
        session = self._require_session(workspace)
        PauseTeachingSessionService().execute(session.id, actor, expected_version=session.version, reason="LEARNER_PAUSED")
        return self.experience(workspace_id=workspace.id, actor=actor)

    def turns(self, *, workspace_id, actor) -> list[dict]:
        session = self._require_owned_session(workspace_id=workspace_id, actor=actor)
        citations_by_turn: dict[str, list[dict]] = {}
        for citation in TeachingTurnCitation.objects.filter(turn__session=session).select_related("resource").order_by("turn_id", "id"):
            citations_by_turn.setdefault(str(citation.turn_id), []).append(self._citation_view(citation))
        return [self._turn_view(turn, citations_by_turn.get(str(turn.id), [])) for turn in session.turns.order_by("sequence_number", "id")]

    @transaction.atomic
    def submit_turn(self, *, workspace_id, actor, text: str, idempotency_key: str, expected_version: int) -> dict:
        text = text.strip()
        if not text:
            raise ValidationError("Learner message is required.", code=ExperienceBlockerCode.LEARNER_MESSAGE_REQUIRED)
        if len(text) > 12000:
            raise ValidationError("Learner message is too long.", code=ExperienceBlockerCode.LEARNER_MESSAGE_TOO_LONG)
        workspace = self._workspace(workspace_id=workspace_id, actor=actor, mutate=True)
        session = self._require_session(workspace)
        if session.version != expected_version:
            raise ValidationError(
                "Teaching session version changed before the learner response was submitted.",
                code=ExperienceBlockerCode.TEACHING_SESSION_VERSION_CONFLICT,
            )
        if session.state != SelfStudyTeachingSessionState.AWAITING_LEARNER:
            raise ValidationError(
                "The teaching session is not awaiting a learner response.",
                code=ExperienceBlockerCode.TEACHING_TURN_PENDING,
            )
        turn = RecordLearnerTurnService().execute(
            session.id,
            actor,
            text=text,
            expected_version=session.version,
            idempotency_key=idempotency_key,
        )
        return self._turn_view(turn, [])

    @transaction.atomic
    def next_turn(self, *, workspace_id, actor, learner_input: str = "") -> dict:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor, mutate=True)
        session = self._require_session(workspace)
        turn = GenerateTeachingTurnService().execute(session.id, learner_input=learner_input)
        citations = [self._citation_view(citation) for citation in turn.citations.select_related("resource").order_by("id")]
        return self._turn_view(turn, citations)

    def current_node(self, *, workspace_id, actor) -> dict:
        session = self._require_owned_session(workspace_id=workspace_id, actor=actor)
        if not session.current_session_node_id:
            raise ValidationError("No current teaching node.", code=ExperienceBlockerCode.CURRENT_NODE_NOT_READY)
        total = session.nodes.count()
        return self._node_view(session.current_session_node, total)

    def progress_response(self, *, workspace_id, actor) -> dict:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor)
        return self.progress(workspace=workspace, session=self._session(workspace))

    def citations(self, *, workspace_id, actor) -> list[dict]:
        session = self._require_owned_session(workspace_id=workspace_id, actor=actor)
        return [self._citation_view(citation) for citation in TeachingTurnCitation.objects.filter(turn__session=session).select_related("resource").order_by("turn__sequence_number", "id")]

    def progress(self, *, workspace: SelfStudyWorkspace, session: SelfStudyTeachingSession | None) -> dict:
        if not session:
            return {"completed_teaching_segments": 0, "total_teaching_segments": 0, "current_index": 0, "concept_check_ready": False}
        nodes = list(session.nodes.order_by("topological_layer", "plan_ordinal", "id"))
        current_id = session.current_session_node_id
        current_index = next((index for index, node in enumerate(nodes, start=1) if node.id == current_id), 0)
        return {
            "completed_teaching_segments": sum(1 for node in nodes if node.state == TeachingSessionNodeState.NODE_COMPLETE),
            "total_teaching_segments": len(nodes),
            "current_index": current_index,
            "concept_check_ready": session.state == SelfStudyTeachingSessionState.NODE_COMPLETE,
            "next_label": "Ready for concept check" if session.state == SelfStudyTeachingSessionState.NODE_COMPLETE else "Learning with Abbot",
        }

    def _blockers(self, workspace: SelfStudyWorkspace, session: SelfStudyTeachingSession | None) -> list[str]:
        blockers: list[str] = []
        if workspace.status == SelfStudyWorkspaceStatus.ARCHIVED:
            blockers.append(WorkspaceBlockerCode.WORKSPACE_ARCHIVED.value)
        if not workspace.active_bridge_plan_id:
            blockers.append(ExperienceBlockerCode.PLAN_NOT_AVAILABLE)
        elif workspace.active_bridge_plan.status in {BridgePlanStatus.STALE, BridgePlanStatus.INVALIDATED, BridgePlanStatus.SUPERSEDED}:
            blockers.append(
                {
                    BridgePlanStatus.STALE: ExperienceBlockerCode.PLAN_STALE,
                    BridgePlanStatus.INVALIDATED: ExperienceBlockerCode.PLAN_INVALIDATED,
                    BridgePlanStatus.SUPERSEDED: ExperienceBlockerCode.PLAN_SUPERSEDED,
                }[workspace.active_bridge_plan.status]
            )
        elif workspace.active_bridge_plan.status != BridgePlanStatus.ACTIVE:
            blockers.append(ExperienceBlockerCode.PLAN_NOT_ACTIVE)
        if not workspace.active_teaching_preparation_id or workspace.active_teaching_preparation.status != TeachingPreparationManifestStatus.READY:
            blockers.append(ExperienceBlockerCode.TEACHING_NOT_PREPARED)
        if session and session.state == SelfStudyTeachingSessionState.STALE:
            blockers.append(ExperienceBlockerCode.LEARNING_SESSION_STALE)
        if session and session.state == SelfStudyTeachingSessionState.INVALIDATED:
            blockers.append(ExperienceBlockerCode.LEARNING_SESSION_INVALIDATED)
        if session and session.state == SelfStudyTeachingSessionState.BLOCKED:
            blockers.append(ExperienceBlockerCode.LEARNING_SESSION_BLOCKED)
        return list(dict.fromkeys(blockers))

    def _next_action(self, session: SelfStudyTeachingSession | None, blockers: list[str]) -> str:
        if blockers:
            return "resolve_blockers"
        if not session:
            return "start_learning"
        if session.state == SelfStudyTeachingSessionState.PAUSED:
            return "resume_learning"
        if session.state == SelfStudyTeachingSessionState.AWAITING_LEARNER:
            return "send_response"
        if session.state == SelfStudyTeachingSessionState.NODE_COMPLETE:
            return "concept_check"
        if session.state == SelfStudyTeachingSessionState.COMPLETED:
            return "plan_complete"
        return "continue_learning"

    def _require_session(self, workspace: SelfStudyWorkspace) -> SelfStudyTeachingSession:
        session = self._session(workspace)
        if not session:
            raise ValidationError("Learning session is not available.", code=ExperienceBlockerCode.LEARNING_SESSION_NOT_FOUND)
        if session.learner_id != workspace.learner_id or session.tenant_id != workspace.tenant_id:
            raise PermissionDenied(ExperienceBlockerCode.LEARNING_SESSION_NOT_OWNED)
        return session

    def _require_owned_session(self, *, workspace_id, actor) -> SelfStudyTeachingSession:
        workspace = self._workspace(workspace_id=workspace_id, actor=actor)
        return self._require_session(workspace)

    def _node_view(self, node: TeachingSessionNode, total: int) -> dict:
        return {
            "plan_node_id": str(node.bridge_node_id),
            "curriculum_node_id": str(node.graph_node_id),
            "node_type": node.graph_node.node_type,
            "title": node.graph_node.title,
            "learning_objective": getattr(node.graph_node, "description", ""),
            "sequence_index": node.plan_ordinal,
            "total_sequence_count": total,
            "dependency_summary": {"topological_layer": node.topological_layer},
            "coverage_state": node.teaching_pack.coverage_state,
            "material_status": node.teaching_pack.material_feasibility,
            "teaching_pack_id": str(node.teaching_pack_id),
            "citations_available": bool(node.permitted_roles),
            "blocked": node.state == TeachingSessionNodeState.BLOCKED,
            "blocker_codes": [ExperienceBlockerCode.CURRENT_NODE_BLOCKED] if node.state == TeachingSessionNodeState.BLOCKED else [],
        }

    def _turn_view(self, turn: TeachingTurn, citations: list[dict]) -> dict:
        return {
            "turn_id": str(turn.id),
            "role": turn.actor,
            "action_type": turn.action,
            "status": "FAILED" if turn.failure_code else "READY",
            "content": turn.response_text,
            "created_at": turn.created_at.isoformat(),
            "citations": citations,
            "rationale_codes": [turn.failure_code] if turn.failure_code else [],
            "requires_response": turn.actor == TeachingTurnActor.ABBOT and turn.action in {"ASK", "PRACTICE", "CHECK_UNDERSTANDING", "REFLECT"},
            "safe_transition": "concept_check" if turn.session.state == SelfStudyTeachingSessionState.NODE_COMPLETE else "awaiting_learner",
        }

    def _citation_view(self, citation: TeachingTurnCitation) -> dict:
        payload = citation.citation or {}
        return {
            "citation_id": str(citation.id),
            "resource_id": str(citation.resource_id),
            "resource_title": getattr(citation.resource, "title", ""),
            "page": payload.get("page", payload.get("page_number", "")),
            "segment": payload.get("segment", payload.get("label", "")),
            "excerpt": str(payload.get("excerpt", ""))[:500],
            "evidence_unit_id": str(citation.evidence_unit_id),
            "mapping_id": str(citation.teaching_pack_resource.accepted_mapping_id),
            "source_state": "ACTIVE",
        }
