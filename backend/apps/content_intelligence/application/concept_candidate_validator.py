from __future__ import annotations

from apps.content_intelligence.application.concept_candidate_scoring_service import ConceptCandidateScoringService
from apps.content_intelligence.domain.models import ParsedSection
from apps.content_intelligence.domain.services import ConceptCandidateAssessment


class ConceptCandidateValidator:
    def __init__(self, scoring_service: ConceptCandidateScoringService | None = None) -> None:
        self.scoring_service = scoring_service or ConceptCandidateScoringService()

    def validate(
        self,
        title: str,
        description: str,
        parsed_section: ParsedSection,
        *,
        seen_titles: set[str] | None = None,
        source_label: str = "body",
    ) -> ConceptCandidateAssessment:
        return self.scoring_service.assess(
            title=title,
            description=description,
            parsed_section=parsed_section,
            seen_titles=seen_titles,
            source_label=source_label,
        )
