import pytest
from django.core.exceptions import ValidationError

from apps.academic_review.domain.models import ProposalReviewSession, ReviewSessionStatus
from apps.users.domain.models import User


def session(status=ReviewSessionStatus.NOT_STARTED):
    return ProposalReviewSession(status=status)


def test_review_session_follows_governed_lifecycle():
    review = session()
    reviewer = User(email="reviewer@example.com")
    review.start(reviewer)
    assert review.status == ReviewSessionStatus.IN_PROGRESS
    review.submit()
    assert review.status == ReviewSessionStatus.READY_FOR_APPROVAL
    review.approve(with_edits=True)
    assert review.status == ReviewSessionStatus.APPROVED_WITH_EDITS


def test_invalid_review_transition_is_rejected():
    review = session()
    with pytest.raises(ValidationError):
        review.submit()


def test_reprocessing_closes_an_active_review_without_approval():
    review = session(ReviewSessionStatus.IN_PROGRESS)
    review.request_reprocessing()
    assert review.status == ReviewSessionStatus.REPROCESS_REQUESTED
    assert review.closed_at is not None


def test_terminal_review_cannot_be_rejected_again():
    review = session(ReviewSessionStatus.APPROVED)
    with pytest.raises(ValidationError):
        review.reject()
