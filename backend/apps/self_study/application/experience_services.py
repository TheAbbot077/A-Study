from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from ..application.diagnostic_services import CreateEntryDiagnosticService, DiagnosticDeliveryService
from ..bridge_models import BridgePlan, BridgePlanNode, BridgePlanStatus, MaterialFeasibility
from ..diagnostic_models import DiagnosticPlacementProfile, DiagnosticStatus, ProfileNodeClassification, ProfileStatus
from ..domain.workspace import WorkspaceBlockerCode
from ..models import IntentStatus
from ..orchestration_models import SelfStudyTeachingSessionState
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
