from __future__ import annotations

import shutil

from apps.content_intelligence.domain.services import ExtractionPayload
from apps.content_intelligence.infrastructure.extraction.adapters import MIN_MEANINGFUL_CHARACTERS, meaningful_character_count


class FallbackOCRService:
    def extract_text(self, file_obj, format_type: str) -> ExtractionPayload:
        file_obj.seek(0)
        data = file_obj.read()
        tesseract_path = shutil.which("tesseract")
        pdftoppm_path = shutil.which("pdftoppm") or shutil.which("pdftocairo")
        dependency_available = bool(tesseract_path and pdftoppm_path)
        metadata = {
            "adapter": "ocr_fallback",
            "ocr_engine": "tesseract",
            "ocr_engine_available": bool(tesseract_path),
            "pdf_rasterizer": "poppler",
            "pdf_rasterizer_available": bool(pdftoppm_path),
            "byte_count": len(data),
            "signature_hex": data[:4].hex(),
            "sufficiency_threshold": MIN_MEANINGFUL_CHARACTERS,
        }

        if format_type != "pdf":
            return ExtractionPayload(
                extracted_text="",
                normalized_text="",
                extraction_method=f"{format_type}_ocr_fallback",
                sufficient_text=False,
                metadata={**metadata, "warning": "OCR is only supported for PDF imports."},
            )

        if not dependency_available:
            warnings: list[str] = []
            if not tesseract_path:
                warnings.append("OCR engine unavailable")
            if not pdftoppm_path:
                warnings.append("PDF rasterizer unavailable")
            return ExtractionPayload(
                extracted_text="",
                normalized_text="",
                extraction_method=f"{format_type}_ocr_fallback",
                sufficient_text=False,
                metadata={**metadata, "warning": "; ".join(warnings)},
            )

        try:
            from pdf2image import convert_from_bytes  # type: ignore
            import pytesseract  # type: ignore
        except Exception as exc:
            return ExtractionPayload(
                extracted_text="",
                normalized_text="",
                extraction_method=f"{format_type}_ocr_fallback",
                sufficient_text=False,
                metadata={
                    **metadata,
                    "warning": "OCR Python dependencies unavailable",
                    "parser_error": f"{exc.__class__.__name__}: {exc}",
                },
            )

        try:
            images = convert_from_bytes(data)
        except Exception as exc:
            return ExtractionPayload(
                extracted_text="",
                normalized_text="",
                extraction_method=f"{format_type}_ocr_fallback",
                sufficient_text=False,
                metadata={
                    **metadata,
                    "warning": "OCR rasterization failed",
                    "parser_error": f"{exc.__class__.__name__}: {exc}",
                },
            )

        page_texts: list[str] = []
        for image in images:
            try:
                page_texts.append(pytesseract.image_to_string(image) or "")
            except Exception as exc:
                return ExtractionPayload(
                    extracted_text="",
                    normalized_text="",
                    extraction_method=f"{format_type}_ocr_fallback",
                    sufficient_text=False,
                    page_count=len(images),
                    metadata={
                        **metadata,
                        "warning": "OCR execution failed",
                        "parser_error": f"{exc.__class__.__name__}: {exc}",
                    },
                )

        extracted_text = "\n\n".join(page_texts)
        normalized_text = extracted_text.replace("\r\n", "\n").replace("\r", "\n").strip()
        meaningful_count = meaningful_character_count(normalized_text)
        return ExtractionPayload(
            extracted_text=extracted_text,
            normalized_text=normalized_text,
            extraction_method=f"{format_type}_ocr_fallback",
            sufficient_text=meaningful_count >= MIN_MEANINGFUL_CHARACTERS,
            page_count=len(images),
            metadata={
                **metadata,
                "page_count": len(images),
                "meaningful_character_count": meaningful_count,
                "raw_character_count": len(extracted_text),
                "normalized_character_count": len(normalized_text),
                "warning": "OCR produced no text" if meaningful_count == 0 else None,
            },
        )
