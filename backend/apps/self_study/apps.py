from django.apps import AppConfig


class SelfStudyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.self_study"

    def ready(self):
        from apps.core.events import default_event_registry
        from .event_handlers import mark_bridge_plans_stale, mark_diagnostic_bridge_plans_stale, mark_teaching_preparations_stale, mark_teaching_sessions_stale, supersede_prior_graph_bridge_plans

        for event_name in ("curriculum_graph.invalidated", "self_study.curriculum_coverage.stale", "self_study.curriculum_coverage.invalidated"):
            default_event_registry.subscribe(event_name, mark_bridge_plans_stale)
        default_event_registry.subscribe("curriculum_graph.published", supersede_prior_graph_bridge_plans)
        default_event_registry.subscribe("self_study.diagnostic_placement_superseded", mark_diagnostic_bridge_plans_stale)
        for event_name in (
            "self_study.bridge_plan.stale",
            "self_study.bridge_plan.invalidated",
            "self_study.bridge_plan.superseded",
            "self_study.curriculum_coverage.stale",
            "self_study.curriculum_coverage.invalidated",
            "curriculum_graph.invalidated",
            "retrieval.resource_retired",
        ):
            default_event_registry.subscribe(event_name, mark_teaching_preparations_stale)
        for event_name in (
            "self_study.bridge_plan.stale",
            "self_study.bridge_plan.invalidated",
            "self_study.bridge_plan.superseded",
            "self_study.teaching_preparation.stale",
            "self_study.teaching_preparation.invalidated",
            "retrieval.resource_retired",
        ):
            default_event_registry.subscribe(event_name, mark_teaching_sessions_stale)
