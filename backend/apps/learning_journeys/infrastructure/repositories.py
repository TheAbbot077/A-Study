from __future__ import annotations

from apps.learning_journeys.domain.models import LearningJourney, LearningJourneySourceBinding


class LearningJourneyRepository:
    def get(self, journey_id) -> LearningJourney:
        return LearningJourney.objects.get(id=journey_id)

    def source_binding_for(self, *, source_type: str, source_id):
        return LearningJourneySourceBinding.objects.select_related("journey").filter(
            source_type=source_type,
            source_id=source_id,
        ).first()
