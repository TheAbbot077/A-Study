import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_anonymous_cannot_retrieve_projection():
    response = APIClient().get("/api/academic-review/projections/00000000-0000-0000-0000-000000000001/")
    assert response.status_code in {401, 403}


def test_approval_request_requires_snapshot_version_and_idempotency_key():
    from apps.academic_review.api.serializers import ApproveReviewedProposalSerializer
    serializer = ApproveReviewedProposalSerializer(data={})
    assert serializer.is_valid() is False
    assert set(serializer.errors) == {"readiness_snapshot_id", "expected_session_version", "idempotency_key"}


def test_rejection_request_requires_reason_and_idempotency_contract():
    from apps.academic_review.api.serializers import RejectReviewedProposalSerializer
    serializer = RejectReviewedProposalSerializer(data={})
    assert serializer.is_valid() is False
    assert set(serializer.errors) == {"reason", "expected_session_version", "idempotency_key"}
