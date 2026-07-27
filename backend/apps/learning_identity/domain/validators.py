from __future__ import annotations

from datetime import date
import re
from typing import Any

from django.core.exceptions import ValidationError

from .enums import LearningAttributeType


MAX_WEEKLY_STUDY_MINUTES = 7 * 24 * 60
LANGUAGE_RE = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?$")
PROHIBITED_TRAIT_WORDS = {
    "ability level",
    "auditory learner",
    "disability inference",
    "intelligence",
    "learning style",
    "motivation score",
    "personality type",
    "risk ranking",
    "slow learner",
    "slow paced learner",
    "visual learner",
    "weak student",
}


def _string_value(value: Any, *, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Attribute value must be a non-empty string.", code=code)
    normalized = " ".join(value.strip().split())
    lowered = normalized.lower()
    if any(term in lowered for term in PROHIBITED_TRAIT_WORDS):
        raise ValidationError("Attribute value uses prohibited learner-trait language.", code="PROHIBITED_TRAIT_LANGUAGE")
    return normalized


def validate_attribute_value(attribute_type: str, value: Any) -> Any:
    if attribute_type == LearningAttributeType.PREFERRED_LEARNING_LANGUAGE:
        normalized = _string_value(value, code="LANGUAGE_REQUIRED")
        if not LANGUAGE_RE.match(normalized):
            raise ValidationError("Preferred learning language must be a normalized language code.", code="LANGUAGE_INVALID")
        return normalized

    if attribute_type == LearningAttributeType.TARGET_QUALIFICATION:
        return _string_value(value, code="TARGET_QUALIFICATION_REQUIRED")

    if attribute_type == LearningAttributeType.TARGET_EXAM_DATE:
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            try:
                date.fromisoformat(value)
            except ValueError as exc:
                raise ValidationError("Target exam date must be an ISO date.", code="TARGET_EXAM_DATE_INVALID") from exc
            return value
        raise ValidationError("Target exam date must be an ISO date.", code="TARGET_EXAM_DATE_INVALID")

    if attribute_type == LearningAttributeType.WEEKLY_STUDY_CAPACITY:
        if not isinstance(value, int):
            raise ValidationError("Weekly study capacity must be minutes per week.", code="WEEKLY_STUDY_CAPACITY_INVALID")
        if value <= 0:
            raise ValidationError("Weekly study capacity must be greater than zero.", code="WEEKLY_STUDY_CAPACITY_INVALID")
        if value > MAX_WEEKLY_STUDY_MINUTES:
            raise ValidationError("Weekly study capacity is outside the supported range.", code="WEEKLY_STUDY_CAPACITY_UNBOUNDED")
        return value

    if attribute_type in {
        LearningAttributeType.PRIOR_STUDY_EXPERIENCE,
        LearningAttributeType.ACCESSIBILITY_PREFERENCE,
        LearningAttributeType.STUDY_GOAL,
        LearningAttributeType.PREFERRED_EXPLANATION_FORMAT,
        LearningAttributeType.PACING_SUPPORT_PREFERENCE,
    }:
        return _string_value(value, code="DECLARED_ATTRIBUTE_REQUIRED")

    raise ValidationError("Unsupported learning identity attribute type.", code="ATTRIBUTE_TYPE_UNSUPPORTED")

