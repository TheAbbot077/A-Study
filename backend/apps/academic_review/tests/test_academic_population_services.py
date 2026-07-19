from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.exceptions import ValidationError

from apps.academic_review.application.population_services import BuildPopulationPlanService
from apps.academic_review.application.approval_services import stable_checksum


def test_plan_builder_preserves_deterministic_order_and_stable_keys():
    section = SimpleNamespace(id=9, source_id="source-9", title="Section", canonical_title="section", ordering=1, parent_source_id=None, depth=1, page_range={}, evidence_references=[], review_decision_id=1, edit_reference_id=None, override_references=[])
    section.projection_id = "projection"
    concept = SimpleNamespace(
        id=4, source_id="source-4", title="Concept", ordering=1, section=section,
        section_id=9, projection_id="projection", supporting_text="Evidence",
        explanation="Objective", canonical_title="concept", page_range={}, supporting_evidence=[],
        review_decision_id=2, edit_reference_id=None, override_references=[],
    )
    checksum = stable_checksum({
        "hierarchy": [{"source_id": "source-9", "title": "Section", "canonical_title": "section", "ordinal": 1, "parent_source_id": None, "depth": 1}],
        "concepts": [{"source_id": "source-4", "section_source_id": "source-9", "title": "Concept", "canonical_title": "concept", "ordinal": 1}],
        "provenance": [
            {"source_id": "source-9", "decision_id": 1, "edit_id": None, "override_references": [], "evidence": []},
            {"source_id": "source-4", "decision_id": 2, "edit_id": None, "override_references": [], "evidence": []},
        ],
    })
    projection = SimpleNamespace(
        id="projection", approval_decision_id="decision", checksum=checksum,
        resource_id="resource", subject_id="subject",
        sections=SimpleNamespace(all=Mock(return_value=[section])),
        concepts=SimpleNamespace(all=Mock(return_value=[concept])),
    )
    first = BuildPopulationPlanService().build(projection)
    second = BuildPopulationPlanService().build(projection)
    assert first == second
    assert first.sections[0]["stable_source_key"] == "approved-projection:projection:section:9"
    assert first.concepts[0]["parent_section_source_key"] == first.sections[0]["stable_source_key"]


def test_plan_builder_rejects_cross_projection_concept():
    section = SimpleNamespace(id=9, source_id="s", title="S", ordering=1, page_range={}, evidence_references=[], projection_id="projection")
    concept = SimpleNamespace(id=1, section_id=9, section=section, projection_id="other")
    projection = SimpleNamespace(
        id="projection", approval_decision_id="d", checksum="f", resource_id="r", subject_id="s",
        sections=SimpleNamespace(all=lambda: [section]), concepts=SimpleNamespace(all=lambda: [concept]),
    )
    with pytest.raises(ValidationError):
        BuildPopulationPlanService().build(projection)
