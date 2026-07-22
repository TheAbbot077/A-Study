from __future__ import annotations

from dataclasses import dataclass

from .bridge_planning import fingerprint


ALGORITHM_VERSION = "pi-6f.7-teaching-preparation-v1"
POLICY_VERSION = "pi-6f.7-teaching-preparation-policy-v1"
ROLE_POLICY_VERSION = "pi-6f.7-role-policy-v1"
RETRIEVAL_SCHEMA_VERSION = "pi-6f.7-self-study-retrieval-schema-v1"
READINESS_POLICY_VERSION = "pi-6f.7-readiness-policy-v1"


ROLE_POLICY = {
    "CONCEPT": {"mandatory": ["PRIMARY_EXPLANATION"], "alternatives": {"PRIMARY_EXPLANATION": ["DEFINITION"]}, "minimum_sources": 1},
    "COMPETENCY": {"mandatory": ["PROCEDURE"], "alternatives": {"PROCEDURE": ["WORKED_EXAMPLE", "PRACTICE"]}, "minimum_sources": 1},
    "OUTCOME": {"mandatory": ["SUPPORTING_EXPLANATION"], "alternatives": {}, "minimum_sources": 1},
    "ASSESSMENT_OBJECTIVE": {"mandatory": ["ASSESSMENT_SUPPORT"], "alternatives": {}, "minimum_sources": 1},
    "DEFAULT": {"mandatory": ["SUPPORTING_EXPLANATION"], "alternatives": {}, "minimum_sources": 1},
}


MAPPING_ROLE = {
    "DIRECT": "PRIMARY_EXPLANATION",
    "SUPPORTING": "SUPPORTING_EXPLANATION",
    "PREREQUISITE_SUPPORT": "PREREQUISITE_SUPPORT",
    "ASSESSMENT_SUPPORT": "ASSESSMENT_SUPPORT",
    "SUPPLEMENTARY": "ENRICHMENT",
    "CONFLICTING": "CONFLICT_WARNING",
}


EVIDENCE_ROLE = {
    "DEFINITION": "DEFINITION",
    "EXAMPLE": "WORKED_EXAMPLE",
    "PROCEDURE": "PROCEDURE",
    "QUESTION": "PRACTICE",
    "ANSWER_EXPLANATION": "ASSESSMENT_SUPPORT",
    "REFERENCE": "REFERENCE",
}


BLOCKING_COVERAGE_STATES = {"MISSING", "CONFLICTING", "OUT_OF_SCOPE", "UNEVALUATED"}
PARTIAL_COVERAGE_STATES = {"PARTIAL", "SUPPLEMENTARY"}
ELIGIBLE_MAPPING_STATUSES = {"ACCEPTED"}
CURRENT_RESOURCE_STATUSES = {"active", "ready", "published", "completed"}
SAFE_DISPOSITIONS = {"allowed", "approved", "safe", "clear", "permitted", "unknown"}


@dataclass(frozen=True)
class AssignmentSpec:
    mapping_id: str
    evidence_unit_id: str
    resource_id: str
    source_input_id: str
    source_block_id: str
    classification: str
    role: str
    rank: int
    diversity_key: str
    duplicate_cluster: str
    licence_disposition: str
    safety_disposition: str
    citation_snapshot: dict
    rationale_codes: tuple[str, ...]
    fingerprint: str


@dataclass(frozen=True)
class FindingSpec:
    code: str
    blocking: bool
    scope: str
    affected: tuple[str, ...]
    details: dict
    severity: str = "BLOCKER"


def role_policy_for(node_type: str, prerequisite: bool = False) -> dict:
    policy = dict(ROLE_POLICY.get(node_type, ROLE_POLICY["DEFAULT"]))
    if prerequisite and "PREREQUISITE_SUPPORT" not in policy["mandatory"]:
        policy["mandatory"] = ["PREREQUISITE_SUPPORT", *policy["mandatory"]]
    return policy


def classify_role(mapping_class: str, evidence_type: str, prerequisite: bool = False) -> str:
    if mapping_class == "CONFLICTING":
        return "CONFLICT_WARNING"
    if prerequisite and mapping_class in {"DIRECT", "SUPPORTING", "PREREQUISITE_SUPPORT"}:
        return "PREREQUISITE_SUPPORT"
    return EVIDENCE_ROLE.get(evidence_type) or MAPPING_ROLE.get(mapping_class, "REFERENCE")


def role_satisfies(required_role: str, roles: set[str], alternatives: dict[str, list[str]]) -> bool:
    return required_role in roles or bool(set(alternatives.get(required_role, [])) & roles)


def evaluate_pack_state(*, coverage_state: str, required: bool, assigned_roles: set[str], required_roles: list[str], alternatives: dict[str, list[str]], source_count: int, minimum_sources: int, conflict_count: int, retrieval_verified: bool):
    findings: list[FindingSpec] = []
    if coverage_state in BLOCKING_COVERAGE_STATES and required:
        findings.append(FindingSpec(f"TEACHING_COVERAGE_{coverage_state}", True, "PACK", (), {"coverage_state": coverage_state}))
    if coverage_state in PARTIAL_COVERAGE_STATES and required:
        findings.append(FindingSpec(f"TEACHING_COVERAGE_{coverage_state}", True, "PACK", (), {"coverage_state": coverage_state}))
    for role in required_roles:
        if not role_satisfies(role, assigned_roles, alternatives):
            findings.append(FindingSpec("TEACHING_REQUIRED_ROLE_MISSING", True, "PACK", (), {"role": role}))
    if source_count < minimum_sources and required:
        findings.append(FindingSpec("TEACHING_SOURCE_DIVERSITY_INSUFFICIENT", True, "PACK", (), {"source_count": source_count, "minimum_sources": minimum_sources}))
    if conflict_count:
        findings.append(FindingSpec("TEACHING_CONFLICTING_MATERIAL", required, "PACK", (), {"conflicting_assignment_count": conflict_count}))
    if not retrieval_verified:
        findings.append(FindingSpec("TEACHING_RETRIEVAL_NOT_VERIFIED", True, "PACK", (), {}, "BLOCKER"))
    if any(item.code == "TEACHING_CONFLICTING_MATERIAL" and item.blocking for item in findings):
        return "CONFLICTING", findings
    if any(item.blocking for item in findings):
        return ("PARTIAL" if assigned_roles else "BLOCKED"), findings
    return "READY" if retrieval_verified else "ASSEMBLED", findings


def run_manifest_for_plan(plan) -> dict:
    run = plan.run
    coverage = run.coverage_evaluation
    return {
        "tenant_id": str(plan.tenant_id),
        "intent_id": str(plan.intent_id),
        "bridge_plan_id": str(plan.id),
        "bridge_plan_fingerprint": plan.plan_fingerprint,
        "graph_version_id": str(plan.graph_version_id),
        "graph_fingerprint": plan.graph_version.graph_fingerprint,
        "coverage_evaluation_id": str(coverage.id),
        "coverage_fingerprint": coverage.evaluation_fingerprint,
        "mapping_set_fingerprint": coverage.mapping_set_fingerprint,
        "gap_set_fingerprint": coverage.gap_set_fingerprint,
        "target_set_fingerprint": plan.target_set_fingerprint,
        "algorithm_version": ALGORITHM_VERSION,
        "policy_version": POLICY_VERSION,
        "role_policy_version": ROLE_POLICY_VERSION,
        "retrieval_schema_version": RETRIEVAL_SCHEMA_VERSION,
        "readiness_policy_version": READINESS_POLICY_VERSION,
    }


def assignment_fingerprint(payload: dict) -> str:
    return fingerprint(payload)
