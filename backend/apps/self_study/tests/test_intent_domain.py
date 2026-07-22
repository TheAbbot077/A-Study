from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.self_study.models import IntentStatus, LearningMode, SelfStudyIntent


def intent(**changes):
    values = {
        "mode": LearningMode.SELF_STUDY,
        "goal_statement": "Learn calculus for engineering.",
        "preferred_language": "en",
        "policy_acknowledged_at": timezone.now(),
    }
    values.update(changes)
    return SelfStudyIntent(**values)


def test_minimum_valid_draft_can_become_ready():
    aggregate = intent()
    aggregate.mark_ready()
    assert aggregate.status == IntentStatus.READY
    assert aggregate.version == 2


@pytest.mark.parametrize(
    ("changes", "code"),
    [
        ({"goal_statement": " "}, "LEARNING_GOAL_REQUIRED"),
        ({"mode": ""}, "LEARNING_MODE_REQUIRED"),
        ({"preferred_language": ""}, "LANGUAGE_REQUIRED"),
        ({"policy_acknowledged_at": None}, "POLICY_ACKNOWLEDGEMENT_REQUIRED"),
    ],
)
def test_ready_returns_stable_blockers(changes, code):
    aggregate = intent(**changes)
    assert code in aggregate.readiness_blockers()
    with pytest.raises(ValidationError) as error:
        aggregate.mark_ready()
    assert error.value.error_list[0].code == code


def test_cancelled_intent_cannot_activate():
    aggregate = intent()
    aggregate.cancel()
    with pytest.raises(ValidationError) as error:
        aggregate.activate(object())
    assert error.value.code == "INVALID_INTENT_TRANSITION"


def test_cancellation_is_idempotent_and_preserves_history_fields():
    aggregate = intent(target_completion_date=date(2030, 1, 1))
    assert aggregate.cancel() is True
    version = aggregate.version
    assert aggregate.cancel() is False
    assert aggregate.version == version
    assert aggregate.target_completion_date == date(2030, 1, 1)
