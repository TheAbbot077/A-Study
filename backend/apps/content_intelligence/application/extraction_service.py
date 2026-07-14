from __future__ import annotations

import logging
from io import BytesIO, UnsupportedOperation
from typing import Optional

from apps.content_intelligence.application.text_sanitizer import sanitize_extraction_payload
from apps.content_intelligence.domain.exceptions import ExtractionError, UnsupportedFormatError
from apps.content_intelligence.domain.models import ContentExtractionResult, ContentImportJob
from apps.content_intelligence.domain.repositories import ContentExtractionResultRepository
from apps.content_intelligence.domain.services import ExtractionPayload
from apps.content_intelligence.infrastructure.extraction import DocxExtractionAdapter, PdfExtractionAdapter
from apps.content_intelligence.infrastructure.extraction.adapters import MIN_MEANINGFUL_CHARACTERS, meaningful_character_count
from apps.content_intelligence.infrastructure.ocr import FallbackOCRService
from apps.content_intelligence.infrastructure.persistence import DjangoContentExtractionResultRepository
from apps.core.events import BusinessEvent, EventPublisher
from apps.storage.infrastructure.providers import LocalStorageProvider

logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(
        self,
        result_repository: Optional[ContentExtractionResultRepository] = None,
        storage_provider=None,
        pdf_adapter: Optional[PdfExtractionAdapter] = None,
        docx_adapter: Optional[DocxExtractionAdapter] = None,
        ocr_service: Optional[FallbackOCRService] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.result_repository = result_repository or DjangoContentExtractionResultRepository()
        self.storage_provider = storage_provider or LocalStorageProvider()
        self.pdf_adapter = pdf_adapter or PdfExtractionAdapter()
        self.docx_adapter = docx_adapter or DocxExtractionAdapter()
        self.ocr_service = ocr_service or FallbackOCRService()
        self.event_publisher = event_publisher or EventPublisher()

    def extract(self, job: ContentImportJob) -> ContentExtractionResult:
        if job.stored_file is None:
            raise UnsupportedFormatError("Content import job has no stored file.")
        file_obj = self.storage_provider.download(job.stored_file.stored_filename)
        initial_position = self._safe_position(file_obj)
        try:
            file_bytes = self._read_all_bytes(file_obj)
        finally:
            final_position = self._safe_position(file_obj)
            close = getattr(file_obj, "close", None)
            if callable(close):
                close()
        diagnostics = self._base_diagnostics(job, file_bytes, initial_position, final_position)
        logger.info(
            "Content extraction starting: job_id=%s format_type=%s byte_count=%s adapter=%s",
            job.id,
            job.format_type,
            len(file_bytes),
            self._adapter_name(job.format_type),
        )
        if not file_bytes:
            raise self._build_extraction_error(
                "The uploaded file is empty.",
                code="empty_stored_file",
                diagnostics=diagnostics,
            )

        try:
            payload = self._sanitize_payload(job, self._extract_from_stream(job.format_type, BytesIO(file_bytes)))
        except ExtractionError as exc:
            diagnostics.update(exc.details or {})
            raise self._build_extraction_error(str(exc), code=exc.code, diagnostics=diagnostics)
        diagnostics = self._merge_payload_diagnostics(diagnostics, payload)
        logger.info(
            "Content extraction primary result: job_id=%s format_type=%s extracted_chars=%s normalized_chars=%s meaningful_chars=%s ocr_attempted=%s parser_diagnostic=%s",
            job.id,
            job.format_type,
            len(payload.extracted_text),
            len(payload.normalized_text),
            diagnostics.get("meaningful_character_count"),
            False,
            payload.metadata.get("parser_error") if isinstance(payload.metadata, dict) else None,
        )

        ocr_requested = False
        ocr_used = False
        native_failure_code = diagnostics.get("structural_failure")
        if native_failure_code in {
            "parser_dependency_unavailable",
            "invalid_pdf_signature",
            "encrypted_pdf",
            "malformed_pdf",
            "invalid_docx_signature",
            "invalid_docx_container",
            "malformed_docx",
        }:
            raise self._build_extraction_error(
                "Unable to extract sufficient text from this document.",
                code=str(native_failure_code),
                diagnostics=diagnostics,
            )

        if not payload.sufficient_text and job.format_type == ContentImportJob.FormatType.PDF:
            job.mark_ocr_requested()
            ocr_requested = True
            self.event_publisher.publish(
                BusinessEvent.create(
                    "content_intelligence.ocr_requested",
                    payload={"content_import_job_id": str(job.id), "learning_resource_id": str(job.learning_resource_id)},
                )
            )
            payload = self._sanitize_payload(job, self.ocr_service.extract_text(BytesIO(file_bytes), job.format_type))
            diagnostics = self._merge_payload_diagnostics(diagnostics, payload, ocr_attempted=True)
            job.mark_ocr_completed()
            ocr_used = True
            logger.info(
                "Content extraction OCR result: job_id=%s format_type=%s extracted_chars=%s normalized_chars=%s meaningful_chars=%s ocr_attempted=%s parser_diagnostic=%s",
                job.id,
                job.format_type,
                len(payload.extracted_text),
                len(payload.normalized_text),
                diagnostics.get("ocr_meaningful_character_count", diagnostics.get("meaningful_character_count")),
                True,
                payload.metadata.get("warning") if isinstance(payload.metadata, dict) else None,
            )
            self.event_publisher.publish(
                BusinessEvent.create(
                    "content_intelligence.ocr_completed",
                    payload={"content_import_job_id": str(job.id), "learning_resource_id": str(job.learning_resource_id)},
                )
            )
            if not payload.sufficient_text:
                raise self._build_extraction_error(
                    "Unable to extract sufficient text from this document.",
                    code="extracted_text_below_threshold",
                    diagnostics=diagnostics,
                )
        elif not payload.sufficient_text:
            raise self._build_extraction_error(
                "Unable to extract sufficient text from this document.",
                code="extracted_text_below_threshold",
                diagnostics=diagnostics,
            )

        result = self.result_repository.get_for_job(job) or ContentExtractionResult(import_job=job)
        result.extracted_text = payload.extracted_text
        result.normalized_text = payload.normalized_text
        result.extraction_method = payload.extraction_method
        result.sufficient_text = payload.sufficient_text
        result.ocr_requested = ocr_requested
        result.ocr_used = ocr_used
        result.char_count = len(payload.normalized_text)
        result.page_count = payload.page_count
        result.metadata = diagnostics
        result = self.result_repository.save_result(result)
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_intelligence.extraction_completed",
                payload={
                    "content_import_job_id": str(job.id),
                    "learning_resource_id": str(job.learning_resource_id),
                    "extraction_method": result.extraction_method,
                    "char_count": result.char_count,
                    "ocr_used": result.ocr_used,
                },
            )
        )
        return result

    def _extract_from_stream(self, format_type: str, file_obj):
        if format_type == ContentImportJob.FormatType.PDF:
            return self.pdf_adapter.extract(file_obj)
        if format_type == ContentImportJob.FormatType.DOCX:
            return self.docx_adapter.extract(file_obj)
        raise UnsupportedFormatError(f"Unsupported content import format: {format_type}.")

    def _read_all_bytes(self, stream) -> bytes:
        seek = getattr(stream, "seek", None)
        if callable(seek):
            try:
                seek(0)
            except (OSError, UnsupportedOperation):
                pass

        data = stream.read()
        if isinstance(data, str):
            data = data.encode("utf-8")

        return bytes(data or b"")

    def _sanitize_payload(self, job: ContentImportJob, payload: ExtractionPayload) -> ExtractionPayload:
        sanitized_payload, removed_count = sanitize_extraction_payload(payload)
        if removed_count:
            logger.warning(
                "Removed NUL bytes from extracted content: job_id=%s removed_count=%s",
                job.id,
                removed_count,
            )
        return sanitized_payload

    def _base_diagnostics(self, job: ContentImportJob, file_bytes: bytes, initial_position, final_position) -> dict:
        stored_file = job.stored_file
        original_filename = getattr(stored_file, "original_filename", "")
        return {
            "job_id": str(job.id) if job.id is not None else None,
            "resource_id": str(job.learning_resource_id) if job.learning_resource_id is not None else None,
            "stored_file_id": str(job.stored_file_id) if job.stored_file_id is not None else None,
            "original_filename": original_filename,
            "stored_filename": getattr(stored_file, "stored_filename", ""),
            "file_extension": (original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else ""),
            "mime_type": getattr(stored_file, "content_type", ""),
            "detected_format": job.format_type,
            "downloaded_byte_count": len(file_bytes),
            "signature_hex": file_bytes[:4].hex(),
            "stream_position_before_rewind": initial_position,
            "stream_position_after_read": final_position,
            "selected_adapter": self._adapter_name(job.format_type),
            "sufficiency_threshold": MIN_MEANINGFUL_CHARACTERS,
            "ocr_attempted": False,
        }

    def _merge_payload_diagnostics(self, diagnostics: dict, payload: ExtractionPayload, *, ocr_attempted: bool = False) -> dict:
        metadata = dict(payload.metadata or {})
        merged = dict(diagnostics)
        merged.update(metadata)
        prefix = "ocr_" if ocr_attempted else ""
        merged[f"{prefix}raw_character_count"] = len(payload.extracted_text)
        merged[f"{prefix}normalized_character_count"] = len(payload.normalized_text)
        merged[f"{prefix}meaningful_character_count"] = metadata.get(
            "meaningful_character_count",
            meaningful_character_count(payload.normalized_text),
        )
        if payload.page_count is not None:
            merged["page_count"] = payload.page_count
        if metadata.get("paragraph_count") is not None:
            merged["paragraph_count"] = metadata.get("paragraph_count")
        if metadata.get("table_count") is not None:
            merged["table_count"] = metadata.get("table_count")
        if metadata.get("parser_error"):
            merged[f"{prefix}parser_error"] = metadata.get("parser_error")
        if metadata.get("parser_exception_class"):
            merged[f"{prefix}parser_exception_class"] = metadata.get("parser_exception_class")
        if metadata.get("warning"):
            merged[f"{prefix}warning"] = metadata.get("warning")
        if metadata.get("ocr_engine_available") is not None:
            merged["ocr_engine_available"] = metadata.get("ocr_engine_available")
        if metadata.get("pdf_rasterizer_available") is not None:
            merged["pdf_rasterizer_available"] = metadata.get("pdf_rasterizer_available")
        if metadata.get("dependency_available") is not None:
            merged[f"{prefix}parser_dependency_available"] = metadata.get("dependency_available")
        if metadata.get("parser_library"):
            merged[f"{prefix}parser_library"] = metadata.get("parser_library")
        if metadata.get("ocr_engine"):
            merged["ocr_engine"] = metadata.get("ocr_engine")
        if metadata.get("pdf_rasterizer"):
            merged["pdf_rasterizer"] = metadata.get("pdf_rasterizer")
        if metadata.get("structural_failure"):
            merged["structural_failure"] = metadata.get("structural_failure")
        if metadata.get("nul_bytes_removed") is not None:
            merged["nul_bytes_removed"] = metadata.get("nul_bytes_removed")
        merged[f"{prefix}adapter"] = metadata.get("adapter", merged.get("selected_adapter"))
        merged["extraction_method"] = payload.extraction_method
        merged["ocr_attempted"] = diagnostics.get("ocr_attempted", False) or ocr_attempted
        return merged

    def _build_extraction_error(self, message: str, *, code: str, diagnostics: dict) -> ExtractionError:
        details = dict(diagnostics)
        details["failure_reason"] = (
            diagnostics.get("ocr_warning")
            or diagnostics.get("ocr_parser_error")
            or diagnostics.get("parser_error")
            or diagnostics.get("structural_failure")
            or code
        )
        return ExtractionError(message, code=code, details=details)

    def _safe_position(self, stream):
        tell = getattr(stream, "tell", None)
        if not callable(tell):
            return None
        try:
            return tell()
        except (OSError, UnsupportedOperation):
            return None

    def _adapter_name(self, format_type: str) -> str:
        if format_type == ContentImportJob.FormatType.PDF:
            return "pdf"
        if format_type == ContentImportJob.FormatType.DOCX:
            return "docx"
        return "unknown"
