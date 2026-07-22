from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass


ALGORITHM_VERSION = "pi-6f.6-bridge-planner-v1"
POLICY_VERSION = "pi-6f.6-bridge-policy-v1"
APPROVAL_POLICY_VERSION = "pi-6f.6-approval-policy-v1"
APPLICABILITY_VERSION = "pi-6f.6-applicability-v1"


def canonicalize(value):
    if isinstance(value, dict):
        return {str(key): canonicalize(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, set):
        return [canonicalize(item) for item in sorted(value, key=str)]
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    return str(value) if hasattr(value, "hex") and not isinstance(value, str) else value


def fingerprint(value) -> str:
    payload = json.dumps(canonicalize(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ClosureEdge:
    edge_id: str
    prerequisite_id: str
    dependent_id: str
    requirement: str
    ordinal: int


@dataclass(frozen=True)
class ClosureResult:
    node_ids: tuple[str, ...]
    edges: tuple[ClosureEdge, ...]
    layers: dict[str, int]


class GraphPlanningError(ValueError):
    pass


RUN_TRANSITIONS = {
    "PENDING": {"PLANNING", "INVALIDATED"}, "PLANNING": {"PLAN_READY", "FAILED", "STALE", "INVALIDATED"},
    "PLAN_READY": {"STALE", "INVALIDATED", "SUPERSEDED"}, "FAILED": {"INVALIDATED", "SUPERSEDED"},
    "STALE": {"INVALIDATED", "SUPERSEDED"}, "INVALIDATED": set(), "SUPERSEDED": set(),
}
PLAN_TRANSITIONS = {
    "PROPOSED": {"READY_FOR_REVIEW", "BLOCKED", "INVALIDATED"},
    "READY_FOR_REVIEW": {"APPROVED", "REJECTED", "STALE", "INVALIDATED"},
    "BLOCKED": {"REJECTED", "STALE", "INVALIDATED"}, "APPROVED": {"ACTIVE", "STALE", "INVALIDATED"},
    "ACTIVE": {"STALE", "INVALIDATED", "SUPERSEDED"}, "REJECTED": set(), "STALE": {"INVALIDATED", "SUPERSEDED"},
    "INVALIDATED": set(), "SUPERSEDED": set(),
}


def ensure_transition(current: str, target: str, transitions):
    if target not in transitions.get(current, set()):
        raise ValueError("BRIDGE_INVALID_LIFECYCLE_TRANSITION")


def calculate_prerequisite_closure(target_ids, edges, node_order) -> ClosureResult:
    """Traverse authoritative prerequisite edges where source requires target.

    PI-6F.3 represents REQUIRES as dependent -> prerequisite. The returned
    dependency reverses that direction for executable ordering.
    """
    targets = {str(item) for item in target_ids}
    known = {str(item) for item in node_order}
    if not targets or not targets.issubset(known):
        raise GraphPlanningError("BRIDGE_TARGET_UNAUTHORIZED")
    incoming = defaultdict(list)
    for edge in edges:
        dependent = str(edge["source_id"])
        prerequisite = str(edge["target_id"])
        if dependent not in known or prerequisite not in known:
            raise GraphPlanningError("BRIDGE_GRAPH_DANGLING_EDGE")
        incoming[dependent].append(edge)
    selected = set(targets)
    selected_edges = {}
    stack = sorted(targets, key=lambda item: (node_order[item], item), reverse=True)
    while stack:
        dependent = stack.pop()
        for edge in sorted(incoming.get(dependent, []), key=lambda item: (item["ordinal"], str(item["id"]))):
            prerequisite = str(edge["target_id"])
            selected_edges[str(edge["id"])] = ClosureEdge(
                str(edge["id"]), prerequisite, dependent, edge.get("requirement") or "REQUIRED", edge["ordinal"]
            )
            if prerequisite not in selected:
                selected.add(prerequisite)
                stack.append(prerequisite)

    successors = defaultdict(list)
    indegree = {node_id: 0 for node_id in selected}
    for edge in selected_edges.values():
        successors[edge.prerequisite_id].append(edge.dependent_id)
        indegree[edge.dependent_id] += 1
    ready = sorted((node for node, degree in indegree.items() if degree == 0), key=lambda item: (node_order[item], item))
    layers = {node: 0 for node in ready}
    ordered = []
    while ready:
        node = ready.pop(0)
        ordered.append(node)
        for successor in sorted(successors[node], key=lambda item: (node_order[item], item)):
            indegree[successor] -= 1
            layers[successor] = max(layers.get(successor, 0), layers[node] + 1)
            if indegree[successor] == 0:
                ready.append(successor)
                ready.sort(key=lambda item: (node_order[item], item))
    if len(ordered) != len(selected):
        raise GraphPlanningError("BRIDGE_GRAPH_CYCLE")
    return ClosureResult(tuple(ordered), tuple(sorted(selected_edges.values(), key=lambda item: (item.ordinal, item.edge_id))), layers)


def coverage_disposition(state: str, *, required: bool, graph_applicable: bool = True):
    if state == "NOT_APPLICABLE" and graph_applicable:
        return "POLICY_BLOCKED", required, "BRIDGE_COVERAGE_APPLICABILITY_MISMATCH"
    table = {
        "COVERED": ("FEASIBLE", False, None),
        "PARTIAL": ("PARTIALLY_FEASIBLE", required, "BRIDGE_MATERIAL_PARTIAL"),
        "MISSING": ("MATERIAL_MISSING", required, "BRIDGE_MATERIAL_MISSING"),
        "CONFLICTING": ("MATERIAL_CONFLICTING", required, "BRIDGE_MATERIAL_CONFLICTING"),
        "UNEVALUATED": ("EVIDENCE_STALE", required, "BRIDGE_COVERAGE_MISSING_OR_STALE"),
        "SUPPLEMENTARY": ("MATERIAL_MISSING", required, "BRIDGE_MATERIAL_SUPPLEMENTARY_ONLY"),
        "OUT_OF_SCOPE": ("POLICY_BLOCKED", required, "BRIDGE_REQUIRED_OUT_OF_SCOPE"),
        "NOT_APPLICABLE": ("NOT_APPLICABLE", False, None),
    }
    return table.get(state, ("EVIDENCE_STALE", required, "BRIDGE_COVERAGE_MISSING_OR_STALE"))


def placement_disposition(classification: str | None, *, target: bool, required: bool, non_waivable: bool = False):
    if target:
        return "TARGET_REQUIRED", ["AUTHORIZED_TARGET"]
    if non_waivable:
        return "PREREQUISITE_REQUIRED", ["NON_WAIVABLE_PREREQUISITE"]
    if classification == "FRONTIER":
        return "ENTRY", ["DIAGNOSTIC_ENTRY_BOUNDARY"]
    if classification == "DEMONSTRATED":
        return "REINFORCEMENT", ["BELOW_ENTRY_BOUNDARY_NO_MASTERY_ASSERTION"]
    if classification in {"UNCERTAIN", "NOT_DIAGNOSABLE"}:
        return "DIAGNOSTIC_REVIEW", ["DIAGNOSTIC_UNCERTAIN"]
    if classification == "GAP":
        return "PREREQUISITE_REQUIRED", ["DIAGNOSTIC_GAP"]
    return ("PREREQUISITE_REQUIRED" if required else "DEFERRED"), ["DIAGNOSTIC_UNASSESSED"]
