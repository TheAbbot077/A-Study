from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class SourceFormat(models.TextChoices):
    PDF = "pdf", "PDF"
    DOCX = "docx", "DOCX"
    UNKNOWN = "unknown", "Unknown"


class DocumentTextClassification(models.TextChoices):
    NATIVE_TEXT = "native_text", "Native Text"
    SCANNED = "scanned", "Scanned"
    MIXED = "mixed", "Mixed"
    EMPTY_OR_UNRESOLVED = "empty_or_unresolved", "Empty Or Unresolved"


class NativeTextQuality(models.TextChoices):
    HIGH = "high", "High"
    MODERATE = "moderate", "Moderate"
    LOW = "low", "Low"
    NONE = "none", "None"
    UNRESOLVED = "unresolved", "Unresolved"


class OcrRequirement(models.TextChoices):
    NOT_REQUIRED = "not_required", "Not Required"
    RECOMMENDED = "recommended", "Recommended"
    REQUIRED = "required", "Required"
    UNAVAILABLE = "unavailable", "Unavailable"
    FAILED = "failed", "Failed"


class ExtractedBlockType(models.TextChoices):
    TITLE = "title", "Title"
    HEADING_1 = "heading_1", "Heading 1"
    HEADING_2 = "heading_2", "Heading 2"
    HEADING_3 = "heading_3", "Heading 3"
    PARAGRAPH = "paragraph", "Paragraph"
    LIST_ITEM = "list_item", "List Item"
    TABLE = "table", "Table"
    TABLE_ROW = "table_row", "Table Row"
    TABLE_CELL = "table_cell", "Table Cell"
    CAPTION = "caption", "Caption"
    HEADER = "header", "Header"
    FOOTER = "footer", "Footer"
    PAGE_NUMBER = "page_number", "Page Number"
    TOC_ENTRY = "toc_entry", "TOC Entry"
    IMAGE = "image", "Image"
    FOOTNOTE = "footnote", "Footnote"
    ENDNOTE = "endnote", "Endnote"
    EQUATION = "equation", "Equation"
    UNKNOWN = "unknown", "Unknown"


class EvidenceOrigin(models.TextChoices):
    SOURCE_EXPLICIT = "source_explicit", "Source Explicit"
    LAYOUT_INFERRED = "layout_inferred", "Layout Inferred"
    STYLE_INFERRED = "style_inferred", "Style Inferred"
    OCR_INFERRED = "ocr_inferred", "OCR Inferred"
    PARSER_DEFAULT = "parser_default", "Parser Default"
    UNKNOWN = "unknown", "Unknown"


class ExtractionMethod(models.TextChoices):
    PDF_NATIVE = "pdf_native", "PDF Native"
    PDF_OCR = "pdf_ocr", "PDF OCR"
    PDF_MIXED = "pdf_mixed", "PDF Mixed"
    DOCX_NATIVE = "docx_native", "DOCX Native"
    UNKNOWN = "unknown", "Unknown"


class ExtractionStatus(models.TextChoices):
    COMPLETED = "completed", "Completed"
    COMPLETED_WITH_WARNINGS = "completed_with_warnings", "Completed With Warnings"
    FAILED = "failed", "Failed"


@dataclass(frozen=True)
class BoundingBox:
    x0: float
    y0: float
    x1: float
    y1: float
    coordinate_space: str = "page_points"

    def __post_init__(self) -> None:
        if self.x1 < self.x0 or self.y1 < self.y0:
            raise ValueError("Bounding-box maximums must not precede minimums.")

    def to_dict(self) -> dict[str, float | str]:
        return {"x0": self.x0, "y0": self.y0, "x1": self.x1, "y1": self.y1, "coordinate_space": self.coordinate_space}


@dataclass(frozen=True)
class PageReference:
    page_index: int
    page_number: int
    page_width: float | None = None
    page_height: float | None = None
    rotation: int = 0

    def __post_init__(self) -> None:
        if self.page_index < 0 or self.page_number < 1:
            raise ValueError("Pages use zero-based indexes and one-based display numbers.")

    def to_dict(self) -> dict[str, int | float | None]:
        return self.__dict__.copy()


_UNSAFE_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_source_text(value: str) -> str:
    return _UNSAFE_CONTROLS.sub("", (value or "").replace("\r\n", "\n").replace("\r", "\n"))


class SourceDocumentProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.CASCADE, related_name="source_profiles")
    attempt = models.ForeignKey("content_processing.ProcessingAttempt", on_delete=models.CASCADE, related_name="source_profiles")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.SET_NULL, null=True, blank=True, related_name="source_document_profiles")
    stored_file = models.ForeignKey("storage.StoredFile", on_delete=models.PROTECT, related_name="source_document_profiles")
    pipeline_version = models.CharField(max_length=100)
    source_filename = models.CharField(max_length=512)
    file_extension = models.CharField(max_length=32, blank=True)
    declared_content_type = models.CharField(max_length=128, blank=True)
    detected_format = models.CharField(max_length=32, choices=SourceFormat.choices)
    detected_mime_type = models.CharField(max_length=128, blank=True)
    file_size_bytes = models.BigIntegerField()
    source_checksum = models.CharField(max_length=128)
    signature_summary = models.JSONField(default=dict)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    encrypted = models.BooleanField(default=False)
    password_required = models.BooleanField(default=False)
    corrupt = models.BooleanField(default=False)
    native_text_available = models.BooleanField(default=False)
    native_text_quality = models.CharField(max_length=32, choices=NativeTextQuality.choices, default=NativeTextQuality.UNRESOLVED)
    text_classification = models.CharField(max_length=32, choices=DocumentTextClassification.choices, default=DocumentTextClassification.EMPTY_OR_UNRESOLVED)
    ocr_requirement = models.CharField(max_length=32, choices=OcrRequirement.choices, default=OcrRequirement.NOT_REQUIRED)
    ocr_pages_recommended = models.JSONField(default=list, blank=True)
    language_hints = models.JSONField(default=list, blank=True)
    parser_recommendation = models.CharField(max_length=128, blank=True)
    inspection_method = models.CharField(max_length=128)
    inspector_name = models.CharField(max_length=128)
    inspector_version = models.CharField(max_length=64)
    inspection_confidence = models.FloatField(default=0)
    warnings = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_source_profile"
        constraints = [
            models.UniqueConstraint(fields=["job", "attempt", "source_checksum", "pipeline_version", "inspector_version"], name="cp_profile_identity_unique"),
            models.CheckConstraint(condition=models.Q(inspection_confidence__gte=0) & models.Q(inspection_confidence__lte=1), name="cp_profile_confidence_range"),
        ]

    def clean(self) -> None:
        if self.password_required and not self.encrypted:
            raise ValidationError("A password-required document must be encrypted.")
        if self.ocr_requirement == OcrRequirement.REQUIRED and self.text_classification not in {DocumentTextClassification.SCANNED, DocumentTextClassification.EMPTY_OR_UNRESOLVED}:
            raise ValidationError("Required OCR must agree with the text classification.")
        if not 0 <= self.inspection_confidence <= 1:
            raise ValidationError("Inspection confidence must be between zero and one.")


class DocumentExtraction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.CASCADE, related_name="document_extractions")
    attempt = models.ForeignKey("content_processing.ProcessingAttempt", on_delete=models.CASCADE, related_name="document_extractions")
    source_document_profile = models.ForeignKey(SourceDocumentProfile, on_delete=models.PROTECT, related_name="extractions")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.SET_NULL, null=True, blank=True, related_name="document_extractions")
    stored_file = models.ForeignKey("storage.StoredFile", on_delete=models.PROTECT, related_name="document_extractions")
    pipeline_version = models.CharField(max_length=100)
    source_checksum = models.CharField(max_length=128)
    extractor_name = models.CharField(max_length=128)
    extractor_version = models.CharField(max_length=64)
    ocr_engine = models.CharField(max_length=128, blank=True)
    ocr_engine_version = models.CharField(max_length=64, blank=True)
    extraction_method = models.CharField(max_length=32, choices=ExtractionMethod.choices)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    native_text_pages = models.PositiveIntegerField(default=0)
    ocr_pages = models.PositiveIntegerField(default=0)
    block_count = models.PositiveIntegerField(default=0)
    text_character_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    result_checksum = models.CharField(max_length=128)
    status = models.CharField(max_length=32, choices=ExtractionStatus.choices, default=ExtractionStatus.COMPLETED)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "content_processing_document_extraction"
        constraints = [models.UniqueConstraint(fields=["job", "attempt", "source_checksum", "pipeline_version", "extractor_version"], name="cp_extraction_identity_unique")]


class ExtractedBlock(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_extraction = models.ForeignKey(DocumentExtraction, on_delete=models.CASCADE, related_name="blocks")
    job = models.ForeignKey("content_processing.ContentProcessingJob", on_delete=models.CASCADE, related_name="extracted_blocks")
    attempt = models.ForeignKey("content_processing.ProcessingAttempt", on_delete=models.CASCADE, related_name="extracted_blocks")
    source_document_profile = models.ForeignKey(SourceDocumentProfile, on_delete=models.PROTECT, related_name="blocks")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.SET_NULL, null=True, blank=True, related_name="extracted_blocks")
    stored_file = models.ForeignKey("storage.StoredFile", on_delete=models.PROTECT, related_name="extracted_blocks")
    pipeline_version = models.CharField(max_length=100)
    page_reference = models.JSONField(default=dict, blank=True)
    sequence_number = models.PositiveIntegerField()
    page_sequence_number = models.PositiveIntegerField(default=0)
    block_type = models.CharField(max_length=32, choices=ExtractedBlockType.choices)
    evidence_origin = models.CharField(max_length=32, choices=EvidenceOrigin.choices)
    raw_text = models.TextField(blank=True)
    normalized_text = models.TextField(blank=True)
    character_count = models.PositiveIntegerField(default=0)
    geometry = models.JSONField(default=dict, blank=True)
    typography = models.JSONField(default=dict, blank=True)
    structural_hints = models.JSONField(default=dict, blank=True)
    source_method = models.CharField(max_length=64)
    table_reference = models.CharField(max_length=128, blank=True)
    image_reference = models.CharField(max_length=128, blank=True)
    confidence = models.FloatField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "content_processing_extracted_block"
        ordering = ["sequence_number"]
        constraints = [
            models.UniqueConstraint(fields=["document_extraction", "sequence_number"], name="cp_block_sequence_unique"),
            models.CheckConstraint(condition=models.Q(confidence__gte=0) & models.Q(confidence__lte=1), name="cp_block_confidence_range"),
        ]
        indexes = [
            models.Index(fields=["job", "attempt"], name="cp_block_job_attempt_idx"),
            models.Index(fields=["document_extraction", "block_type"], name="cp_block_type_idx"),
        ]

    def clean(self) -> None:
        self.raw_text = sanitize_source_text(self.raw_text)
        self.normalized_text = sanitize_source_text(self.normalized_text)
        self.character_count = len(self.normalized_text)
        if not self.normalized_text and self.block_type not in {ExtractedBlockType.IMAGE, ExtractedBlockType.TABLE}:
            raise ValidationError("Text blocks must contain storage-safe text.")
        if not 0 <= self.confidence <= 1:
            raise ValidationError("Block confidence must be between zero and one.")


__all__ = [name for name in (
    "SourceFormat", "DocumentTextClassification", "NativeTextQuality", "OcrRequirement", "ExtractedBlockType",
    "EvidenceOrigin", "ExtractionMethod", "ExtractionStatus", "BoundingBox", "PageReference", "sanitize_source_text",
    "SourceDocumentProfile", "DocumentExtraction", "ExtractedBlock",
)]
