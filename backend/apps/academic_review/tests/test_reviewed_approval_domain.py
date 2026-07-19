from types import SimpleNamespace

import pytest
from django.core.exceptions import ValidationError

from apps.academic_review.application.approval_services import (
    ApprovalReadinessPolicy, DeterministicApprovedProjectionBuilder,
    canonical_title, stable_checksum,
)
from apps.academic_review.domain.models import ApprovedProposalProjection, ReviewSessionStatus


def test_canonical_title_removes_numbering_dotted_leaders_and_page_artifacts():
    assert canonical_title("6.2.2. Other income accounts ........ 94") == "other income accounts"


def test_checksum_is_deterministic_across_dictionary_order():
    assert stable_checksum({"a": 1, "b": 2}) == stable_checksum({"b": 2, "a": 1})


def test_approved_projection_rejects_mutation(monkeypatch):
    projection = ApprovedProposalProjection(id="00000000-0000-0000-0000-000000000001")
    monkeypatch.setattr(ApprovedProposalProjection.objects, "filter", lambda **kwargs: SimpleNamespace(exists=lambda: True))
    with pytest.raises(ValidationError, match="immutable"):
        projection.save()


def test_readiness_requires_ready_for_approval_state():
    session = SimpleNamespace(status=ReviewSessionStatus.IN_PROGRESS, proposal=SimpleNamespace(result_checksum="sum", proposal_version="v1", review_state="under_review"), proposal_checksum="sum", proposal_version="v1")
    result = ApprovalReadinessPolicy().evaluate({"session": session, "decisions": [], "validations": [], "resolutions": [], "newer_exists": False})
    assert result.ready is False
    assert "review_not_ready_for_approval" in result.reasons


def test_readiness_blocks_pending_items_and_unresolved_findings():
    section = SimpleNamespace(item_type="section", decision="pending")
    finding = SimpleNamespace(id=1, passed=False, severity="blocking")
    session = SimpleNamespace(status=ReviewSessionStatus.READY_FOR_APPROVAL, proposal=SimpleNamespace(result_checksum="sum", proposal_version="v1", review_state="under_review"), proposal_checksum="sum", proposal_version="v1")
    result = ApprovalReadinessPolicy().evaluate({"session": session, "decisions": [section], "validations": [finding], "resolutions": [], "newer_exists": False})
    assert result.ready is False
    assert set(result.reasons) >= {"pending_sections", "unresolved_blocking_findings"}


def test_readiness_blocks_duplicate_canonical_section_titles():
    node = SimpleNamespace(structural_role="body")
    source_a = SimpleNamespace(id="a", title="1. Markets", ordering=1, hierarchy_node=node, hierarchy_node_id="n1", parent_reference="")
    source_b = SimpleNamespace(id="b", title="Markets", ordering=2, hierarchy_node=node, hierarchy_node_id="n2", parent_reference="")
    decisions = [SimpleNamespace(item_type="section", decision="accepted", proposed_section_id=item.id, proposed_section=item) for item in (source_a, source_b)]
    session = SimpleNamespace(status=ReviewSessionStatus.READY_FOR_APPROVAL, proposal=SimpleNamespace(result_checksum="sum", proposal_version="v1", review_state="under_review"), proposal_checksum="sum", proposal_version="v1")
    result = ApprovalReadinessPolicy().evaluate({"session": session, "decisions": decisions, "validations": [], "resolutions": [], "newer_exists": False})
    assert result.duplicate_titles == 1
    assert result.ready is False


def test_builder_omits_rejected_items_and_applies_edited_title():
    accepted_source = SimpleNamespace(id="s1", title="Old", ordering=1, source_page_start=1, source_page_end=2, hierarchy_node_id="n1", parent_reference="")
    rejected_source = SimpleNamespace(id="s2", title="Rejected", ordering=2, source_page_start=3, source_page_end=3, hierarchy_node_id="n2", parent_reference="")
    edit = SimpleNamespace(id=10, title="Final title", ordering=1, parent_section_id=None)
    decisions = [
        SimpleNamespace(id=1, item_type="section", decision="edited", proposed_section_id="s1", proposed_section=accepted_source, edit=edit),
        SimpleNamespace(id=2, item_type="section", decision="rejected", proposed_section_id="s2", proposed_section=rejected_source),
    ]
    plan = DeterministicApprovedProjectionBuilder().build({"decisions": decisions, "resolutions": [], "section_evidence": {"s1": [1]}, "concept_evidence": {}})
    assert len(plan.sections) == 1
    assert plan.sections[0]["title"] == "Final title"
