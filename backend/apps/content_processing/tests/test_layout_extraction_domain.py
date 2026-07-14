import pytest
from django.core.exceptions import ValidationError

from apps.content_processing.domain.extraction import BoundingBox, ExtractedBlock, ExtractedBlockType, EvidenceOrigin, PageReference, sanitize_source_text


def test_bounding_box_rejects_inverted_geometry():
    with pytest.raises(ValueError):
        BoundingBox(10, 0, 5, 20)


def test_page_reference_uses_zero_based_index_and_one_based_number():
    assert PageReference(0, 1).to_dict()["page_number"] == 1
    with pytest.raises(ValueError):
        PageReference(-1, 0)


def test_source_text_sanitizer_removes_nul_and_unsafe_controls():
    assert sanitize_source_text("safe\x00 text\x07") == "safe text"


def test_text_block_requires_text():
    block = ExtractedBlock(block_type=ExtractedBlockType.PARAGRAPH, evidence_origin=EvidenceOrigin.PARSER_DEFAULT, normalized_text="", confidence=.5)
    with pytest.raises(ValidationError):
        block.clean()


def test_image_block_may_have_no_text():
    block = ExtractedBlock(block_type=ExtractedBlockType.IMAGE, evidence_origin=EvidenceOrigin.SOURCE_EXPLICIT, normalized_text="", confidence=.9)
    block.clean()
