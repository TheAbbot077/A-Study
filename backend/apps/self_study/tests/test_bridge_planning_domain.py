import pytest

from apps.self_study.domain.bridge_planning import (
    GraphPlanningError, PLAN_TRANSITIONS, calculate_prerequisite_closure,
    coverage_disposition, ensure_transition, fingerprint, placement_disposition,
)


def test_fingerprints_ignore_mapping_and_set_insertion_order():
    assert fingerprint({"targets": {"b", "a"}, "graph": "g"}) == fingerprint({"graph": "g", "targets": {"a", "b"}})


def test_shared_prerequisites_are_deduplicated_and_topologically_ordered():
    order = {"p": 1, "a": 2, "b": 3}
    edges = [
        {"id": "a-p", "source_id": "a", "target_id": "p", "requirement": "REQUIRED", "ordinal": 1},
        {"id": "b-p", "source_id": "b", "target_id": "p", "requirement": "RECOMMENDED", "ordinal": 2},
    ]
    result = calculate_prerequisite_closure(["a", "b"], edges, order)
    assert result.node_ids == ("p", "a", "b")
    assert result.layers == {"p": 0, "a": 1, "b": 1}
    assert {edge.edge_id for edge in result.edges} == {"a-p", "b-p"}


def test_cycle_and_dangling_edge_are_stable_failures():
    with pytest.raises(GraphPlanningError, match="BRIDGE_GRAPH_CYCLE"):
        calculate_prerequisite_closure(["a"], [{"id":"1","source_id":"a","target_id":"b","requirement":"REQUIRED","ordinal":1},{"id":"2","source_id":"b","target_id":"a","requirement":"REQUIRED","ordinal":2}], {"a":1,"b":2})
    with pytest.raises(GraphPlanningError, match="BRIDGE_GRAPH_DANGLING_EDGE"):
        calculate_prerequisite_closure(["a"], [{"id":"1","source_id":"a","target_id":"missing","requirement":"REQUIRED","ordinal":1}], {"a":1})


@pytest.mark.parametrize(("state","expected","blocked"), [
    ("COVERED","FEASIBLE",False), ("PARTIAL","PARTIALLY_FEASIBLE",True),
    ("MISSING","MATERIAL_MISSING",True), ("CONFLICTING","MATERIAL_CONFLICTING",True),
    ("UNEVALUATED","EVIDENCE_STALE",True), ("SUPPLEMENTARY","MATERIAL_MISSING",True),
    ("OUT_OF_SCOPE","POLICY_BLOCKED",True),
])
def test_coverage_overlay_preserves_material_axis(state, expected, blocked):
    assert coverage_disposition(state, required=True)[:2] == (expected, blocked)


def test_placement_is_not_a_mastery_assertion_and_non_waivable_wins():
    disposition, rationale = placement_disposition("DEMONSTRATED", target=False, required=True)
    assert disposition == "REINFORCEMENT"
    assert "NO_MASTERY_ASSERTION" in rationale[0]
    assert placement_disposition("DEMONSTRATED", target=False, required=True, non_waivable=True)[0] == "PREREQUISITE_REQUIRED"


def test_invalid_plan_transition_is_rejected():
    with pytest.raises(ValueError, match="BRIDGE_INVALID_LIFECYCLE_TRANSITION"):
        ensure_transition("BLOCKED", "ACTIVE", PLAN_TRANSITIONS)
