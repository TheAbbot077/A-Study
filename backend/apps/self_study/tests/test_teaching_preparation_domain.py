from apps.self_study.domain.teaching_preparation import classify_role, evaluate_pack_state, fingerprint, role_policy_for


def test_teaching_roles_preserve_mapping_and_node_semantics():
    assert classify_role("DIRECT", "PROSE") == "PRIMARY_EXPLANATION"
    assert classify_role("SUPPORTING", "DEFINITION") == "DEFINITION"
    assert classify_role("DIRECT", "PROSE", prerequisite=True) == "PREREQUISITE_SUPPORT"
    assert classify_role("CONFLICTING", "PROSE") == "CONFLICT_WARNING"


def test_node_type_role_policies_keep_mandatory_roles_distinct():
    assert role_policy_for("CONCEPT")["mandatory"] == ["PRIMARY_EXPLANATION"]
    assert role_policy_for("COMPETENCY")["mandatory"] == ["PROCEDURE"]
    assert role_policy_for("ASSESSMENT_OBJECTIVE")["mandatory"] == ["ASSESSMENT_SUPPORT"]
    assert role_policy_for("CONCEPT", prerequisite=True)["mandatory"][0] == "PREREQUISITE_SUPPORT"


def test_readiness_fails_closed_for_missing_roles_and_unverified_retrieval():
    state, findings = evaluate_pack_state(
        coverage_state="COVERED",
        required=True,
        assigned_roles=set(),
        required_roles=["PRIMARY_EXPLANATION"],
        alternatives={},
        source_count=0,
        minimum_sources=1,
        conflict_count=0,
        retrieval_verified=False,
    )

    assert state == "BLOCKED"
    assert {finding.code for finding in findings} >= {"TEACHING_REQUIRED_ROLE_MISSING", "TEACHING_RETRIEVAL_NOT_VERIFIED"}


def test_fingerprints_are_deterministic_for_equivalent_manifests():
    assert fingerprint({"b": [2, 1], "a": "x"}) == fingerprint({"a": "x", "b": [2, 1]})
