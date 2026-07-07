from __future__ import annotations

from typing import Any, Optional

from apps.academic.domain.models import ContentConcept
from apps.core.events import BusinessEvent, EventPublisher
from apps.learning.domain.models import (
    ContextConceptSnapshot,
    ContextCurriculumSnapshot,
    ContextLearnerSnapshot,
    ContextResourceSnapshot,
    ContextSectionSnapshot,
    PedagogicalContext,
    PedagogicalSession,
)
from apps.users.domain.models import User


class ContextAssemblyService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def assemble_for_session(self, session: PedagogicalSession) -> PedagogicalContext:
        context = self.assemble_for_concept(
            learner=session.learner,
            content_concept=session.content_concept,
            session_id=str(session.id),
        )
        return context

    def assemble_for_concept(
        self,
        learner: User,
        content_concept: ContentConcept,
        session_id: str | None = None,
    ) -> PedagogicalContext:
        learner_snapshot = ContextLearnerSnapshot(learner_id=self._object_id(learner))
        concept_snapshot = self._build_concept_snapshot(content_concept)
        context = PedagogicalContext(
            session_id=session_id,
            learner=learner_snapshot,
            concept=concept_snapshot,
            metadata={"source": "context_assembly_service"},
        )
        self._publish_context_assembled(context)
        return context

    def _build_concept_snapshot(self, content_concept: ContentConcept) -> ContextConceptSnapshot:
        content_section = getattr(content_concept, "content_section", None)
        return ContextConceptSnapshot(
            content_concept_id=self._object_id(content_concept),
            content_concept_title=getattr(content_concept, "title", ""),
            content_concept_description=getattr(content_concept, "description", ""),
            content_concept_learning_objective=getattr(content_concept, "learning_objective", ""),
            sequence_number=getattr(content_concept, "sequence_number", None),
            review_status=getattr(content_concept, "review_status", None),
            quality_status=getattr(content_concept, "quality_status", None),
            content_section=self._build_section_snapshot(content_section) if content_section is not None else None,
        )

    def _build_section_snapshot(self, content_section: Any) -> ContextSectionSnapshot:
        learning_resource = getattr(content_section, "learning_resource", None)
        return ContextSectionSnapshot(
            content_section_id=self._object_id(content_section),
            content_section_title=getattr(content_section, "title", ""),
            sequence_number=getattr(content_section, "sequence_number", None),
            review_status=getattr(content_section, "review_status", None),
            quality_status=getattr(content_section, "quality_status", None),
            learning_resource=self._build_resource_snapshot(learning_resource) if learning_resource is not None else None,
        )

    def _build_resource_snapshot(self, learning_resource: Any) -> ContextResourceSnapshot:
        subject = getattr(learning_resource, "subject", None)
        return ContextResourceSnapshot(
            learning_resource_id=self._object_id(learning_resource),
            learning_resource_title=getattr(learning_resource, "title", ""),
            resource_type=getattr(learning_resource, "resource_type", ""),
            subject_id=self._object_id_or_none(subject),
            subject_name=getattr(subject, "name", None) if subject is not None else None,
            curriculum=self._build_curriculum_snapshot(learning_resource),
        )

    def _build_curriculum_snapshot(self, learning_resource: Any) -> ContextCurriculumSnapshot:
        curriculum = getattr(learning_resource, "curriculum", None)
        curriculum_unit = getattr(learning_resource, "curriculum_unit", None)
        return ContextCurriculumSnapshot(
            curriculum_id=self._object_id_or_none(curriculum),
            curriculum_name=getattr(curriculum, "name", None) if curriculum is not None else None,
            curriculum_unit_id=self._object_id_or_none(curriculum_unit),
            curriculum_unit_title=getattr(curriculum_unit, "title", None) if curriculum_unit is not None else None,
            curriculum_unit_sequence_number=getattr(curriculum_unit, "sequence_number", None) if curriculum_unit is not None else None,
        )

    def _publish_context_assembled(self, context: PedagogicalContext) -> None:
        self.event_publisher.publish(
            BusinessEvent.create(
                "learning.context_assembled",
                payload={
                    "session_id": context.session_id,
                    "learner_id": context.learner.learner_id,
                    "content_concept_id": context.concept.content_concept_id,
                },
            )
        )

    def _object_id(self, value: Any) -> str:
        return str(getattr(value, "id"))

    def _object_id_or_none(self, value: Any | None) -> str | None:
        if value is None:
            return None
        return self._object_id(value)
