from __future__ import annotations

import re

from apps.content_intelligence.application.heading_normalization_service import HeadingNormalizationService
from apps.content_intelligence.application.document_text_normalization_service import DocumentTextNormalizationService
from apps.content_intelligence.domain.models import ParsedSection
from apps.content_intelligence.domain.services import ConceptCandidateAssessment


class ConceptCandidateScoringService:
    class Decision:
        ACCEPTED = "accepted"
        ACCEPTED_WITH_WARNING = "accepted_with_warning"
        REJECTED = "rejected"
        MANUAL_REVIEW = "manual_review"

    _DATE_LINE = re.compile(
        r"^(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+\d{1,2}(?:,\s*\d{4})?$",
        re.IGNORECASE,
    )
    _ROMAN_LINE = re.compile(r"^[ivxlcdm]{1,8}$", re.IGNORECASE)
    _PAGE_LINE = re.compile(r"^(?:page\s+)?\d{1,4}$", re.IGNORECASE)
    _ISBN_LINE = re.compile(r"^isbn(?:-13|-10)?[:\s]+\S+", re.IGNORECASE)
    _MOSTLY_NUMERIC = re.compile(r"^[\W_]*\d[\d\W_]*$")
    _MALFORMED_TOKEN = re.compile(r"\d+[A-Z][a-zA-Z]+|[A-Za-z]+\d+[A-Z][a-zA-Z]*")
    _GENERIC_NAVIGATION = re.compile(r"\b(contents?|table of contents|index|bibliography|copyright|isbn)\b", re.IGNORECASE)

    def __init__(
        self,
        heading_normalization_service: HeadingNormalizationService | None = None,
        text_normalization_service: DocumentTextNormalizationService | None = None,
    ) -> None:
        self.heading_normalization_service = heading_normalization_service or HeadingNormalizationService()
        self.text_normalization_service = text_normalization_service or DocumentTextNormalizationService()

    def assess(
        self,
        title: str,
        description: str,
        parsed_section: ParsedSection,
        *,
        seen_titles: set[str] | None = None,
        source_label: str = "body",
    ) -> ConceptCandidateAssessment:
        normalized_heading = self.heading_normalization_service.normalize(title)
        normalized_title = normalized_heading.semantic_title or normalized_heading.normalized_heading
        description = (description or "").strip()
        reasons: list[str] = []
        score = 0.5

        line_classification = self.text_normalization_service.classify_line(title)
        if line_classification in {"date_like", "navigation", "front_matter", "reference", "page_marker", "table_of_contents", "malformed_fragment"}:
            reasons.append(
                {
                    "date_like": "date_like",
                    "navigation": "navigation_text",
                    "front_matter": "navigation_text",
                    "reference": "navigation_text",
                    "page_marker": "page_marker",
                    "table_of_contents": "navigation_text",
                    "malformed_fragment": "malformed_tokenization",
                }[line_classification]
            )

        if normalized_heading.generic_structure:
            reasons.append("generic_structure")
        if normalized_heading.malformed_tokenization or self._MALFORMED_TOKEN.search(title.replace(" ", "")):
            reasons.append("malformed_tokenization")
        if self._DATE_LINE.fullmatch(normalized_title):
            reasons.append("date_like")
        if self._PAGE_LINE.fullmatch(normalized_title) or self._ROMAN_LINE.fullmatch(normalized_title):
            reasons.append("page_marker")
        if self._ISBN_LINE.match(normalized_title) or self._GENERIC_NAVIGATION.search(normalized_title):
            reasons.append("navigation_text")
        if self._MOSTLY_NUMERIC.fullmatch(normalized_title):
            reasons.append("mostly_numeric")
        if not description or len(description) < 20:
            reasons.append("insufficient_supporting_text")

        alpha_count = sum(char.isalpha() for char in normalized_title)
        alpha_ratio = alpha_count / max(len(normalized_title), 1)
        word_count = len(normalized_title.split())
        if alpha_ratio >= 0.65:
            score += 0.2
        else:
            reasons.append("low_semantic_confidence")
            score -= 0.15
        if 1 <= word_count <= 8:
            score += 0.1
        else:
            score -= 0.05
        if description:
            score += 0.1
        if len(description.split()) >= 6:
            score += 0.1

        section_key = self.heading_normalization_service.semantic_key(parsed_section.heading)
        title_key = self.heading_normalization_service.semantic_key(normalized_title)
        if title_key and section_key and title_key == section_key:
            score += 0.05

        seen_titles = seen_titles or set()
        if title_key and title_key in seen_titles:
            reasons.append("duplicate_candidate")
            score -= 0.2

        unique_reasons = tuple(dict.fromkeys(reason for reason in reasons if reason))
        if any(reason in unique_reasons for reason in ("date_like", "page_marker", "navigation_text", "generic_structure", "malformed_tokenization", "mostly_numeric")):
            decision = self.Decision.REJECTED
        elif "duplicate_candidate" in unique_reasons:
            decision = self.Decision.REJECTED
        elif "low_semantic_confidence" in unique_reasons and "insufficient_supporting_text" in unique_reasons:
            decision = self.Decision.MANUAL_REVIEW
        elif "insufficient_supporting_text" in unique_reasons:
            decision = self.Decision.ACCEPTED_WITH_WARNING
        else:
            decision = self.Decision.ACCEPTED

        return ConceptCandidateAssessment(
            normalized_title=normalized_title,
            confidence=round(max(0.0, min(score, 1.0)), 4),
            decision=decision,
            rejection_reasons=unique_reasons,
            metadata={
                "source_label": source_label,
                "normalized_heading": normalized_heading.normalized_heading,
                "semantic_title": normalized_heading.semantic_title,
                "structural_prefix": normalized_heading.structural_prefix,
                "heading_sequence_number": normalized_heading.sequence_number,
                "alphabetic_ratio": round(alpha_ratio, 4),
                "word_count": word_count,
                "supporting_text_length": len(description),
                "section_semantic_key": section_key,
                "title_semantic_key": title_key,
            },
        )
