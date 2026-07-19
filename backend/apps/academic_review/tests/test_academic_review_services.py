from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError

from apps.academic_review.application.services import AcademicReviewService, ProposalReviewQueryService
from apps.academic_review.domain.models import ReviewSessionStatus


@pytest.mark.django_db
def test_summary_blocks_readiness_for_pending_items_and_findings():
    decisions = Mock()
    decisions.values_list.return_value = [("section", "pending"), ("concept", "accepted")]
    validations = Mock(); validations.filter.return_value.count.return_value = 1
    resolutions = Mock(); resolutions.filter.return_value.count.return_value = 0
    overrides = Mock(); overrides.count.return_value = 0
    session = SimpleNamespace(item_decisions=decisions, proposal=SimpleNamespace(validations=validations), finding_resolutions=resolutions, overrides=overrides)
    query = ProposalReviewQueryService(); query.relationships_valid = Mock(return_value=True)
    summary = query.summary(session)
    assert summary.ready is False
    assert summary.outstanding_findings == 1


def test_stale_proposal_checksum_prevents_submission():
    review = SimpleNamespace(proposal=SimpleNamespace(result_checksum="new", proposal_version="v1"), proposal_checksum="old", proposal_version="v1")
    with pytest.raises(ValidationError, match="changed"):
        AcademicReviewService()._ensure_current(review)


def test_review_ready_for_approval_requires_relationship_consistency():
    decisions = Mock(); decisions.values_list.return_value = []
    validations = Mock(); validations.filter.return_value.count.return_value = 0
    resolutions = Mock(); resolutions.filter.return_value.count.return_value = 0
    overrides = Mock(); overrides.count.return_value = 0
    session = SimpleNamespace(item_decisions=decisions, proposal=SimpleNamespace(validations=validations), finding_resolutions=resolutions, overrides=overrides)
    query = ProposalReviewQueryService(); query.relationships_valid = Mock(return_value=False)
    assert query.summary(session).ready is False
