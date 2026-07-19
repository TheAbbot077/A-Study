from types import SimpleNamespace

from apps.content_processing.application.structure_services import DeterministicSemanticSegmenter
from apps.content_processing.domain.extraction import ExtractedBlockType
from apps.content_processing.domain.structure import NodeBlockRole, SemanticSegmentType, StructuralRole


def node(title="", role=StructuralRole.BODY):
    return SimpleNamespace(title=title, structural_role=role)


def block(text, block_type=ExtractedBlockType.PARAGRAPH):
    return SimpleNamespace(normalized_text=text, block_type=block_type)


def relationship(text, block_type=ExtractedBlockType.PARAGRAPH, role=NodeBlockRole.BODY):
    return SimpleNamespace(extracted_block=block(text, block_type), relationship_role=role)


def test_deterministic_semantic_types_cover_explicit_labels():
    segmenter = DeterministicSemanticSegmenter()
    cases = {"Definition: a cell is defined as a unit.": SemanticSegmentType.DEFINITION, "Example 1 demonstrates the rule.": SemanticSegmentType.EXAMPLE, "Procedure: follow these steps.": SemanticSegmentType.PROCEDURE, "Summary of the chapter.": SemanticSegmentType.SUMMARY, "Exercise 2": SemanticSegmentType.EXERCISE}
    for text, expected in cases.items():
        assert segmenter.classify([relationship(text)], node()) == expected


def test_tables_and_figures_remain_independent_types():
    segmenter = DeterministicSemanticSegmenter()
    assert segmenter.classify([relationship("A | B", ExtractedBlockType.TABLE)], node()) == SemanticSegmentType.TABLE
    assert segmenter.classify([relationship("", ExtractedBlockType.IMAGE)], node()) == SemanticSegmentType.FIGURE


def test_back_matter_produces_reference_segment():
    assert DeterministicSemanticSegmenter().classify([relationship("Smith, 2024")], node(role=StructuralRole.REFERENCES)) == SemanticSegmentType.REFERENCE


def test_heading_only_material_is_not_classified_as_explanation():
    result = DeterministicSemanticSegmenter().classify([relationship("Chapter Three Market Structure", role=NodeBlockRole.HEADING)], node())
    assert result == SemanticSegmentType.PARAGRAPH_GROUP
