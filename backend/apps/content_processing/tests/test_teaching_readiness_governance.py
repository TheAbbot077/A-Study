from dataclasses import replace

from apps.content_processing.domain.teaching_readiness import (
    CheckSeverity, TeachingReadinessDecision, TeachingReadinessPolicy, TeachingReadinessSnapshot,
)


def passing_snapshot(**changes):
    values = {
        "resource_id": "resource", "subject_id": "subject", "processing_job_id": "job",
        "processing_attempt_id": "attempt", "stored_file_id": "file", "source_fingerprint": "source",
        "processing_source_fingerprint": "source",
        "source_exists": True, "source_available": True, "processing_status": "ready_for_review",
        "processing_attempt_status": "succeeded", "processing_outputs_complete": True,
        "blocking_diagnostic_count": 0, "review_session_id": "review", "review_status": "approved",
        "unresolved_review_findings": 0, "approval_decision_id": "approval",
        "approval_decision": "approved", "approval_actor_authorized": True,
        "approved_projection_id": "projection", "projection_fingerprint": "academic-v1",
        "projection_status": "populated", "academic_population_run_id": "population",
        "population_status": "populated", "population_fingerprint": "academic-v1",
        "expected_section_count": 2, "actual_section_count": 2,
        "expected_concept_count": 3, "actual_concept_count": 3,
        "official_academic_fingerprint": "academic-v1", "academic_content_valid": True,
        "retrieval_synchronization_run_id": "synchronization",
        "synchronization_status": "synchronized", "synchronization_source_fingerprint": "academic-v1",
        "manifest_fingerprint": "manifest", "retrieval_generation_id": "generation",
        "generation_status": "active", "planned_chunk_count": 3, "stored_chunk_count": 3,
        "keyword_indexed_count": 3, "vector_indexed_count": 3, "failed_chunk_count": 0,
        "duplicate_chunk_count": 0, "orphaned_chunk_count": 0, "citation_coverage": 1,
        "provenance_valid": True, "policy_version": "teaching-readiness-v1",
    }
    values.update(changes)
    return TeachingReadinessSnapshot(**values)


def policy_decision(checks):
    return TeachingReadinessDecision.BLOCKED if any(
        not item.passed and item.severity == CheckSeverity.BLOCKER for item in checks
    ) else TeachingReadinessDecision.READY


def test_policy_grants_only_fully_governed_snapshot():
    checks = TeachingReadinessPolicy().evaluate(passing_snapshot())
    assert policy_decision(checks) == TeachingReadinessDecision.READY
    assert all(item.passed for item in checks)


def test_synchronized_alone_does_not_grant_readiness():
    checks = TeachingReadinessPolicy().evaluate(passing_snapshot(review_status="in_progress"))
    assert policy_decision(checks) == TeachingReadinessDecision.BLOCKED
    assert any(item.code == "READINESS_REVIEW_INCOMPLETE" and not item.passed for item in checks)


def test_citation_coverage_is_a_blocker():
    checks = TeachingReadinessPolicy().evaluate(passing_snapshot(citation_coverage=.99))
    assert policy_decision(checks) == TeachingReadinessDecision.BLOCKED


def test_lineage_fingerprint_is_deterministic_and_versioned():
    snapshot = passing_snapshot()
    assert snapshot.lineage_fingerprint() == snapshot.lineage_fingerprint()
    assert snapshot.lineage_fingerprint() != replace(snapshot, retrieval_generation_id="generation-2").lineage_fingerprint()
    assert snapshot.lineage_fingerprint() != replace(snapshot, policy_version="teaching-readiness-v2").lineage_fingerprint()


def test_checks_have_deterministic_order():
    first = TeachingReadinessPolicy().evaluate(passing_snapshot())
    second = TeachingReadinessPolicy().evaluate(passing_snapshot())
    assert [item.code for item in first] == [item.code for item in second]
