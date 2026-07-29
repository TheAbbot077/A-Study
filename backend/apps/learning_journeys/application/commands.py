from __future__ import annotations

from dataclasses import dataclass, field

from .services import CreateLearningJourneyService, LearningJourneyLifecycleService, SynchronizeLearningJourneyService


@dataclass(frozen=True)
class ExecuteLearningJourneyActionCommand:
    journey_id: str
    action_code: str
    actor_id: str
    idempotency_key: str = ""
    expected_journey_version: int | None = None
    payload: dict = field(default_factory=dict)
    request_context: dict = field(default_factory=dict)

__all__ = [
    "CreateLearningJourneyService",
    "ExecuteLearningJourneyActionCommand",
    "LearningJourneyLifecycleService",
    "SynchronizeLearningJourneyService",
]
