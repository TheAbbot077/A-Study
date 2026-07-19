from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError

from apps.content_processing.application.document_services import DocumentProcessingError
from apps.content_processing.application.proposal_services import ApproveProposalService, DeterministicAcademicProposalEngine, PopulateAcademicPlatformService, ValidateAcademicProposalService
from apps.content_processing.domain.proposal import AcademicImportProposal, PopulationState, ProposalDecisionType, ProposalReviewState
from apps.content_processing.domain.structure import HierarchyEvidenceStrength, SemanticSegmentType, StructuralRole


def segment(identifier="segment-1", text="Photosynthesis converts light energy into chemical energy for plants.", segment_type=SemanticSegmentType.EXPLANATION):
    return SimpleNamespace(id=identifier, hierarchy_node_id="node-1", normalized_text=text, segment_type=segment_type, confidence=.85, evidence_strength="structure_derived", title="Photosynthesis", source_page_start=1, source_page_end=1, metadata={"heading_only": False, "body_block_count": 1, "substantive_body_character_count": len(text), "supporting_body_block_ids": ["block-1"]})


def node(title="Photosynthesis"):
    return SimpleNamespace(id="node-1", title=title, parent_node_id=None, structural_role=StructuralRole.BODY, confidence=.9, evidence_strength=HierarchyEvidenceStrength.SOURCE_EXPLICIT, source_page_start=1, source_page_end=1)


def test_proposal_review_approval_is_independent_from_population():
    proposal = AcademicImportProposal(review_state=ProposalReviewState.READY_FOR_REVIEW)
    proposal.approve()
    assert proposal.review_state == ProposalReviewState.APPROVED
    assert proposal.decision == ProposalDecisionType.APPROVED
    assert proposal.population_state == PopulationState.READY_FOR_POPULATION


def test_rejected_proposal_cannot_be_approved():
    proposal = AcademicImportProposal(review_state=ProposalReviewState.READY_FOR_REVIEW)
    proposal.reject()
    with pytest.raises(ValidationError):
        proposal.approve()


def test_engine_builds_traceable_section_and_concept_from_semantic_evidence():
    hierarchy = SimpleNamespace(id="hierarchy")
    segmentation = SimpleNamespace(document_hierarchy_id="hierarchy")
    result = DeterministicAcademicProposalEngine().generate(hierarchy, [node()], [segment()])
    assert len(result.sections) == 1
    assert result.sections[0].node.id == "node-1"
    assert result.sections[0].concepts[0].segment.id == "segment-1"


def test_engine_rejects_reference_and_malformed_fallback_concepts():
    engine = DeterministicAcademicProposalEngine()
    reference = segment(segment_type=SemanticSegmentType.REFERENCE)
    weak = segment("segment-2", "Too short")
    result = engine.generate(SimpleNamespace(id="hierarchy"), [node("Source group 1")], [reference, weak])
    assert result.sections == ()


def test_engine_rejects_heading_only_semantic_evidence():
    candidate = segment()
    candidate.metadata = {"heading_only": True, "body_block_count": 0, "substantive_body_character_count": 0, "supporting_body_block_ids": []}
    result = DeterministicAcademicProposalEngine().generate(SimpleNamespace(id="hierarchy"), [node("Chapter Three")], [candidate])
    assert result.sections == ()


def test_engine_rejects_dates_roman_markers_and_toc_leaders_as_sections():
    engine = DeterministicAcademicProposalEngine()
    for title in ["September 2019", "ii", "Market Structure ........................ 74"]:
        assert engine.generate(SimpleNamespace(id="hierarchy"), [node(title)], [segment()]).sections == ()


def test_validation_detects_duplicate_concepts():
    engine = DeterministicAcademicProposalEngine()
    first = segment("segment-1")
    second = segment("segment-2")
    result = engine.generate(SimpleNamespace(id="hierarchy"), [node()], [first, second])
    assert ValidateAcademicProposalService().validate(result)[-1]["passed"] is True


def test_population_rejects_an_unapproved_proposal():
    proposal = SimpleNamespace(population_state=PopulationState.NOT_READY, review_state=ProposalReviewState.READY_FOR_REVIEW)
    with pytest.raises(DocumentProcessingError) as error:
        PopulateAcademicPlatformService().execute(SimpleNamespace(job_id="job", attempt_id="attempt"), proposal)
    assert error.value.code == "proposal_approval_failed"


def test_population_rejects_a_proposal_with_blocking_validation_findings():
    validations = Mock()
    validations.order_by.return_value.first.return_value = SimpleNamespace(created_at=2)
    validations.filter.return_value.exists.return_value = True
    proposal = SimpleNamespace(population_state=PopulationState.READY_FOR_POPULATION, review_state=ProposalReviewState.APPROVED, validations=validations, decisions=Mock())
    with pytest.raises(DocumentProcessingError) as error:
        PopulateAcademicPlatformService().execute(SimpleNamespace(job_id="job", attempt_id="attempt"), proposal)
    assert error.value.code == "proposal_validation_blocked"


def test_blocking_findings_prevent_approval():
    validations = Mock()
    validations.filter.return_value.exists.return_value = True
    proposal = SimpleNamespace(validations=validations)
    with pytest.raises(DocumentProcessingError) as error:
        ApproveProposalService().approve(proposal)
    assert error.value.code == "proposal_blocking_validation"


def test_population_rejects_approval_older_than_latest_validation():
    validations = Mock()
    validations.order_by.return_value.first.return_value = SimpleNamespace(created_at=2)
    validations.filter.return_value.exists.return_value = False
    decisions = Mock()
    decisions.filter.return_value.order_by.return_value.first.return_value = SimpleNamespace(created_at=1)
    proposal = SimpleNamespace(population_state=PopulationState.READY_FOR_POPULATION, review_state=ProposalReviewState.APPROVED, validations=validations, decisions=decisions)
    with pytest.raises(DocumentProcessingError) as error:
        PopulateAcademicPlatformService().execute(SimpleNamespace(job_id="job", attempt_id="attempt"), proposal)
    assert error.value.code == "proposal_approval_stale"
