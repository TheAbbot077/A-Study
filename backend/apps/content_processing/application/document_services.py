from __future__ import annotations

import hashlib
import json
import os

from django.db import transaction

from apps.content_processing.domain.extraction import DocumentExtraction, ExtractedBlock, ExtractionStatus, SourceDocumentProfile, SourceFormat
from apps.content_processing.infrastructure.document_extraction import (
    DocxDocumentExtractor, DocxDocumentInspector, PdfDocumentExtractor, PdfDocumentInspector, StoragePlatformSourceReader, detect_source_format,
)


class DocumentProcessingError(RuntimeError):
    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


class InspectSourceDocumentService:
    def __init__(self, reader=None, inspectors=None) -> None:
        self.reader = reader or StoragePlatformSourceReader()
        self.inspectors = inspectors or (PdfDocumentInspector(), DocxDocumentInspector())

    def execute(self, context):
        if not context.stored_file_id:
            raise DocumentProcessingError("The source file is missing.", "storage_read_failed")
        source = self.reader.read(context.stored_file_id)
        detected_format, detected_mime, detection_warnings = detect_source_format(source)
        if detected_format == SourceFormat.UNKNOWN:
            raise DocumentProcessingError("The uploaded file format is not supported.", "unsupported_format")
        inspector = next(item for item in self.inspectors if item.supports(detected_format))
        evidence = inspector.inspect(source)
        if evidence.password_required:
            raise DocumentProcessingError("The PDF requires a password.", "password_required")
        if evidence.corrupt:
            raise DocumentProcessingError("The document is corrupt or malformed.", "corrupt_document")
        existing = SourceDocumentProfile.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id, source_checksum=source.checksum, pipeline_version=context.pipeline_version, inspector_version=inspector.version).first()
        if existing:
            return existing, [*detection_warnings, *evidence.warnings]
        profile = SourceDocumentProfile(
            job_id=context.job_id, attempt_id=context.attempt_id, resource_id=context.resource_id, stored_file_id=context.stored_file_id,
            pipeline_version=context.pipeline_version, source_filename=source.filename, file_extension=os.path.splitext(source.filename)[1].lower(),
            declared_content_type=source.declared_content_type, detected_format=evidence.detected_format, detected_mime_type=detected_mime,
            file_size_bytes=source.size_bytes, source_checksum=source.checksum, signature_summary={"prefix_hex": source.content[:8].hex()},
            page_count=evidence.page_count, encrypted=evidence.encrypted, password_required=evidence.password_required, corrupt=evidence.corrupt,
            native_text_available=evidence.native_text_available, native_text_quality=evidence.native_text_quality, text_classification=evidence.text_classification,
            ocr_requirement=evidence.ocr_requirement, ocr_pages_recommended=list(evidence.ocr_pages_recommended), parser_recommendation=evidence.parser_recommendation,
            inspection_method=inspector.name, inspector_name=inspector.name, inspector_version=inspector.version, inspection_confidence=evidence.confidence,
            warnings=[*detection_warnings, *evidence.warnings],
        )
        profile.full_clean()
        profile.save()
        return profile, profile.warnings


class ValidateExtractionService:
    def validate(self, profile, evidence) -> None:
        if not evidence.blocks:
            raise DocumentProcessingError("No trustworthy extractable evidence was found.", "no_extractable_content")
        sequences = [block.sequence_number for block in evidence.blocks]
        if sequences != list(range(len(sequences))) or len(sequences) != len(set(sequences)):
            raise DocumentProcessingError("Extraction block order is invalid.", "extraction_output_invalid")
        if any(not 0 <= block.confidence <= 1 for block in evidence.blocks):
            raise DocumentProcessingError("Extraction confidence is invalid.", "extraction_output_invalid")


class ExtractDocumentService:
    def __init__(self, reader=None, extractors=None, validator=None) -> None:
        self.reader = reader or StoragePlatformSourceReader()
        self.extractors = extractors or (PdfDocumentExtractor(), DocxDocumentExtractor())
        self.validator = validator or ValidateExtractionService()

    def execute(self, context, profile):
        source = self.reader.read(context.stored_file_id)
        if source.checksum != profile.source_checksum:
            raise DocumentProcessingError("The source checksum changed after inspection.", "extraction_output_invalid")
        extractor = next(item for item in self.extractors if item.supports(profile.detected_format))
        existing = DocumentExtraction.objects.filter(job_id=context.job_id, attempt_id=context.attempt_id, source_checksum=source.checksum, pipeline_version=context.pipeline_version, extractor_version=extractor.version).first()
        if existing:
            return existing, list(profile.warnings)
        evidence = extractor.extract(source, profile)
        self.validator.validate(profile, evidence)
        canonical = [{"sequence": b.sequence_number, "page": b.page_reference.get("page_index"), "type": b.block_type, "text": b.normalized_text, "origin": b.evidence_origin} for b in evidence.blocks]
        result_checksum = hashlib.sha256(json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        with transaction.atomic():
            extraction = DocumentExtraction.objects.create(
                job_id=context.job_id, attempt_id=context.attempt_id, source_document_profile=profile, resource_id=context.resource_id,
                stored_file_id=context.stored_file_id, pipeline_version=context.pipeline_version, source_checksum=source.checksum,
                extractor_name=extractor.name, extractor_version=extractor.version, ocr_engine=evidence.ocr_engine, ocr_engine_version=evidence.ocr_engine_version,
                extraction_method=evidence.method, page_count=evidence.page_count, native_text_pages=evidence.native_text_pages, ocr_pages=evidence.ocr_pages,
                block_count=len(evidence.blocks), text_character_count=sum(len(b.normalized_text) for b in evidence.blocks), warning_count=len(evidence.warnings),
                result_checksum=result_checksum, status=ExtractionStatus.COMPLETED_WITH_WARNINGS if evidence.warnings else ExtractionStatus.COMPLETED,
            )
            rows = []
            for block in evidence.blocks:
                row = ExtractedBlock(
                    document_extraction=extraction, job_id=context.job_id, attempt_id=context.attempt_id, source_document_profile=profile,
                    resource_id=context.resource_id, stored_file_id=context.stored_file_id, pipeline_version=context.pipeline_version,
                    page_reference=block.page_reference, sequence_number=block.sequence_number, page_sequence_number=block.page_sequence_number,
                    block_type=block.block_type, evidence_origin=block.evidence_origin, raw_text=block.raw_text, normalized_text=block.normalized_text,
                    character_count=len(block.normalized_text), geometry=block.geometry, typography=block.typography, structural_hints=block.structural_hints,
                    source_method=block.source_method, table_reference=block.table_reference, image_reference=block.image_reference,
                    confidence=block.confidence, metadata=block.metadata,
                )
                row.full_clean()
                rows.append(row)
            ExtractedBlock.objects.bulk_create(rows)
        return extraction, list(evidence.warnings)


class FlatTextCompatibilityMapper:
    def project(self, extraction: DocumentExtraction) -> str:
        parts: list[str] = []
        for block in extraction.blocks.order_by("sequence_number"):
            if block.normalized_text and block.block_type != "image":
                parts.append(block.normalized_text)
        return "\n\n".join(parts).replace("\x00", "")


class LegacyBlockExtractionService:
    """Temporary content-intelligence adapter; ordered blocks remain authoritative."""

    def __init__(self, extraction: DocumentExtraction) -> None:
        self.extraction = extraction

    def extract(self, job):
        from apps.content_intelligence.domain.models import ContentExtractionResult
        from apps.content_intelligence.infrastructure.persistence.repositories import DjangoContentExtractionResultRepository
        text = FlatTextCompatibilityMapper().project(self.extraction)
        result = ContentExtractionResult(
            import_job=job,
            extracted_text=text,
            normalized_text=text,
            extraction_method=f"layout_blocks:{self.extraction.extractor_name}:{self.extraction.extractor_version}",
            sufficient_text=bool(text.strip()),
            ocr_requested=self.extraction.ocr_pages > 0,
            ocr_used=self.extraction.ocr_pages > 0,
            char_count=len(text),
            page_count=self.extraction.page_count,
            metadata={"document_extraction_id": str(self.extraction.id), "source_of_truth": "ordered_extracted_blocks"},
        )
        return DjangoContentExtractionResultRepository().save_result(result)
