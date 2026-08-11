from django.apps import AppConfig


class LearningJourneysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.learning_journeys"
    verbose_name = "Learning Journeys"

    def ready(self):
        from apps.core.events.registry import default_event_registry

        for event_name in [
            "learning_journey.created",
            "learning_journey.progressed",
            "study_lab.artefact.created",
            "study_lab.scaffold_generation.completed",
            "ariel.knowledge.created",
        ]:
            default_event_registry._subscribers.setdefault(event_name, [])
