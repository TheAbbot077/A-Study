from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Callable

from django.core.exceptions import ValidationError

from .enums import (
    AttributeVisibility,
    DeclarationChangeType,
    DeclarationFieldStatus,
    LearningAttributeType,
    OnboardingDeclarationDisposition,
)
from .validators import validate_attribute_value


Normalizer = Callable[[Any], Any]


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        raise ValidationError("Declaration value must be text.", code="VALUE_NORMALIZATION_FAILED")
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise ValidationError("Declaration value is required.", code="INVALID_ATTRIBUTE_VALUE")
    if len(normalized) > 255:
        raise ValidationError("Declaration value is too long.", code="INVALID_ATTRIBUTE_VALUE")
    return normalized


def normalize_date(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        try:
            return date.fromisoformat(value).isoformat()
        except ValueError as exc:
            raise ValidationError("Declaration date must be ISO formatted.", code="VALUE_NORMALIZATION_FAILED") from exc
    raise ValidationError("Declaration date must be explicit.", code="VALUE_NORMALIZATION_FAILED")


def normalize_minutes(value: Any) -> int:
    if isinstance(value, bool):
        raise ValidationError("Weekly capacity must be minutes per week.", code="VALUE_NORMALIZATION_FAILED")
    if isinstance(value, int):
        minutes = value
    elif isinstance(value, str) and value.strip().isdigit():
        minutes = int(value.strip())
    else:
        raise ValidationError("Weekly capacity must be minutes per week.", code="VALUE_NORMALIZATION_FAILED")
    return validate_attribute_value(LearningAttributeType.WEEKLY_STUDY_CAPACITY, minutes)


def semantic_equal(left: Any, right: Any, *, normalizer: Normalizer) -> bool:
    try:
        return normalizer(left) == normalizer(right)
    except ValidationError:
        return left == right


@dataclass(frozen=True)
class OnboardingDeclarationMapping:
    source_field: str
    target_attribute_type: str
    supported_source_schema_versions: tuple[int, ...]
    normalizer: Normalizer
    default_visibility: str = AttributeVisibility.LEARNER_VISIBLE
    restricted: bool = False
    clearing_allowed: bool = True
    safe_source_label: str = "Declared during conversational onboarding"

    def normalize(self, value: Any) -> Any:
        normalized = self.normalizer(value)
        return validate_attribute_value(self.target_attribute_type, normalized)

    def equivalent(self, left: Any, right: Any) -> bool:
        return semantic_equal(left, right, normalizer=self.normalize)


@dataclass(frozen=True)
class DeclarationChange:
    source_field: str
    attribute_type: str
    change_type: str
    status: str
    reason_codes: tuple[str, ...] = ()
    current_value_present: bool = False
    incoming_value_present: bool = False
    visibility: str = AttributeVisibility.LEARNER_VISIBLE
    restricted: bool = False
    normalized_value: Any = None

    def safe_dict(self) -> dict[str, Any]:
        return {
            "source_field": self.source_field,
            "attribute_type": self.attribute_type,
            "change_type": self.change_type,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "current_value_present": self.current_value_present,
            "incoming_value_present": self.incoming_value_present,
            "visibility": self.visibility,
            "restricted": self.restricted,
        }


class OnboardingDeclarationMappingRegistry:
    def __init__(self):
        self._mappings: dict[str, OnboardingDeclarationMapping] = {}

    def register(self, mapping: OnboardingDeclarationMapping) -> None:
        if mapping.source_field in self._mappings:
            raise ValidationError("Onboarding declaration mapping already registered.", code="DECLARATION_MAPPING_DUPLICATE")
        self._mappings[mapping.source_field] = mapping

    def get(self, source_field: str) -> OnboardingDeclarationMapping:
        try:
            return self._mappings[source_field]
        except KeyError as exc:
            raise ValidationError("Unsupported onboarding declaration field.", code="UNSUPPORTED_ONBOARDING_FIELD") from exc

    def all(self) -> tuple[OnboardingDeclarationMapping, ...]:
        return tuple(self._mappings[field] for field in sorted(self._mappings))


ELIGIBLE_DISPOSITIONS = {
    OnboardingDeclarationDisposition.EXPLICITLY_DECLARED,
    OnboardingDeclarationDisposition.EXPLICITLY_CONFIRMED,
}


def build_default_onboarding_declaration_mapping_registry() -> OnboardingDeclarationMappingRegistry:
    registry = OnboardingDeclarationMappingRegistry()
    registry.register(
        OnboardingDeclarationMapping(
            source_field="topic_query",
            target_attribute_type=LearningAttributeType.STUDY_GOAL,
            supported_source_schema_versions=(1,),
            normalizer=normalize_text,
        )
    )
    registry.register(
        OnboardingDeclarationMapping(
            source_field="qualification_query",
            target_attribute_type=LearningAttributeType.TARGET_QUALIFICATION,
            supported_source_schema_versions=(1,),
            normalizer=normalize_text,
        )
    )
    registry.register(
        OnboardingDeclarationMapping(
            source_field="target_date",
            target_attribute_type=LearningAttributeType.TARGET_EXAM_DATE,
            supported_source_schema_versions=(1,),
            normalizer=normalize_date,
        )
    )
    registry.register(
        OnboardingDeclarationMapping(
            source_field="weekly_study_minutes",
            target_attribute_type=LearningAttributeType.WEEKLY_STUDY_CAPACITY,
            supported_source_schema_versions=(1,),
            normalizer=normalize_minutes,
        )
    )
    return registry


def rejected_change(source_field: str, reason_code: str) -> DeclarationChange:
    return DeclarationChange(
        source_field=source_field,
        attribute_type="",
        change_type=DeclarationChangeType.REJECTED,
        status=DeclarationFieldStatus.REJECTED,
        reason_codes=(reason_code,),
    )
