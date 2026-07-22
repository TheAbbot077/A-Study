from apps.core.events import BusinessEvent


def mark_bridge_plans_stale(event: BusinessEvent) -> None:
    from .application.bridge_services import MarkBridgePlansStaleService
    from .bridge_models import BridgePlan

    graph_version_id = event.payload.get("graph_version_id")
    if not graph_version_id:
        return
    tenant_ids = BridgePlan.objects.filter(graph_version_id=graph_version_id).values_list("tenant_id", flat=True).distinct()
    for tenant_id in tenant_ids:
        MarkBridgePlansStaleService().execute(tenant_id=tenant_id, graph_version_id=graph_version_id, reason=event.event_name)


def supersede_prior_graph_bridge_plans(event: BusinessEvent) -> None:
    from .application.bridge_services import MarkBridgePlansStaleService
    from .bridge_models import BridgePlan

    graph_id = event.payload.get("graph_id")
    current_version_id = event.payload.get("graph_version_id")
    if not graph_id or not current_version_id:
        return
    rows = BridgePlan.objects.filter(graph_version__graph_id=graph_id).exclude(graph_version_id=current_version_id).values_list("tenant_id", "graph_version_id").distinct()
    for tenant_id, graph_version_id in rows:
        MarkBridgePlansStaleService().execute(tenant_id=tenant_id, graph_version_id=graph_version_id, reason="BRIDGE_GRAPH_SUPERSEDED")


def mark_diagnostic_bridge_plans_stale(event: BusinessEvent) -> None:
    from .application.bridge_services import MarkBridgePlansStaleService
    from .bridge_models import BridgePlan

    profile_id = event.payload.get("profile_id")
    if not profile_id:
        return
    tenant_ids = BridgePlan.objects.filter(run__diagnostic_profile_id=profile_id).values_list("tenant_id", flat=True).distinct()
    for tenant_id in tenant_ids:
        MarkBridgePlansStaleService().execute(tenant_id=tenant_id, diagnostic_profile_id=profile_id, reason="BRIDGE_DIAGNOSTIC_SUPERSEDED")


def mark_teaching_preparations_stale(event: BusinessEvent) -> None:
    from .application.teaching_services import MarkTeachingPreparationsStaleService
    from .teaching_models import TeachingPreparationManifest

    bridge_plan_id = event.payload.get("plan_id") or event.payload.get("bridge_plan_id")
    graph_version_id = event.payload.get("graph_version_id")
    coverage_evaluation_id = event.payload.get("coverage_evaluation_id")
    query = TeachingPreparationManifest.objects.all()
    if bridge_plan_id:
        query = query.filter(bridge_plan_id=bridge_plan_id)
    if graph_version_id:
        query = query.filter(graph_version_id=graph_version_id)
    if coverage_evaluation_id:
        query = query.filter(coverage_evaluation_id=coverage_evaluation_id)
    for tenant_id in query.values_list("tenant_id", flat=True).distinct():
        MarkTeachingPreparationsStaleService().execute(
            tenant_id=tenant_id,
            bridge_plan_id=bridge_plan_id,
            graph_version_id=graph_version_id,
            coverage_evaluation_id=coverage_evaluation_id,
            reason=event.event_name,
        )


def mark_teaching_sessions_stale(event: BusinessEvent) -> None:
    from .application.orchestration_services import MarkTeachingSessionsStaleService
    from .orchestration_models import SelfStudyTeachingSession

    bridge_plan_id = event.payload.get("plan_id") or event.payload.get("bridge_plan_id")
    preparation_manifest_id = event.payload.get("manifest_id") or event.payload.get("preparation_manifest_id")
    query = SelfStudyTeachingSession.objects.all()
    if bridge_plan_id:
        query = query.filter(bridge_plan_id=bridge_plan_id)
    if preparation_manifest_id:
        query = query.filter(preparation_manifest_id=preparation_manifest_id)
    for tenant_id in query.values_list("tenant_id", flat=True).distinct():
        MarkTeachingSessionsStaleService().execute(
            tenant_id=tenant_id,
            bridge_plan_id=bridge_plan_id,
            preparation_manifest_id=preparation_manifest_id,
            reason=event.event_name,
        )
