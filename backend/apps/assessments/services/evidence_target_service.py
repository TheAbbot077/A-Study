from __future__ import annotations

from dataclasses import dataclass

from apps.academic.domain.models import ContentConcept
from apps.assessments.domain.models import AssessmentEvaluation


@dataclass(frozen=True)
class ResolvedEvidenceTarget:
    target_type: str
    target_id: str
    target_title: str


class ResolveEvaluationEvidenceTargetService:
    def resolve(self, evaluation: AssessmentEvaluation) -> ResolvedEvidenceTarget | None:
        item = getattr(evaluation, "assessment_item", None) or getattr(getattr(evaluation, "response", None), "item", None)
        concept = getattr(getattr(evaluation, "response", None), "attempt", None)
        concept = getattr(getattr(concept, "assessment", None), "content_concept", None)
        if concept is None:
            return None
        metadata = getattr(item, "metadata", {}) or {}

        target_id = str(metadata.get("academic_target_id") or concept.id)
        target_title = str(metadata.get("academic_target_title") or getattr(concept, "title", ""))
        target_type = str(metadata.get("academic_target_type") or "CONTENT_CONCEPT")
        if not target_id:
            return None
        return ResolvedEvidenceTarget(target_type=target_type, target_id=target_id, target_title=target_title)
