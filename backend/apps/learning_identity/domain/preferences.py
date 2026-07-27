from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ValidationError

from .enums import LearnerPreferenceKey


@dataclass(frozen=True)
class PreferenceDefinition:
    key: str
    label: str
    allowed_values: tuple[Any, ...]
    mentor_context_eligible: bool
    teaching_context_eligible: bool
    sensitive: bool = False
    withdrawal_supported: bool = True


PREFERENCE_REGISTRY: dict[str, PreferenceDefinition] = {
    LearnerPreferenceKey.EXPLANATION_MODE: PreferenceDefinition(
        key=LearnerPreferenceKey.EXPLANATION_MODE,
        label="Explanation style",
        allowed_values=("step_by_step", "examples_first", "concise", "story_based"),
        mentor_context_eligible=True,
        teaching_context_eligible=True,
    ),
    LearnerPreferenceKey.TEACHING_PACE: PreferenceDefinition(
        key=LearnerPreferenceKey.TEACHING_PACE,
        label="Teaching pace",
        allowed_values=("gentle", "standard", "fast"),
        mentor_context_eligible=True,
        teaching_context_eligible=True,
    ),
    LearnerPreferenceKey.INTERFACE_LANGUAGE: PreferenceDefinition(
        key=LearnerPreferenceKey.INTERFACE_LANGUAGE,
        label="Interface language",
        allowed_values=("en", "st", "fr", "pt"),
        mentor_context_eligible=False,
        teaching_context_eligible=True,
    ),
    LearnerPreferenceKey.SESSION_LENGTH: PreferenceDefinition(
        key=LearnerPreferenceKey.SESSION_LENGTH,
        label="Preferred session length",
        allowed_values=(15, 25, 45, 60),
        mentor_context_eligible=True,
        teaching_context_eligible=True,
    ),
    LearnerPreferenceKey.REDUCED_MOTION: PreferenceDefinition(
        key=LearnerPreferenceKey.REDUCED_MOTION,
        label="Reduced motion",
        allowed_values=(True, False),
        mentor_context_eligible=False,
        teaching_context_eligible=False,
        sensitive=True,
    ),
    LearnerPreferenceKey.HIGH_CONTRAST: PreferenceDefinition(
        key=LearnerPreferenceKey.HIGH_CONTRAST,
        label="Higher contrast",
        allowed_values=(True, False),
        mentor_context_eligible=False,
        teaching_context_eligible=False,
        sensitive=True,
    ),
    LearnerPreferenceKey.LARGER_TEXT: PreferenceDefinition(
        key=LearnerPreferenceKey.LARGER_TEXT,
        label="Larger text",
        allowed_values=(True, False),
        mentor_context_eligible=False,
        teaching_context_eligible=False,
        sensitive=True,
    ),
    LearnerPreferenceKey.CAPTIONS: PreferenceDefinition(
        key=LearnerPreferenceKey.CAPTIONS,
        label="Captions",
        allowed_values=(True, False),
        mentor_context_eligible=False,
        teaching_context_eligible=True,
        sensitive=True,
    ),
}


def validate_preference_value(preference_key: str, value: Any) -> Any:
    definition = PREFERENCE_REGISTRY.get(preference_key)
    if definition is None:
        raise ValidationError("Unsupported learner preference.", code="UNSUPPORTED_PREFERENCE")
    if value not in definition.allowed_values:
        raise ValidationError("Unsupported learner preference value.", code="INVALID_PREFERENCE_VALUE")
    return value
