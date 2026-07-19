from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError

from apps.academic_review.application.approval_services import (
    APPROVAL_POLICY_VERSION, ApprovalReadinessResult, ApproveReviewedProposalService,
    EvaluateProposalApprovalReadinessService, RejectReviewedProposalService,
    ProjectionPlan,
)


@pytest.mark.django_db
def test_readiness_evaluation_persists_snapshot_and_audits():
    session = SimpleNamespace(id="session", version=3, proposal=SimpleNamespace(id="proposal", resource=SimpleNamespace(institution=None)), proposal_version="v1", proposal_checksum="sum")
    reviews = Mock(); reviews.approval_context.return_value = {"session": session}
    policy = Mock(version=APPROVAL_POLICY_VERSION); policy.evaluate.return_value = ApprovalReadinessResult(True, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, ())
    snapshots, events, audit = Mock(), Mock(), Mock()
    service = EvaluateProposalApprovalReadinessService(reviews=reviews, snapshots=snapshots, policy=policy, events=events, audit=audit)
    with patch("apps.academic_review.application.approval_services.ApprovalReadinessSnapshot", side_effect=lambda **values: SimpleNamespace(id="snapshot", **values)):
        service.execute("session", SimpleNamespace(is_superuser=True, is_staff=True), expected_session_version=3)
    snapshots.add.assert_called_once()
    audit.record_action.assert_called_once()


@pytest.mark.django_db
def test_approval_rejects_stale_expected_session_version():
    session = SimpleNamespace(id="session", version=4, proposal=SimpleNamespace(resource=SimpleNamespace()))
    reviews = Mock(); reviews.approval_context.return_value = {"session": session}
    decisions = Mock(); decisions.get_idempotent.return_value = None
    service = ApproveReviewedProposalService(reviews=reviews, decisions=decisions)
    with pytest.raises(ValidationError, match="version is stale"):
        service.execute("session", "snapshot", SimpleNamespace(is_superuser=True, is_staff=True), "key", expected_session_version=3)


def test_duplicate_approval_returns_idempotent_projection_before_version_check():
    projection = SimpleNamespace(id="projection")
    existing = SimpleNamespace(projection=projection)
    session = SimpleNamespace(id="session", version=9, proposal=SimpleNamespace(resource=SimpleNamespace()))
    reviews = Mock(); reviews.approval_context.return_value = {"session": session}
    decisions = Mock(); decisions.get_idempotent.return_value = existing
    projections = Mock()
    service = ApproveReviewedProposalService(reviews=reviews, decisions=decisions, projections=projections)
    assert service.execute("session", "old-snapshot", SimpleNamespace(is_superuser=True), "same-key", expected_session_version=3) is projection
    reviews.approval_context.assert_not_called()
    projections.add.assert_not_called()


def test_rejection_requires_reason():
    reviews, decisions = Mock(), Mock()
    with pytest.raises(ValidationError, match="reason"):
        RejectReviewedProposalService(reviews=reviews, decisions=decisions).execute("session", object(), "", "key")
    reviews.approval_context.assert_not_called()
    decisions.get_idempotent.assert_not_called()


def test_approval_requires_idempotency_key_before_repository_access():
    reviews, decisions = Mock(), Mock()
    with pytest.raises(ValidationError, match="idempotency key"):
        ApproveReviewedProposalService(reviews=reviews, decisions=decisions).execute("session", "snapshot", object(), "  ", 1)
    reviews.approval_context.assert_not_called()
    decisions.get_idempotent.assert_not_called()


@pytest.mark.django_db
def test_successful_approval_creates_projection_without_population_dispatch():
    resource = SimpleNamespace(subject=SimpleNamespace(institution="institution"), institution=None)
    proposal = SimpleNamespace(id="proposal", resource=resource)
    session = SimpleNamespace(id="session", proposal_id="proposal", proposal=proposal, proposal_version="v1", proposal_checksum="sum", version=3)
    context = {"session": session, "decisions": []}
    reviews = Mock(); reviews.approval_context.return_value = context
    snapshot = SimpleNamespace(id="snapshot", session_id="session", review_session_version=3, proposal_checksum="sum", policy_version=APPROVAL_POLICY_VERSION, ready=True, checksum="ready-sum", override_count=0, resolved_findings=0)
    readiness = Mock(); readiness.get.return_value = snapshot
    result = ApprovalReadinessResult(True, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ())
    evaluator = Mock(); evaluator.evaluate_context.return_value = (result, SimpleNamespace(checksum="ready-sum"))
    decisions = Mock(); decisions.get_idempotent.return_value = None; decisions.add.side_effect = lambda value: value
    projections = Mock(); projections.get_by_approval_version.return_value = None; projections.add.side_effect = lambda value: value
    sections, concepts, builder = Mock(), Mock(), Mock()
    sections.by_source.return_value = {}; builder.build.return_value = ProjectionPlan((), (), "projection-sum", "hierarchy-sum", "concepts-sum", "provenance-sum")
    with patch("apps.academic_review.application.approval_services.ApprovalDecision", side_effect=lambda **values: SimpleNamespace(id="decision", **values)), patch("apps.academic_review.application.approval_services.ApprovedProposalProjection", side_effect=lambda **values: SimpleNamespace(id="projection", **values)):
        projection = ApproveReviewedProposalService(reviews=reviews, readiness=readiness, decisions=decisions, projections=projections, sections=sections, concepts=concepts, builder=builder, readiness_evaluator=evaluator, events=Mock(), audit=Mock()).execute("session", "snapshot", SimpleNamespace(is_superuser=True, is_staff=True), "command-1", 3)
    assert projection.status == "ready_for_population"
    reviews.finalize_approval.assert_called_once_with(session, with_edits=False)
    assert decisions.get_idempotent.call_count == 2
    assert not hasattr(projection, "population_job")
