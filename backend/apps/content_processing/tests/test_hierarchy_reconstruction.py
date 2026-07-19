from types import SimpleNamespace

from apps.content_processing.application.structure_services import DeterministicHierarchyReconstructor, DocumentStyleAnalyzer, HeadingPolicy
from apps.content_processing.domain.extraction import EvidenceOrigin, ExtractedBlockType
from apps.content_processing.domain.structure import BlockDisposition, HierarchyEvidenceStrength, HierarchyNodeType, StructuralRole


def block(sequence, text, block_type=ExtractedBlockType.PARAGRAPH, size=11, bold=False, page=1, style=""):
    return SimpleNamespace(id=f"block-{sequence}", sequence_number=sequence, normalized_text=text, block_type=block_type, typography={"font_size": size, "bold": bold}, structural_hints={"style_name": style}, page_reference={"page_number": page}, evidence_origin=EvidenceOrigin.SOURCE_EXPLICIT, confidence=.95)


def included(*blocks):
    return {str(item.id): {"disposition": BlockDisposition.INCLUDED} for item in blocks}


def test_document_wide_style_analysis_finds_dominant_body_font():
    profile = DocumentStyleAnalyzer().analyze([block(0, "One", size=11), block(1, "Two", size=11), block(2, "Heading", size=18)])
    assert profile["dominant_body_font_size"] == 11
    assert profile["heading_font_sizes"] == [18]


def test_explicit_docx_heading_is_source_grounded():
    heading, body = block(0, "Cell Biology", style="Heading 1"), block(1, "Cells are the basic unit of life.")
    candidate = HeadingPolicy().candidates([heading, body], DocumentStyleAnalyzer().analyze([heading, body]), included(heading, body))[0]
    assert candidate.candidate_level == 1
    assert candidate.evidence_strength == HierarchyEvidenceStrength.SOURCE_EXPLICIT


def test_heading_policy_rejects_dates_urls_page_numbers_and_synthetic_titles():
    policy = HeadingPolicy()
    for text in ["2026", "September 2019", "https://example.com", "notes.pdf", "Imported Content", "Concept 2Available"]:
        candidate, body = block(0, text, ExtractedBlockType.HEADING_1), block(1, "Supporting body text")
        assert policy.candidates([candidate, body], DocumentStyleAnalyzer().analyze([candidate, body]), included(candidate, body)) == []


def test_numbered_headings_create_nested_ranges():
    blocks = [block(0, "1 Foundations", ExtractedBlockType.HEADING_1), block(1, "Body"), block(2, "1.1 Cells", ExtractedBlockType.HEADING_2), block(3, "Cell body")]
    nodes, _, _, _ = DeterministicHierarchyReconstructor().reconstruct(blocks)
    assert nodes[0].node_type == HierarchyNodeType.DOCUMENT
    assert nodes[2].parent_key == nodes[1].key


def test_unstructured_prose_generates_multiple_explicit_fallback_groups():
    blocks = [block(index, f"Paragraph {index}") for index in range(25)]
    nodes, _, _, warnings = DeterministicHierarchyReconstructor().reconstruct(blocks)
    assert len(nodes) == 3
    assert all(node.strength == HierarchyEvidenceStrength.FALLBACK_GENERATED for node in nodes[1:])
    assert warnings[0]["code"] == "fallback_hierarchy_generated"


def test_page_numbers_and_repeated_headers_are_preserved_but_excluded():
    blocks = [block(0, "Study Guide", page=1), block(1, "1", ExtractedBlockType.PAGE_NUMBER, page=1), block(2, "Study Guide", page=2), block(3, "2", ExtractedBlockType.PAGE_NUMBER, page=2)]
    _, classifications, _, _ = DeterministicHierarchyReconstructor().reconstruct(blocks)
    assert classifications["block-0"]["role"] == StructuralRole.PROBABLE_NOISE
    assert classifications["block-1"]["disposition"] == BlockDisposition.EXCLUDED


def test_split_dotted_toc_region_owns_navigation_blocks_and_roman_markers():
    blocks = [block(0, "Contents", page=2), block(1, "Chapter Three . . . . . 4 0", page=2), block(2, "ii", page=2), block(3, "Market Structure ................ 74", page=3), block(4, "1 Introduction", ExtractedBlockType.HEADING_1, page=8), block(5, "Substantive body content starts here.", page=8)]
    _, classifications, _, _ = DeterministicHierarchyReconstructor().reconstruct(blocks)
    for index in range(4):
        assert classifications[f"block-{index}"]["disposition"] == BlockDisposition.EXCLUDED
        assert classifications[f"block-{index}"]["role"] == StructuralRole.TABLE_OF_CONTENTS
