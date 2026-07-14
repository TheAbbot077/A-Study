from __future__ import annotations

from apps.content_intelligence.domain.models import ContentExtractionResult, ParsedConceptCandidate, ParsedSection


class ConfidenceScoringService:
    def score_extraction_quality(self, result: ContentExtractionResult) -> float:
        if result.char_count == 0:
            return 0.0
        score = 0.5
        if result.sufficient_text:
            score += 0.25
        if not result.ocr_used:
            score += 0.15
        if result.page_count:
            score += 0.1
        return round(min(score, 1.0), 4)

    def score_section_confidence(self, sections: list[ParsedSection]) -> float:
        if not sections:
            return 0.0
        return round(sum(self._numeric_confidence(getattr(section, "confidence", None), default=0.75) for section in sections) / len(sections), 4)

    def score_concept_confidence(self, concepts: list[ParsedConceptCandidate]) -> float:
        if not concepts:
            return 0.0
        return round(sum(self._numeric_confidence(getattr(concept, "confidence", None), default=0.75) for concept in concepts) / len(concepts), 4)

    def score_structural_consistency(self, sections: list[ParsedSection]) -> float:
        if not sections:
            return 0.0
        headings = [section.heading.strip().lower() for section in sections]
        unique_ratio = len(set(headings)) / len(headings)
        return round(min(1.0, max(0.3, unique_ratio)), 4)

    def _numeric_confidence(self, value, default: float) -> float:
        return float(value) if isinstance(value, (int, float)) else default
