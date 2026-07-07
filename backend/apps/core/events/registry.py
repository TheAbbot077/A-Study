from .subscribers import EventSubscriber


class EventRegistry:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventSubscriber]] = {}

    def subscribe(self, event_name: str, subscriber: EventSubscriber) -> None:
        self._subscribers.setdefault(event_name, []).append(subscriber)

    def get_subscribers(self, event_name: str) -> list[EventSubscriber]:
        return list(self._subscribers.get(event_name, []))

    def clear(self) -> None:
        self._subscribers.clear()


default_event_registry = EventRegistry()

# Known platform and domain event names. Empty subscriber lists make event names
# discoverable even before asynchronous subscribers are attached.
for event_name in [
    "settings.user_setting_changed",
    "settings.user_setting_deleted",
    "settings.institution_setting_changed",
    "settings.institution_setting_deleted",
    "audit.entry_recorded",
    "academic.subject_created",
    "academic.subject_updated",
    "academic.subject_archived",
    "academic.curriculum_created",
    "academic.curriculum_updated",
    "academic.curriculum_archived",
    "academic.curriculum_unit_created",
    "academic.curriculum_unit_updated",
    "academic.curriculum_unit_archived",
    "academic.learning_resource_created",
    "academic.learning_resource_updated",
    "academic.learning_resource_activated",
    "academic.learning_resource_archived",
    "academic.content_section_created",
    "academic.content_section_updated",
    "academic.content_section_archived",
    "academic.content_concept_created",
    "academic.content_concept_updated",
    "academic.content_concept_archived",
    "academic.content_section_submitted_for_review",
    "academic.content_section_approved",
    "academic.content_section_rejected",
    "academic.content_section_quality_marked",
    "academic.content_concept_submitted_for_review",
    "academic.content_concept_approved",
    "academic.content_concept_rejected",
    "academic.content_concept_quality_marked",
    "academic.manual_section_created",
    "academic.manual_section_updated",
    "academic.manual_section_archived",
    "academic.manual_section_reordered",
    "academic.manual_concept_created",
    "academic.manual_concept_updated",
    "academic.manual_concept_archived",
    "academic.manual_concept_reordered",
    "academic.resource_ingestion_job_created",
    "academic.resource_ingestion_job_started",
    "academic.resource_ingestion_job_completed",
    "academic.resource_ingestion_job_failed",
    "academic.resource_ingestion_job_cancelled",
    "pedagogy.session_created",
    "pedagogy.session_started",
    "pedagogy.session_paused",
    "pedagogy.session_resumed",
    "pedagogy.session_completed",
    "pedagogy.session_abandoned",
    "pedagogy.message_added",
    "learning.context_assembled",
    "learning.grounding_package_created",
    "learning.grounding_validated",
    "learning.strategy_selected",
    "learning.strategy_validated",
    "learning.conversation_initialized",
    "learning.turn_added",
    "learning.window_trimmed",
    "learning.abbot_request_prepared",
    "learning.abbot_response_generated",
    "learning.abbot_response_validated",
    "learning.companion_registered",
    "learning.companion_activated",
    "learning.companion_deactivated",
    "learning.companion_response_generated",
]:
    default_event_registry._subscribers.setdefault(event_name, [])
