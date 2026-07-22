from __future__ import annotations

from dataclasses import dataclass

from .bridge_planning import fingerprint


ORCHESTRATION_VERSION = "pi-6f.8-orchestration-v1"
MODEL_VERSION = "deterministic-self-study-tutor-v1"
PROMPT_POLICY_VERSION = "pi-6f.8-prompt-policy-v1"
SAFETY_POLICY_VERSION = "pi-6f.8-safety-policy-v1"
DISCLOSURE_POLICY_VERSION = "pi-6f.8-disclosure-policy-v1"
PRIVACY_POLICY_VERSION = "pi-6f.8-privacy-policy-v1"


VALID_SESSION_TRANSITIONS = {
    "PENDING": {"ACTIVE", "BLOCKED", "STALE", "INVALIDATED", "CANCELLED"},
    "ACTIVE": {"AWAITING_LEARNER", "PAUSED", "AWAITING_EVIDENCE", "NODE_COMPLETE", "BLOCKED", "STALE", "INVALIDATED", "COMPLETED", "CANCELLED"},
    "AWAITING_LEARNER": {"ACTIVE", "PAUSED", "BLOCKED", "STALE", "INVALIDATED", "CANCELLED"},
    "AWAITING_EVIDENCE": {"NODE_COMPLETE", "PAUSED", "BLOCKED", "STALE", "INVALIDATED", "CANCELLED"},
    "NODE_COMPLETE": {"ACTIVE", "COMPLETED", "STALE", "INVALIDATED", "CANCELLED"},
    "PAUSED": {"ACTIVE", "STALE", "INVALIDATED", "CANCELLED"},
    "BLOCKED": {"STALE", "INVALIDATED", "CANCELLED"},
    "STALE": {"INVALIDATED", "CANCELLED"},
    "INVALIDATED": set(),
    "COMPLETED": set(),
    "CANCELLED": set(),
}

VALID_NODE_TRANSITIONS = {
    "PENDING": {"ACTIVE", "SKIPPED_BY_POLICY", "BLOCKED", "STALE", "CANCELLED"},
    "ACTIVE": {"AWAITING_EVIDENCE", "NODE_COMPLETE", "PAUSED", "BLOCKED", "STALE", "CANCELLED"},
    "AWAITING_EVIDENCE": {"NODE_COMPLETE", "PAUSED", "BLOCKED", "STALE", "CANCELLED"},
    "PAUSED": {"ACTIVE", "STALE", "CANCELLED"},
    "NODE_COMPLETE": set(),
    "BLOCKED": {"STALE", "CANCELLED"},
    "STALE": {"CANCELLED"},
    "SKIPPED_BY_POLICY": set(),
    "CANCELLED": set(),
}

FINDING_DEFAULTS = {
    "TEACHING_SESSION_INTENT_NOT_ACTIVE": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_PLAN_NOT_ACTIVE": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_PLAN_STALE": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_PREPARATION_NOT_READY": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_PREPARATION_STALE": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_RETRIEVAL_NOT_VERIFIED": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_GRAPH_MISMATCH": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_COVERAGE_MISMATCH": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_TENANT_MISMATCH": ("BLOCKER", True, "SESSION"),
    "TEACHING_NODE_NOT_ELIGIBLE": ("BLOCKER", True, "NODE"),
    "TEACHING_NODE_BLOCKED": ("BLOCKER", True, "NODE"),
    "TEACHING_NODE_DEPENDENCY_UNSATISFIED": ("BLOCKER", True, "NODE"),
    "TEACHING_NODE_NOT_CURRENT": ("BLOCKER", True, "NODE"),
    "TEACHING_SKIP_NOT_PERMITTED": ("WARNING", False, "NODE"),
    "TEACHING_REVISIT_REQUESTED": ("INFO", False, "NODE"),
    "TEACHING_TRANSITION_NOT_PERMITTED": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_VERSION_CONFLICT": ("BLOCKER", True, "SESSION"),
    "TEACHING_NO_ELIGIBLE_EVIDENCE": ("BLOCKER", True, "NODE"),
    "TEACHING_CITATION_UNAVAILABLE": ("BLOCKER", True, "TURN"),
    "TEACHING_SOURCE_RETIRED": ("BLOCKER", True, "TURN"),
    "TEACHING_SOURCE_UNLICENSED": ("BLOCKER", True, "TURN"),
    "TEACHING_SOURCE_UNSAFE": ("BLOCKER", True, "TURN"),
    "TEACHING_SOURCE_CONFLICTING": ("BLOCKER", True, "TURN"),
    "TEACHING_RETRIEVAL_SCOPE_VIOLATION": ("BLOCKER", True, "TURN"),
    "TEACHING_RETRIEVAL_RESULT_STALE": ("BLOCKER", True, "TURN"),
    "TEACHING_RETRIEVAL_PROVENANCE_MISSING": ("BLOCKER", True, "TURN"),
    "TEACHING_MODEL_UNAVAILABLE": ("BLOCKER", True, "TURN"),
    "TEACHING_MODEL_OUTPUT_INVALID": ("BLOCKER", True, "TURN"),
    "TEACHING_UNSUPPORTED_CLAIM": ("BLOCKER", True, "TURN"),
    "TEACHING_CITATION_MISMATCH": ("BLOCKER", True, "TURN"),
    "TEACHING_PROMPT_INJECTION_DETECTED": ("BLOCKER", True, "TURN"),
    "TEACHING_SAFETY_BLOCKED": ("BLOCKER", True, "TURN"),
    "TEACHING_PRIVACY_BLOCKED": ("BLOCKER", True, "TURN"),
    "TEACHING_TOOL_USE_NOT_PERMITTED": ("BLOCKER", True, "TURN"),
    "TEACHING_EVIDENCE_EVALUATION_REQUIRED": ("INFO", False, "NODE"),
    "TEACHING_MASTERY_NOT_ESTABLISHED": ("INFO", False, "NODE"),
    "TEACHING_COMPLETION_NOT_MASTERY": ("INFO", False, "SESSION"),
    "TEACHING_EVALUATION_SERVICE_UNAVAILABLE": ("BLOCKER", True, "NODE"),
    "TEACHING_SESSION_BLOCKED": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_STALE": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_INVALIDATED": ("BLOCKER", True, "SESSION"),
    "TEACHING_SESSION_SUPERSEDED": ("BLOCKER", True, "SESSION"),
    "TEACHING_POLICY_CHANGED": ("BLOCKER", True, "SESSION"),
    "TEACHING_MODEL_POLICY_CHANGED": ("BLOCKER", True, "SESSION"),
}


@dataclass(frozen=True)
class AuthorityFinding:
    code: str
    severity: str
    blocking: bool
    scope: str
    affected: tuple[str, ...] = ()
    details: dict | None = None


def finding(code: str, affected=(), details=None) -> AuthorityFinding:
    severity, blocking, scope = FINDING_DEFAULTS.get(code, ("BLOCKER", True, "SESSION"))
    return AuthorityFinding(code, severity, blocking, scope, tuple(str(item) for item in affected), details or {})


def ensure_transition(current: str, target: str, transitions=VALID_SESSION_TRANSITIONS) -> None:
    if target not in transitions.get(current, set()):
        raise ValueError("TEACHING_TRANSITION_NOT_PERMITTED")


def select_action(*, has_learner_input: bool, turn_count: int, node_type: str, roles: set[str]) -> str:
    if has_learner_input:
        return "PROVIDE_FEEDBACK"
    if turn_count == 0:
        return "INTRODUCE"
    if node_type == "ASSESSMENT_OBJECTIVE" or "PRACTICE" in roles:
        return "CHECK_UNDERSTANDING"
    if "WORKED_EXAMPLE" in roles or "PROCEDURE" in roles:
        return "ILLUSTRATE"
    return "EXPLAIN"


def detect_prompt_injection(text: str) -> bool:
    lowered = (text or "").lower()
    suspicious = ("ignore previous", "system prompt", "developer message", "tool call", "reveal hidden", "bypass policy")
    return any(token in lowered for token in suspicious)


def build_context_payload(*, session, session_node, learner_input: str, prior_turns, assignments, retrieval_manifest) -> dict:
    return {
        "session_id": str(session.id),
        "intent_id": str(session.intent_id),
        "bridge_plan_id": str(session.bridge_plan_id),
        "bridge_plan_fingerprint": session.bridge_plan.plan_fingerprint,
        "preparation_manifest_id": str(session.preparation_manifest_id),
        "preparation_fingerprint": session.preparation_manifest.manifest_fingerprint,
        "retrieval_manifest_id": str(retrieval_manifest.id),
        "retrieval_fingerprint": retrieval_manifest.manifest_fingerprint,
        "graph_version_id": str(session_node.graph_version_id),
        "current_graph_node_id": str(session_node.graph_node_id),
        "current_bridge_node_id": str(session_node.bridge_node_id),
        "permitted_roles": list(session_node.permitted_roles),
        "prohibited_roles": ["CONFLICT_WARNING"],
        "required_citations": True,
        "output_schema": {"sections": "ordered cited text", "mastery_assertions": "forbidden"},
        "authority_boundaries": [
            "cannot modify graph or bridge plan",
            "cannot infer mastery",
            "cannot use unauthorized retrieval",
            "cannot expose diagnostic answers",
        ],
        "learner_input": learner_input,
        "prior_turns": prior_turns,
        "assignments": assignments,
        "retrieval_filters": retrieval_manifest.metadata_filters,
        "safety_policy_version": SAFETY_POLICY_VERSION,
        "disclosure_policy_version": DISCLOSURE_POLICY_VERSION,
        "model_version": MODEL_VERSION,
        "prompt_policy_version": PROMPT_POLICY_VERSION,
    }


def safe_teaching_text(*, action: str, node_title: str, assignments: list[dict], learner_input: str = "") -> str:
    if not assignments:
        return f"I cannot teach {node_title} from governed evidence yet. This node needs review before we continue."
    citation_labels = ", ".join(item.get("citation_label") or item["assignment_id"] for item in assignments[:3])
    if action == "PROVIDE_FEEDBACK":
        return f"Thanks for the response. Staying within the governed sources for {node_title}, I can give formative feedback but not award mastery. Citations: {citation_labels}."
    if action == "CHECK_UNDERSTANDING":
        return f"Let's check understanding of {node_title}. Use the cited material to explain the main idea in your own words. Citations: {citation_labels}."
    if action == "ILLUSTRATE":
        return f"Here is a governed illustration of {node_title} using only selected teaching-pack evidence. Citations: {citation_labels}."
    return f"Let's work on {node_title}. This explanation is limited to the current teaching pack and its citations. Citations: {citation_labels}."


def generation_fingerprint(payload: dict) -> str:
    return fingerprint(payload)
