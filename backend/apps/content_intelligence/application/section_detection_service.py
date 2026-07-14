from __future__ import annotations

import re

from apps.content_intelligence.application.document_text_normalization_service import DocumentTextNormalizationService
from apps.content_intelligence.application.heading_normalization_service import HeadingNormalizationService
from apps.content_intelligence.domain.models import ParsedDocument, ParsedSection
from apps.core.events import BusinessEvent, EventPublisher


class SectionDetectionService:
    FALLBACK_HEADING = "Imported Content"
    LARGE_FALLBACK_THRESHOLD = 12000
    _SYNTHETIC_PLACEHOLDER_HEADINGS = {
        "imported content",
        "untitled section",
        "document content",
        "main content",
        "section 1",
    }
    _HEADING_PATTERNS = [
        re.compile(r"^(chapter|section|unit|lesson|topic)\s+(\d+|[ivxlcdm]+|[A-Za-z]+)(?:\s*[:.\-]\s*|\s+.+)$", re.IGNORECASE),
        re.compile(r"^\d+(?:\.\d+)*\s*[:.\-)]\s+\S+"),
    ]
    _FRONT_MATTER_HEADINGS = {"contents", "table of contents", "preface", "acknowledgements", "dedication", "copyright", "index", "bibliography"}
    _APPENDIX_PREFIXES = ("appendix",)
    _INFERRED_HEADING_PATTERNS = [
        re.compile(r"^(chapter|section|unit|lesson|topic)\s+(\d+|[ivxlcdm]+|[A-Za-z]+)(?:\s*[:.\-]\s*|\s+.+)$", re.IGNORECASE),
        re.compile(r"^\d+(?:\.\d+)*\s*[:.\-)]\s+\S+"),
        re.compile(r"^[A-Z][A-Za-z0-9,\-()' ]{2,80}$"),
        re.compile(r"^[A-Z][A-Z0-9\s\-]{3,80}$"),
    ]

    def __init__(
        self,
        event_publisher: EventPublisher | None = None,
        heading_normalization_service: HeadingNormalizationService | None = None,
        text_normalization_service: DocumentTextNormalizationService | None = None,
    ) -> None:
        self.event_publisher = event_publisher or EventPublisher()
        self.heading_normalization_service = heading_normalization_service or HeadingNormalizationService()
        self.text_normalization_service = text_normalization_service or DocumentTextNormalizationService()

    def detect_sections(self, parsed_document: ParsedDocument) -> list[ParsedSection]:
        text = parsed_document.normalized_text or ""
        blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
        sections: list[ParsedSection] = []
        current_heading = self.FALLBACK_HEADING
        current_lines: list[str] = []
        current_metadata: dict[str, object] = {
            "section_classification": "academic_content",
            "section_origin": "synthetic_fallback",
        }
        sequence_number = 1
        skipped_front_matter = 0
        skipped_navigation = 0

        for block in blocks:
            heading = self._heading_for(block)
            if heading and current_lines:
                section = self._build_section(parsed_document, current_heading, current_lines, sequence_number, current_metadata)
                if self._should_keep_section(section):
                    sections.append(section)
                    sequence_number += 1
                else:
                    skipped_front_matter += int(section.metadata.get("section_classification") == "front_matter")
                    skipped_navigation += int(section.metadata.get("section_classification") == "navigation")
                current_heading = heading
                current_metadata = self._metadata_for_heading(heading)
                current_lines = [self._body_without_heading(block)]
                continue
            if heading:
                current_heading = heading
                current_metadata = self._metadata_for_heading(heading)
                current_lines = [self._body_without_heading(block)]
                continue
            current_lines.append(block)

        if current_lines or not sections:
            section = self._build_section(parsed_document, current_heading, current_lines, sequence_number, current_metadata)
            if self._should_keep_section(section):
                sections.append(section)
            else:
                skipped_front_matter += int(section.metadata.get("section_classification") == "front_matter")
                skipped_navigation += int(section.metadata.get("section_classification") == "navigation")

        sections = self._subdivide_large_sections(parsed_document, sections)

        self.event_publisher.publish(
            BusinessEvent.create(
                "content_intelligence.sections_detected",
                payload={
                    "content_import_job_id": str(parsed_document.import_job_id),
                    "parsed_document_id": str(parsed_document.id),
                    "section_count": len(sections),
                },
            )
        )
        if hasattr(parsed_document, "metadata"):
            metadata = dict(parsed_document.metadata or {})
            metadata["front_matter_sections_skipped"] = skipped_front_matter
            metadata["navigation_sections_skipped"] = skipped_navigation
            metadata["secondary_subdivision_attempted"] = any(
                (section.metadata or {}).get("section_origin") == "inferred_heading" for section in sections
            )
            parsed_document.metadata = metadata
        return sections

    def _heading_for(self, block: str) -> str | None:
        first_line = block.splitlines()[0].strip()
        if not first_line:
            return None
        line_classification = self.text_normalization_service.classify_line(first_line)
        if line_classification in {"page_marker", "date_like", "table_of_contents", "malformed_fragment"}:
            return None
        normalized = self.heading_normalization_service.normalize(first_line)
        if self._is_synthetic_placeholder_heading(normalized.normalized_heading):
            return None
        if any(pattern.match(first_line) for pattern in self._HEADING_PATTERNS):
            return normalized.normalized_heading[:255]
        word_count = len(first_line.split())
        if len(first_line) <= 90 and first_line == first_line.title() and 2 <= word_count <= 8:
            return normalized.normalized_heading[:255]
        return None

    def _metadata_for_heading(self, heading: str) -> dict[str, object]:
        classification = self._classify_heading(heading)
        normalized = self.heading_normalization_service.normalize(heading)
        return {
            "section_classification": classification,
            "section_origin": "detected_heading",
            "normalized_heading": normalized.normalized_heading,
            "semantic_title": normalized.semantic_title,
            "structural_prefix": normalized.structural_prefix,
            "heading_sequence_number": normalized.sequence_number,
        }

    def _classify_heading(self, heading: str) -> str:
        normalized = self.heading_normalization_service.normalize(heading)
        lowered = normalized.normalized_heading.lower()
        semantic_title = normalized.semantic_title.lower()
        combined = f"{lowered} {semantic_title}".strip()
        if any(prefix in lowered for prefix in self._APPENDIX_PREFIXES):
            return "appendix"
        if combined in self._FRONT_MATTER_HEADINGS or lowered in self._FRONT_MATTER_HEADINGS or semantic_title in self._FRONT_MATTER_HEADINGS:
            if "index" in combined or "bibliography" in combined:
                return "reference"
            if "contents" in combined:
                return "navigation"
            return "front_matter"
        return "academic_content"

    def _body_without_heading(self, block: str) -> str:
        lines = block.splitlines()
        body_lines = [line for line in lines[1:] if line.strip()] if len(lines) > 1 else []
        return "\n".join(body_lines).strip()

    def _build_section(
        self,
        parsed_document: ParsedDocument,
        heading: str,
        lines: list[str],
        sequence_number: int,
        heading_metadata: dict[str, object],
    ) -> ParsedSection:
        body_text = "\n\n".join(line for line in lines if line).strip()
        normalized = self.heading_normalization_service.normalize(heading)
        section_classification = str(heading_metadata.get("section_classification", "academic_content"))
        if section_classification == "appendix":
            section_type = ParsedSection.SectionType.APPENDIX
        elif section_classification in {"front_matter", "navigation", "reference"}:
            section_type = ParsedSection.SectionType.FRONT_MATTER
        elif heading == self.FALLBACK_HEADING:
            section_type = ParsedSection.SectionType.UNKNOWN
        else:
            section_type = ParsedSection.SectionType.CHAPTER

        confidence = 0.85 if normalized.semantic_title or heading != self.FALLBACK_HEADING else 0.55
        if section_classification in {"front_matter", "navigation", "reference"}:
            confidence = 0.3
        metadata = {
            "body_char_count": len(body_text),
            **heading_metadata,
            "original_heading": heading,
        }
        return ParsedSection(
            parsed_document=parsed_document,
            heading=heading[:255],
            body_text=body_text,
            sequence_number=sequence_number,
            section_type=section_type,
            confidence=confidence,
            metadata=metadata,
        )

    def _should_keep_section(self, section: ParsedSection) -> bool:
        return section.metadata.get("section_classification") not in {"front_matter", "navigation", "reference"}

    def _subdivide_large_sections(self, parsed_document: ParsedDocument, sections: list[ParsedSection]) -> list[ParsedSection]:
        next_sections: list[ParsedSection] = []
        sequence_number = 1
        subdivision_attempted = False
        inferred_total = 0

        for section in sections:
            body_text = section.body_text.strip()
            if len(body_text) < self.LARGE_FALLBACK_THRESHOLD:
                section.sequence_number = sequence_number
                next_sections.append(section)
                sequence_number += 1
                continue

            inferred_sections = self._infer_sections_from_text(parsed_document, body_text)
            section_metadata = dict(section.metadata or {})
            section_metadata["subdivision_attempted"] = True
            section_metadata["inferred_subsections_found"] = len(inferred_sections)
            section.metadata = section_metadata
            subdivision_attempted = True

            replace_threshold = 1 if section_metadata.get("section_origin") == "synthetic_fallback" else 2
            if len(inferred_sections) >= replace_threshold:
                inferred_total += len(inferred_sections)
                for inferred_section in inferred_sections:
                    inferred_section.sequence_number = sequence_number
                    next_sections.append(inferred_section)
                    sequence_number += 1
                continue

            section.sequence_number = sequence_number
            next_sections.append(section)
            sequence_number += 1

        if hasattr(parsed_document, "metadata"):
            metadata = dict(parsed_document.metadata or {})
            metadata["secondary_subdivision_attempted"] = subdivision_attempted
            metadata["fallback_subsections_found"] = inferred_total
            parsed_document.metadata = metadata
        return next_sections

    def _infer_sections_from_text(self, parsed_document: ParsedDocument, body_text: str) -> list[ParsedSection]:
        lines = [line.rstrip() for line in body_text.splitlines()]
        sections: list[ParsedSection] = []
        current_heading: str | None = None
        current_lines: list[str] = []
        sequence_number = 1

        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                if current_heading and current_lines and current_lines[-1] != "":
                    current_lines.append("")
                continue

            inferred_heading = self._inferred_heading_for_line(stripped, index, lines)
            if inferred_heading:
                if current_heading and any(item.strip() for item in current_lines):
                    sections.append(self._build_inferred_section(parsed_document, current_heading, current_lines, sequence_number))
                    sequence_number += 1
                current_heading = inferred_heading
                current_lines = []
                continue
            if current_heading:
                current_lines.append(stripped)

        if current_heading and any(item.strip() for item in current_lines):
            sections.append(self._build_inferred_section(parsed_document, current_heading, current_lines, sequence_number))

        return [section for section in sections if section.body_text.strip()]

    def _inferred_heading_for_line(self, line: str, index: int, lines: list[str]) -> str | None:
        if not line:
            return None
        classification = self.text_normalization_service.classify_line(line)
        if classification != "academic_content":
            return None
        next_non_empty = ""
        for candidate in lines[index + 1 :]:
            if candidate.strip():
                next_non_empty = candidate.strip()
                break
        if not next_non_empty:
            return None
        if any(pattern.match(line) for pattern in self._INFERRED_HEADING_PATTERNS):
            return self.heading_normalization_service.normalize(line).normalized_heading[:255]
        word_count = len(line.split())
        if len(line) <= 90 and line == line.title() and 1 <= word_count <= 8:
            return self.heading_normalization_service.normalize(line).normalized_heading[:255]
        return None

    def _build_inferred_section(
        self,
        parsed_document: ParsedDocument,
        heading: str,
        lines: list[str],
        sequence_number: int,
    ) -> ParsedSection:
        metadata = self._metadata_for_heading(heading)
        metadata["section_origin"] = "inferred_heading"
        metadata["subdivision_attempted"] = True
        metadata["inferred_subsections_found"] = 1
        return self._build_section(parsed_document, heading, lines, sequence_number, metadata)

    def _is_synthetic_placeholder_heading(self, heading: str) -> bool:
        normalized_heading = heading.strip().lower()
        if normalized_heading in self._SYNTHETIC_PLACEHOLDER_HEADINGS:
            return True
        return bool(re.fullmatch(r"section\s+\d+", normalized_heading))
