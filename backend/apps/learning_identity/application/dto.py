from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LearnerSafeAttributeSummary:
    attribute_type: str
    learner_label: str
    learner_safe_value: str
    classification: str
    source_summary: str
    validity_summary: str
    review_required: bool


@dataclass(frozen=True)
class LearnerSafeProfileSummary:
    profile_id: str
    status: str
    current_version_number: int | None
    last_updated_at: str
    attributes: list[LearnerSafeAttributeSummary]

