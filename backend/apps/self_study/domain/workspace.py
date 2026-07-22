from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SelfStudyNextAction(StrEnum):
    CREATE_WORKSPACE = "CREATE_WORKSPACE"
    COMPLETE_INTENT = "COMPLETE_INTENT"
    UPLOAD_MATERIALS = "UPLOAD_MATERIALS"
    WAIT_FOR_PROCESSING = "WAIT_FOR_PROCESSING"
    RESOLVE_MATERIAL_ISSUES = "RESOLVE_MATERIAL_ISSUES"
    START_DIAGNOSTIC = "START_DIAGNOSTIC"
    RESUME_DIAGNOSTIC = "RESUME_DIAGNOSTIC"
    WAIT_FOR_MAPPING = "WAIT_FOR_MAPPING"
    WAIT_FOR_BRIDGE_PLAN = "WAIT_FOR_BRIDGE_PLAN"
    REVIEW_STUDY_PLAN = "REVIEW_STUDY_PLAN"
    WAIT_FOR_TEACHING_PREPARATION = "WAIT_FOR_TEACHING_PREPARATION"
    START_LEARNING = "START_LEARNING"
    RESUME_LEARNING = "RESUME_LEARNING"
    CONTACT_SUPPORT = "CONTACT_SUPPORT"
    NO_ACTION_AVAILABLE = "NO_ACTION_AVAILABLE"


class WorkspaceBlockerCode(StrEnum):
    WORKSPACE_NOT_FOUND = "WORKSPACE_NOT_FOUND"
    WORKSPACE_ARCHIVED = "WORKSPACE_ARCHIVED"
    WORKSPACE_STALE = "WORKSPACE_STALE"
    WORKSPACE_OWNER_MISMATCH = "WORKSPACE_OWNER_MISMATCH"
    INTENT_REQUIRED = "INTENT_REQUIRED"
    INTENT_INCOMPLETE = "INTENT_INCOMPLETE"
    DIAGNOSTIC_DISCLOSURE_REQUIRED = "DIAGNOSTIC_DISCLOSURE_REQUIRED"
    RESOURCE_POLICY_ACKNOWLEDGEMENT_REQUIRED = "RESOURCE_POLICY_ACKNOWLEDGEMENT_REQUIRED"
    INTENT_POLICY_VERSION_STALE = "INTENT_POLICY_VERSION_STALE"
    CURRICULUM_UNRESOLVED = "CURRICULUM_UNRESOLVED"
    CURRICULUM_AMBIGUOUS = "CURRICULUM_AMBIGUOUS"
    CURRICULUM_UNAVAILABLE = "CURRICULUM_UNAVAILABLE"
    CURRICULUM_GRAPH_UNPUBLISHED = "CURRICULUM_GRAPH_UNPUBLISHED"
    CURRICULUM_GRAPH_SUPERSEDED = "CURRICULUM_GRAPH_SUPERSEDED"
    CURRICULUM_GRAPH_INVALIDATED = "CURRICULUM_GRAPH_INVALIDATED"
    MATERIALS_REQUIRED = "MATERIALS_REQUIRED"
    MATERIALS_PROCESSING = "MATERIALS_PROCESSING"
    MATERIAL_PROCESSING_FAILED = "MATERIAL_PROCESSING_FAILED"
    MATERIAL_UNSUPPORTED_FORMAT = "MATERIAL_UNSUPPORTED_FORMAT"
    MATERIAL_UNLICENSED = "MATERIAL_UNLICENSED"
    MATERIAL_UNSAFE = "MATERIAL_UNSAFE"
    MATERIAL_QUARANTINED = "MATERIAL_QUARANTINED"
    MATERIAL_RETIRED = "MATERIAL_RETIRED"
    MATERIAL_STALE = "MATERIAL_STALE"
    NO_ELIGIBLE_MATERIALS = "NO_ELIGIBLE_MATERIALS"
    DIAGNOSTIC_NOT_READY = "DIAGNOSTIC_NOT_READY"
    DIAGNOSTIC_IN_PROGRESS = "DIAGNOSTIC_IN_PROGRESS"
    DIAGNOSTIC_INVALIDATED = "DIAGNOSTIC_INVALIDATED"
    DIAGNOSTIC_RESULT_REQUIRED = "DIAGNOSTIC_RESULT_REQUIRED"
    COVERAGE_PENDING = "COVERAGE_PENDING"
    COVERAGE_BLOCKED = "COVERAGE_BLOCKED"
    BRIDGE_PLAN_PENDING = "BRIDGE_PLAN_PENDING"
    BRIDGE_PLAN_BLOCKED = "BRIDGE_PLAN_BLOCKED"
    TEACHING_PREPARATION_PENDING = "TEACHING_PREPARATION_PENDING"
    TEACHING_PREPARATION_BLOCKED = "TEACHING_PREPARATION_BLOCKED"
    LEARNING_SESSION_UNAVAILABLE = "LEARNING_SESSION_UNAVAILABLE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    TENANT_SCOPE_REQUIRED = "TENANT_SCOPE_REQUIRED"
    IDEMPOTENCY_CONFLICT = "IDEMPOTENCY_CONFLICT"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    UNEXPECTED_STATE = "UNEXPECTED_STATE"


ACTION_COPY = {
    SelfStudyNextAction.COMPLETE_INTENT: (
        "Tell Abbot what you want to learn",
        "Answer or resume the self-study intent questions so the governed pipeline has a safe learning goal.",
        "Answer intent questions",
    ),
    SelfStudyNextAction.UPLOAD_MATERIALS: (
        "Add your materials",
        "Upload the notes, PDFs, or documents you want Abbot to use as learner-provided evidence.",
        "Add materials",
    ),
    SelfStudyNextAction.WAIT_FOR_PROCESSING: (
        "We are processing your materials",
        "Abbot is extracting and validating your uploaded materials before they can support study planning.",
        "View materials",
    ),
    SelfStudyNextAction.RESOLVE_MATERIAL_ISSUES: (
        "Some materials need attention",
        "At least one material is blocked, failed, unsafe, retired, or otherwise ineligible.",
        "Review material issues",
    ),
    SelfStudyNextAction.START_DIAGNOSTIC: (
        "You are ready for your diagnostic",
        "The next safe step is the private entry diagnostic. Placement is not mastery.",
        "Start diagnostic",
    ),
    SelfStudyNextAction.RESUME_DIAGNOSTIC: (
        "Resume your diagnostic",
        "Continue the private diagnostic from where you left off.",
        "Resume diagnostic",
    ),
    SelfStudyNextAction.WAIT_FOR_MAPPING: (
        "Your material coverage is being checked",
        "Abbot is waiting for governed evidence mapping and coverage before planning a path.",
        "View workspace",
    ),
    SelfStudyNextAction.WAIT_FOR_BRIDGE_PLAN: (
        "Your study plan is being prepared",
        "Abbot is waiting for the governed bridge plan from your diagnostic boundary to your targets.",
        "View plan status",
    ),
    SelfStudyNextAction.REVIEW_STUDY_PLAN: (
        "Review your study plan",
        "A governed bridge plan is available for this workspace.",
        "Review plan",
    ),
    SelfStudyNextAction.WAIT_FOR_TEACHING_PREPARATION: (
        "Learning resources are being assembled",
        "Abbot is preparing citation-grounded teaching packs for the approved plan.",
        "View preparation status",
    ),
    SelfStudyNextAction.START_LEARNING: (
        "Start learning with Abbot",
        "The governed preparation is ready and a learner-facing session can begin.",
        "Start learning",
    ),
    SelfStudyNextAction.RESUME_LEARNING: (
        "Resume learning with Abbot",
        "Continue the active governed self-study teaching session.",
        "Resume learning",
    ),
    SelfStudyNextAction.CONTACT_SUPPORT: (
        "This workspace needs help",
        "The workspace is blocked, stale, or archived and cannot safely continue automatically.",
        "Contact support",
    ),
    SelfStudyNextAction.NO_ACTION_AVAILABLE: (
        "No safe next action is available",
        "Abbot could not determine a safe learner action from the current governed state.",
        "Refresh workspace",
    ),
}


@dataclass(frozen=True)
class NextActionProjection:
    code: str
    title: str
    explanation: str
    primary_cta_label: str
    target_route: str
    blocker_codes: tuple[str, ...]
    safe_ids: dict[str, str]
    safe_status_summary: dict[str, str]

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "explanation": self.explanation,
            "primary_cta_label": self.primary_cta_label,
            "target_route": self.target_route,
            "blocker_codes": list(self.blocker_codes),
            "safe_ids": dict(self.safe_ids),
            "safe_status_summary": dict(self.safe_status_summary),
        }


def build_next_action(
    code: SelfStudyNextAction,
    *,
    workspace_id: str,
    blockers: list[str] | tuple[str, ...] = (),
    safe_ids: dict[str, str] | None = None,
    summary: dict[str, str] | None = None,
) -> NextActionProjection:
    title, explanation, cta = ACTION_COPY.get(code, ACTION_COPY[SelfStudyNextAction.NO_ACTION_AVAILABLE])
    route_suffix = {
        SelfStudyNextAction.COMPLETE_INTENT: "intent",
        SelfStudyNextAction.UPLOAD_MATERIALS: "materials",
        SelfStudyNextAction.WAIT_FOR_PROCESSING: "materials",
        SelfStudyNextAction.RESOLVE_MATERIAL_ISSUES: "materials",
        SelfStudyNextAction.START_DIAGNOSTIC: "diagnostic",
        SelfStudyNextAction.RESUME_DIAGNOSTIC: "diagnostic",
        SelfStudyNextAction.WAIT_FOR_MAPPING: "",
        SelfStudyNextAction.WAIT_FOR_BRIDGE_PLAN: "plan",
        SelfStudyNextAction.REVIEW_STUDY_PLAN: "plan",
        SelfStudyNextAction.WAIT_FOR_TEACHING_PREPARATION: "plan",
        SelfStudyNextAction.START_LEARNING: "learn",
        SelfStudyNextAction.RESUME_LEARNING: "learn",
    }.get(code, "")
    base = f"/dashboard/self-study/{workspace_id}"
    target_route = f"{base}/{route_suffix}" if route_suffix else base
    return NextActionProjection(
        code=code.value,
        title=title,
        explanation=explanation,
        primary_cta_label=cta,
        target_route=target_route,
        blocker_codes=tuple(str(item) for item in blockers),
        safe_ids=safe_ids or {},
        safe_status_summary=summary or {},
    )
