from __future__ import annotations

import re

from apps.content_intelligence.application.concept_candidate_validator import ConceptCandidateValidator
from apps.content_intelligence.application.heading_normalization_service import HeadingNormalizationService
from apps.content_intelligence.domain.models import ParsedConceptCandidate, ParsedSection
from apps.core.events import BusinessEvent, EventPublisher


class ConceptExtractionService:
    SYNTHETIC_SECTION_TITLES = {
        "imported content",
        "untitled section",
        "document content",
        "main content",
    }

    def __init__(
        self,
        event_publisher: EventPublisher | None = None,
        heading_normalization_service: HeadingNormalizationService | None = None,
        validator: ConceptCandidateValidator | None = None,
    ) -> None:
        self.event_publisher = event_publisher or EventPublisher()
        self.heading_normalization_service = heading_normalization_service or HeadingNormalizationService()
        self.validator = validator or ConceptCandidateValidator()

    def extract_concepts(self, parsed_section: ParsedSection) -> list[ParsedConceptCandidate]:
        paragraphs = [paragraph.strip() for paragraph in parsed_section.body_text.split("\n\n") if paragraph.strip()]
        concepts: list[ParsedConceptCandidate] = []
        seen_titles: set[str] = set()
        duplicate_candidates_removed = 0
        synthetic_section_titles_skipped = 0

        heading_result = self.heading_normalization_service.normalize(parsed_section.heading)
        heading_title = heading_result.semantic_title
        heading_candidate_added = False
        if self._should_use_section_title(parsed_section, heading_title) and len(paragraphs) <= 1:
            candidate = self._build_candidate(
                parsed_section=parsed_section,
                title=heading_title,
                description=parsed_section.body_text or heading_title,
                sequence_number=len(concepts) + 1,
                seen_titles=seen_titles,
                source_label="section_heading",
                original_title=parsed_section.heading,
            )
            concepts.append(candidate)
            if candidate.metadata.get("title_semantic_key") in seen_titles:
                duplicate_candidates_removed += 1
            else:
                seen_titles.add(str(candidate.metadata.get("title_semantic_key", "")).strip())
                heading_candidate_added = True
        elif self._is_synthetic_placeholder_section(parsed_section):
            synthetic_section_titles_skipped += 1

        if heading_candidate_added and len(paragraphs) <= 1:
            paragraphs = []

        for paragraph in paragraphs:
            title = self._title_from(
                paragraph,
                allow_sentence_fallback=not self._is_synthetic_placeholder_section(parsed_section),
            )
            if not title:
                continue
            candidate = self._build_candidate(
                parsed_section=parsed_section,
                title=title,
                description=paragraph,
                sequence_number=len(concepts) + 1,
                seen_titles=seen_titles,
                source_label="body",
                original_title=title,
            )
            title_key = str(candidate.metadata.get("title_semantic_key", "")).strip()
            if title_key and title_key in seen_titles:
                duplicate_candidates_removed += 1
            else:
                if title_key:
                    seen_titles.add(title_key)
                concepts.append(candidate)

        if not concepts and not self._is_synthetic_placeholder_section(parsed_section):
            fallback_title = heading_title or parsed_section.heading
            concepts.append(
                self._build_candidate(
                    parsed_section=parsed_section,
                    title=fallback_title,
                    description=parsed_section.body_text or fallback_title,
                    sequence_number=1,
                    seen_titles=seen_titles,
                    source_label="fallback",
                    original_title=fallback_title,
                )
            )

        self.event_publisher.publish(
            BusinessEvent.create(
                "content_intelligence.concepts_extracted",
                payload={
                    "content_import_job_id": str(parsed_section.parsed_document.import_job_id),
                    "parsed_section_id": str(parsed_section.id),
                    "concept_count": len(concepts),
                },
            )
        )
        if hasattr(parsed_section, "metadata"):
            metadata = self._metadata_dict(getattr(parsed_section, "metadata", None))
            metadata["duplicate_candidates_removed"] = duplicate_candidates_removed
            metadata["synthetic_section_titles_skipped"] = synthetic_section_titles_skipped
            parsed_section.metadata = metadata
        return concepts

    def _build_candidate(
        self,
        *,
        parsed_section: ParsedSection,
        title: str,
        description: str,
        sequence_number: int,
        seen_titles: set[str],
        source_label: str,
        original_title: str,
    ) -> ParsedConceptCandidate:
        assessment = self.validator.validate(
            title=title,
            description=description,
            parsed_section=parsed_section,
            seen_titles=seen_titles,
            source_label=source_label,
        )
        normalized_title = assessment.normalized_title or title
        learning_objective = f"Understand {normalized_title.lower()}" if assessment.decision == "accepted" else ""
        metadata = {
            "original_title": original_title,
            "normalized_title": normalized_title,
            "decision": assessment.decision,
            "rejection_reasons": list(assessment.rejection_reasons),
            "supporting_text_length": len(description or ""),
            **assessment.metadata,
        }
        return ParsedConceptCandidate(
            parsed_section=parsed_section,
            title=normalized_title[:255],
            description=(description or "")[:2000],
            learning_objective=learning_objective[:2000],
            sequence_number=sequence_number,
            confidence=assessment.confidence,
            metadata=metadata,
        )

    def _title_from(self, paragraph: str, *, allow_sentence_fallback: bool = True) -> str:
        lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
        if not lines:
            return ""
        first_line = lines[0]
        if len(first_line.split()) <= 8 and len(first_line) <= 90 and first_line == first_line.title():
            return first_line.strip(" -:")
        if not allow_sentence_fallback:
            return ""
        first_sentence = re.split(r"[.!?]\s+", paragraph, maxsplit=1)[0].strip(" -:")
        if first_sentence:
            words = first_sentence.split()
            return " ".join(words[:8])
        return ""

    def _should_use_section_title(self, parsed_section: ParsedSection, heading_title: str) -> bool:
        return bool(heading_title) and not self._is_synthetic_placeholder_section(parsed_section)

    def _is_synthetic_placeholder_section(self, parsed_section: ParsedSection) -> bool:
        metadata = self._metadata_dict(getattr(parsed_section, "metadata", None))
        if metadata.get("section_origin") == "synthetic_fallback":
            return True
        normalized_heading = self.heading_normalization_service.normalize(parsed_section.heading).normalized_heading.lower()
        if normalized_heading in self.SYNTHETIC_SECTION_TITLES:
            return True
        if re.fullmatch(r"section\s+\d+", normalized_heading):
            return True
        return False

    def _metadata_dict(self, value: object) -> dict[str, object]:
        return value if isinstance(value, dict) else {}
