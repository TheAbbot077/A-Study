from __future__ import annotations

import uuid
from collections import Counter

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher
from apps.audit.services.audit_service import AuditService

from ..bridge_models import (
    BridgeFindingSeverity, BridgePlan, BridgePlanDependency, BridgePlanFinding,
    BridgePlanNode, BridgePlanStatus, BridgePlanningRun, BridgePlanningRunStatus,
    BridgeRequirementType,
)
from ..diagnostic_models import DiagnosticPlacementProfile, ProfileStatus
from ..evidence_models import CoverageStatus, CurriculumCoverageEvaluation
from ..graph_models import CurriculumEdge, EdgeType, GraphStatus, GraphVersionStatus, RequirementType
from ..models import SelfStudyIntent
from ..domain.bridge_planning import (
    ALGORITHM_VERSION, APPLICABILITY_VERSION, APPROVAL_POLICY_VERSION, POLICY_VERSION,
    GraphPlanningError, calculate_prerequisite_closure, coverage_disposition,
    fingerprint, placement_disposition,
)
from .services import _has_institutional_authority


TARGET_NODE_TYPES = {"OUTCOME", "MODULE", "TOPIC", "CONCEPT", "COMPETENCY", "ASSESSMENT_OBJECTIVE"}


def _publish(name, payload):
    EventPublisher().publish(BusinessEvent.create(name, payload=payload))


def _after_commit(name, **payload):
    transaction.on_commit(lambda: _publish(name, {key: str(value) for key, value in payload.items()}))


def _audit_after_commit(*, actor, institution, action, plan, metadata):
    transaction.on_commit(lambda: AuditService().record_action(actor=actor, institution=institution, action=action, target_type="BridgePlan", target_id=str(plan.id), target_display=plan.plan_fingerprint, metadata=metadata))


def _govern(actor, tenant_id):
    if not (actor.is_superuser or _has_institutional_authority(actor, tenant_id)):
        raise PermissionDenied("BRIDGE_PLAN_GOVERNANCE_REQUIRED")


def _currentness(run):
    codes = []
    if run.graph_version.status != GraphVersionStatus.PUBLISHED or run.graph_version.graph.status != GraphStatus.PUBLISHED or run.graph_version.graph.current_version_id != run.graph_version_id:
        codes.append("BRIDGE_GRAPH_MISMATCH")
    if not run.diagnostic_profile or run.diagnostic_profile.status not in {ProfileStatus.FINAL, ProfileStatus.INCONCLUSIVE}:
        codes.append("BRIDGE_DIAGNOSTIC_MISSING_OR_STALE")
    if run.diagnostic_profile and run.diagnostic_profile.graph_version_id != run.graph_version_id:
        codes.append("BRIDGE_DIAGNOSTIC_MISMATCH")
    if not run.coverage_evaluation or run.coverage_evaluation.status != CoverageStatus.COMPLETED:
        codes.append("BRIDGE_COVERAGE_MISSING_OR_STALE")
    if run.coverage_evaluation and run.coverage_evaluation.graph_version_id != run.graph_version_id:
        codes.append("BRIDGE_COVERAGE_MISMATCH")
    if run.coverage_evaluation and run.input_manifest.get("gap_set_fingerprint") != run.coverage_evaluation.gap_set_fingerprint:
        codes.append("BRIDGE_GAP_SET_MISMATCH")
    return codes


class ResolveBridgeTargetsService:
    def execute(self, *, intent, graph_version, target_node_ids):
        identifiers = sorted({str(item) for item in target_node_ids})
        nodes = list(graph_version.nodes.filter(id__in=identifiers).order_by("ordinal", "stable_key"))
        if not identifiers or len(nodes) != len(identifiers):
            raise ValidationError("Target is not in the selected graph.", code="BRIDGE_TARGET_UNAUTHORIZED")
        for node in nodes:
            if node.node_type not in TARGET_NODE_TYPES or node.metadata.get("applicable") is False:
                raise ValidationError("Target is not authorized or applicable.", code="BRIDGE_TARGET_UNAUTHORIZED")
        if graph_version.graph.intent_id != intent.id:
            raise ValidationError("Target graph does not belong to the intent.", code="BRIDGE_GRAPH_MISMATCH")
        return nodes


class CreateBridgePlanningRunService:
    def execute(self, *, intent_id, target_node_ids, actor, idempotency_key=""):
        intent = SelfStudyIntent.objects.select_related("tenant", "effective_policy_snapshot").get(id=intent_id)
        if actor.id != intent.learner_id:
            _govern(actor, intent.tenant_id)
        graph = intent.curriculum_graphs.select_related("current_version", "selection_decision").filter(status=GraphStatus.PUBLISHED, current_version__status=GraphVersionStatus.PUBLISHED).order_by("-updated_at").first()
        if not graph:
            raise ValidationError("A current published graph is required.", code="BRIDGE_GRAPH_MISMATCH")
        graph_version = graph.current_version
        if not graph_version or graph_version.status != GraphVersionStatus.PUBLISHED:
            raise ValidationError("A current published graph is required.", code="BRIDGE_GRAPH_MISMATCH")
        targets = ResolveBridgeTargetsService().execute(intent=intent, graph_version=graph_version, target_node_ids=target_node_ids)
        profile = DiagnosticPlacementProfile.objects.filter(intent=intent, graph_version=graph_version, status__in=[ProfileStatus.FINAL, ProfileStatus.INCONCLUSIVE]).order_by("-created_at").first()
        coverage = CurriculumCoverageEvaluation.objects.filter(run__intent=intent, graph_version=graph_version, status=CoverageStatus.COMPLETED).order_by("-completed_at", "-created_at").first()
        target_manifest = [{"id": str(node.id), "stable_key": node.stable_key, "node_type": node.node_type, "ordinal": node.ordinal} for node in targets]
        manifest = {
            "tenant_id": str(intent.tenant_id), "intent_id": str(intent.id),
            "selection_decision_id": str(graph.selection_decision_id or ""),
            "graph_version_id": str(graph_version.id), "graph_fingerprint": graph_version.graph_fingerprint,
            "diagnostic_profile_id": str(profile.id) if profile else None,
            "diagnostic_fingerprint": profile.profile_fingerprint if profile else None,
            "coverage_evaluation_id": str(coverage.id) if coverage else None,
            "coverage_fingerprint": coverage.evaluation_fingerprint if coverage else None,
            "gap_set_fingerprint": coverage.gap_set_fingerprint if coverage else None,
            "target_set_fingerprint": fingerprint(target_manifest),
            "algorithm_version": ALGORITHM_VERSION, "policy_version": POLICY_VERSION,
            "approval_policy_version": APPROVAL_POLICY_VERSION, "applicability_version": APPLICABILITY_VERSION,
        }
        run_fingerprint = fingerprint(manifest)
        with transaction.atomic():
            existing = BridgePlanningRun.objects.filter(tenant=intent.tenant, run_fingerprint=run_fingerprint).exclude(status__in=[BridgePlanningRunStatus.INVALIDATED, BridgePlanningRunStatus.SUPERSEDED]).first()
            if existing:
                return existing, False
            run = BridgePlanningRun.objects.create(
                tenant=intent.tenant, intent=intent, selection_decision=graph.selection_decision,
                graph_version=graph_version, diagnostic_profile=profile, coverage_evaluation=coverage,
                target_manifest=target_manifest, input_manifest=manifest,
                algorithm_version=ALGORITHM_VERSION, policy_version=POLICY_VERSION,
                approval_policy_version=APPROVAL_POLICY_VERSION, applicability_version=APPLICABILITY_VERSION,
                run_fingerprint=run_fingerprint, requested_by=actor,
            )
            transaction.on_commit(lambda: __import__("apps.self_study.tasks", fromlist=["create_bridge_plan_task"]).create_bridge_plan_task.delay(str(run.id)))
            _after_commit("self_study.bridge_planning_run.created", run_id=run.id, tenant_id=run.tenant_id, intent_id=run.intent_id)
        return run, True


class CalculatePrerequisiteClosureService:
    def execute(self, run):
        nodes = list(run.graph_version.nodes.all().order_by("ordinal", "stable_key"))
        order = {str(node.id): node.ordinal for node in nodes}
        edges = list(run.graph_version.edges.filter(edge_type=EdgeType.REQUIRES).values("id", "source_node_id", "target_node_id", "requirement", "ordinal"))
        normalized = [{"id": row["id"], "source_id": row["source_node_id"], "target_id": row["target_node_id"], "requirement": row["requirement"], "ordinal": row["ordinal"]} for row in edges]
        return calculate_prerequisite_closure([row["id"] for row in run.target_manifest], normalized, order)


class ApplyDiagnosticEntryBoundaryService:
    def execute(self, run, node_ids):
        if not run.diagnostic_profile:
            return {node_id: None for node_id in node_ids}
        return {str(row.graph_node_id): row.classification for row in run.diagnostic_profile.classified_nodes.filter(graph_node_id__in=node_ids)}


class OverlayMaterialCoverageService:
    def execute(self, run, node_ids):
        if not run.coverage_evaluation:
            return {}
        return {str(row.graph_node_id): row for row in run.coverage_evaluation.node_results.filter(graph_node_id__in=node_ids)}


def _requirement(value):
    return {RequirementType.REQUIRED: BridgeRequirementType.MANDATORY, RequirementType.RECOMMENDED: BridgeRequirementType.CONDITIONAL, RequirementType.OPTIONAL: BridgeRequirementType.OPTIONAL}.get(value, BridgeRequirementType.MANDATORY)


class OrderBridgePlanService:
    def execute(self, run, closure, placements, coverage_rows):
        nodes = {str(node.id): node for node in run.graph_version.nodes.filter(id__in=closure.node_ids)}
        targets = {row["id"] for row in run.target_manifest}
        inbound = Counter(edge.dependent_id for edge in closure.edges)
        specs, findings = [], []
        currentness = _currentness(run)
        for code in currentness:
            findings.append((code, None, {}, True, BridgeFindingSeverity.BLOCKER))
        for node_id in closure.node_ids:
            node = nodes[node_id]
            edge_requirements = [_requirement(edge.requirement) for edge in closure.edges if edge.dependent_id == node_id or edge.prerequisite_id == node_id]
            requirement = BridgeRequirementType.MANDATORY if node_id in targets or BridgeRequirementType.MANDATORY in edge_requirements else (edge_requirements[0] if edge_requirements else BridgeRequirementType.MANDATORY)
            required = requirement == BridgeRequirementType.MANDATORY
            non_waivable = bool(node.metadata.get("non_waivable"))
            learner, rationale = placement_disposition(placements.get(node_id), target=node_id in targets, required=required, non_waivable=non_waivable)
            coverage = coverage_rows.get(node_id)
            state = coverage.state if coverage else "UNEVALUATED"
            feasibility, blocked, code = coverage_disposition(state, required=required, graph_applicable=node.metadata.get("applicable") is not False)
            if placements.get(node_id) in {"UNCERTAIN", "NOT_DIAGNOSABLE"}:
                findings.append(("BRIDGE_UNCERTAIN_PREREQUISITE", node_id, {"classification": placements[node_id]}, required, BridgeFindingSeverity.BLOCKER if required else BridgeFindingSeverity.WARNING))
            elif placements.get(node_id) is None and required:
                findings.append(("BRIDGE_UNASSESSED_PREREQUISITE", node_id, {}, True, BridgeFindingSeverity.BLOCKER))
            if non_waivable:
                findings.append(("BRIDGE_NON_WAIVABLE_PREREQUISITE", node_id, {}, False, BridgeFindingSeverity.INFO))
            if code and blocked:
                findings.append((code, node_id, {"coverage_state": state}, True, BridgeFindingSeverity.BLOCKER))
            spec = {
                "node": node, "layer": closure.layers[node_id], "learner": learner, "requirement": requirement,
                "rationale": rationale, "placement": placements.get(node_id) or "UNASSESSED", "coverage": coverage,
                "coverage_state": state, "feasibility": feasibility, "target": node_id in targets,
                "entry": learner == "ENTRY", "required": required, "blocked": int(blocked), "dependencies": inbound[node_id],
                "citations": ([coverage.citation_set_fingerprint] if coverage and coverage.citation_set_fingerprint else []),
            }
            specs.append(spec)
        if run.coverage_evaluation:
            for upstream in run.coverage_evaluation.findings.filter(Q(graph_node_id__in=closure.node_ids) | Q(graph_node__isnull=True)).order_by("code", "graph_node_id"):
                findings.append((upstream.code, str(upstream.graph_node_id) if upstream.graph_node_id else None, {"source": "PI-6F.5", "scope_type": upstream.scope_type, "scope_identifier": upstream.scope_identifier}, upstream.blocking, BridgeFindingSeverity.BLOCKER if upstream.blocking else BridgeFindingSeverity.WARNING))
        findings.append(("BRIDGE_APPROVAL_REQUIRED", None, {}, False, BridgeFindingSeverity.INFO))
        specs.sort(key=lambda item: (item["layer"], item["node"].ordinal, item["node"].stable_key))
        return specs, findings


class CreateBridgePlanService:
    def execute(self, run_id):
        with transaction.atomic():
            run = BridgePlanningRun.objects.select_for_update().select_related("graph_version__graph", "diagnostic_profile", "coverage_evaluation").get(id=run_id)
            if hasattr(run, "plan"):
                return run.plan
            if run.status != BridgePlanningRunStatus.PENDING:
                raise ValidationError("Run cannot be claimed.", code="BRIDGE_RUN_NOT_CLAIMABLE")
            run.status = BridgePlanningRunStatus.PLANNING; run.stage = "CLAIMED"; run.claim_token = uuid.uuid4(); run.claimed_at = timezone.now(); run.claimed_by = "self_study.create_bridge_plan"; run.version += 1; run.save()
        try:
            closure = CalculatePrerequisiteClosureService().execute(run)
            placements = ApplyDiagnosticEntryBoundaryService().execute(run, closure.node_ids)
            coverage = OverlayMaterialCoverageService().execute(run, closure.node_ids)
            specs, finding_specs = OrderBridgePlanService().execute(run, closure, placements, coverage)
        except GraphPlanningError as exc:
            return FailBridgePlanningRunService().execute(run.id, str(exc))
        with transaction.atomic():
            run = BridgePlanningRun.objects.select_for_update().get(id=run.id)
            target_fp = fingerprint(run.target_manifest)
            node_payload = [{"id": str(item["node"].id), "layer": item["layer"], "learner": item["learner"], "material": item["feasibility"]} for item in specs]
            dependency_payload = [edge.__dict__ for edge in closure.edges]
            blockers = sorted({(code, node_id or "") for code, node_id, _, blocking, _ in finding_specs if blocking})
            plan = BridgePlan.objects.create(
                run=run, tenant=run.tenant, intent=run.intent, graph_version=run.graph_version,
                target_set_snapshot=run.target_manifest, target_set_fingerprint=target_fp,
                node_set_fingerprint=fingerprint(node_payload), dependency_set_fingerprint=fingerprint(dependency_payload),
                blocker_set_fingerprint=fingerprint(blockers), plan_fingerprint=fingerprint({"run": run.run_fingerprint, "nodes": node_payload, "dependencies": dependency_payload, "blockers": blockers}),
                algorithm_version=run.algorithm_version, policy_version=run.policy_version, status=BridgePlanStatus.PROPOSED,
            )
            node_records = {}
            for item in specs:
                node = item["node"]
                payload = {"node": str(node.id), "learner": item["learner"], "material": item["feasibility"], "layer": item["layer"], "requirement": item["requirement"]}
                node_records[str(node.id)] = BridgePlanNode.objects.create(
                    plan=plan, graph_node=node, node_type=node.node_type, ordinal=node.ordinal, topological_layer=item["layer"],
                    learner_disposition=item["learner"], requirement_type=item["requirement"], inclusion_rationale=item["rationale"],
                    placement_band=item["placement"], coverage=item["coverage"], coverage_state=item["coverage_state"],
                    material_feasibility=item["feasibility"], is_target=item["target"], is_entry=item["entry"], is_required=item["required"],
                    blocker_count=item["blocked"], dependency_count=item["dependencies"], coverage_citations=item["citations"], fingerprint=fingerprint(payload),
                )
            graph_edges = {str(edge.id): edge for edge in CurriculumEdge.objects.filter(id__in=[item.edge_id for item in closure.edges])}
            for edge in closure.edges:
                BridgePlanDependency.objects.create(
                    plan=plan, predecessor_node=node_records[edge.prerequisite_id], successor_node=node_records[edge.dependent_id], graph_edge=graph_edges[edge.edge_id],
                    edge_type=graph_edges[edge.edge_id].edge_type, requirement_type=_requirement(edge.requirement), affects_ordering=True,
                    rationale=["AUTHORITATIVE_GRAPH_EDGE"], fingerprint=fingerprint(edge.__dict__),
                )
            for code, node_id, details, blocking, severity in sorted(finding_specs, key=lambda item: (item[0], item[1] or "")):
                BridgePlanFinding.objects.create(plan=plan, code=code, severity=severity, blocking=blocking, scope="NODE" if node_id else "PLAN", affected_identities=[node_id] if node_id else [], details=details, algorithm_version=run.algorithm_version, policy_version=run.policy_version)
            run.stage = "PLAN_PERSISTED"; run.save(update_fields=["stage", "updated_at"])
            transaction.on_commit(lambda: __import__("apps.self_study.tasks", fromlist=["finalize_bridge_plan_task"]).finalize_bridge_plan_task.delay(str(run.id)))
        return plan


class FinalizeBridgePlanService:
    def execute(self, run_id):
        with transaction.atomic():
            run = BridgePlanningRun.objects.select_for_update().select_related("plan").get(id=run_id)
            plan = run.plan
            if run.status == BridgePlanningRunStatus.PLAN_READY:
                return plan
            blocked = plan.findings.filter(blocking=True).exists()
            plan.status = BridgePlanStatus.BLOCKED if blocked else BridgePlanStatus.READY_FOR_REVIEW; plan.version += 1; plan.save(update_fields=["status", "version"])
            run.status = BridgePlanningRunStatus.PLAN_READY; run.stage = "FINALIZED"; run.completed_at = timezone.now(); run.version += 1; run.save()
            _after_commit("self_study.bridge_plan.generated", plan_id=plan.id, run_id=run.id, tenant_id=run.tenant_id)
            if blocked:
                _after_commit("self_study.bridge_plan.blocked", plan_id=plan.id, run_id=run.id, tenant_id=run.tenant_id)
            return plan


class FailBridgePlanningRunService:
    def execute(self, run_id, code, detail=""):
        with transaction.atomic():
            run = BridgePlanningRun.objects.select_for_update().get(id=run_id)
            if run.status in {BridgePlanningRunStatus.PLAN_READY, BridgePlanningRunStatus.INVALIDATED, BridgePlanningRunStatus.SUPERSEDED}:
                return run
            run.status = BridgePlanningRunStatus.FAILED; run.stage = "FAILED"; run.failure_code = code; run.failure_detail = detail[:500]; run.completed_at = timezone.now(); run.version += 1; run.save()
            _after_commit("self_study.bridge_plan.failed", run_id=run.id, tenant_id=run.tenant_id)
            return run


class MarkBridgePlansStaleService:
    """Application hook for PI-6F.3/4/5 supersession and policy changes."""
    def execute(self, *, tenant_id, reason, graph_version_id=None, diagnostic_profile_id=None, coverage_evaluation_id=None):
        filters = {"tenant_id": tenant_id}
        if graph_version_id: filters["graph_version_id"] = graph_version_id
        if diagnostic_profile_id: filters["run__diagnostic_profile_id"] = diagnostic_profile_id
        if coverage_evaluation_id: filters["run__coverage_evaluation_id"] = coverage_evaluation_id
        with transaction.atomic():
            plans = list(BridgePlan.objects.select_for_update().filter(**filters).exclude(status__in=[BridgePlanStatus.INVALIDATED, BridgePlanStatus.SUPERSEDED, BridgePlanStatus.REJECTED, BridgePlanStatus.STALE]))
            for plan in plans:
                plan.status = BridgePlanStatus.STALE; plan.version += 1; plan.save(update_fields=["status", "version"])
                run = plan.run; run.status = BridgePlanningRunStatus.STALE; run.failure_code = reason; run.version += 1; run.save()
                _after_commit("self_study.bridge_plan.stale", plan_id=plan.id, tenant_id=plan.tenant_id, reason=reason)
            return plans


class ApproveBridgePlanService:
    def execute(self, plan_id, actor, reason, expected_version):
        with transaction.atomic():
            plan = BridgePlan.objects.select_for_update().select_related("run__graph_version__graph").get(id=plan_id)
            _govern(actor, plan.tenant_id)
            if plan.version != expected_version: raise ValidationError("Plan version changed.", code="BRIDGE_PLAN_VERSION_CONFLICT")
            stale = _currentness(plan.run)
            if stale: raise ValidationError(stale[0], code=stale[0])
            if plan.status not in {BridgePlanStatus.READY_FOR_REVIEW, BridgePlanStatus.BLOCKED}: raise ValidationError("Plan is not reviewable.", code="BRIDGE_PLAN_NOT_REVIEWABLE")
            plan.approved_by = actor; plan.approved_at = timezone.now(); plan.approval_reason = reason; plan.version += 1
            if plan.status != BridgePlanStatus.BLOCKED: plan.status = BridgePlanStatus.APPROVED
            plan.save(); _audit_after_commit(actor=actor, institution=plan.tenant, action="self_study.bridge_plan.approved", plan=plan, metadata={"reason": reason, "version": plan.version}); _after_commit("self_study.bridge_plan.approved", plan_id=plan.id, tenant_id=plan.tenant_id)
            return plan


class RejectBridgePlanService:
    def execute(self, plan_id, actor, reason, expected_version):
        with transaction.atomic():
            plan = BridgePlan.objects.select_for_update().get(id=plan_id); _govern(actor, plan.tenant_id)
            if plan.version != expected_version: raise ValidationError("Plan version changed.", code="BRIDGE_PLAN_VERSION_CONFLICT")
            if plan.status not in {BridgePlanStatus.READY_FOR_REVIEW, BridgePlanStatus.BLOCKED}: raise ValidationError("Plan is not reviewable.", code="BRIDGE_PLAN_NOT_REVIEWABLE")
            plan.status = BridgePlanStatus.REJECTED; plan.rejected_by = actor; plan.rejected_at = timezone.now(); plan.rejection_reason = reason; plan.version += 1; plan.save()
            _audit_after_commit(actor=actor, institution=plan.tenant, action="self_study.bridge_plan.rejected", plan=plan, metadata={"reason": reason, "version": plan.version})
            _after_commit("self_study.bridge_plan.rejected", plan_id=plan.id, tenant_id=plan.tenant_id); return plan


class ActivateBridgePlanService:
    def execute(self, plan_id, actor, expected_version):
        with transaction.atomic():
            plan = BridgePlan.objects.select_for_update().select_related("run").get(id=plan_id); _govern(actor, plan.tenant_id)
            if plan.version != expected_version: raise ValidationError("Plan version changed.", code="BRIDGE_PLAN_VERSION_CONFLICT")
            if plan.status != BridgePlanStatus.APPROVED or plan.findings.filter(blocking=True).exists(): raise ValidationError("Only an approved unblocked plan can be activated.", code="BRIDGE_PLAN_BLOCKED")
            stale = _currentness(plan.run)
            if stale: raise ValidationError(stale[0], code=stale[0])
            previous = BridgePlan.objects.select_for_update().filter(tenant=plan.tenant, intent=plan.intent, target_set_fingerprint=plan.target_set_fingerprint, status=BridgePlanStatus.ACTIVE).exclude(id=plan.id).first()
            if previous:
                previous.status = BridgePlanStatus.SUPERSEDED; previous.version += 1; previous.save(update_fields=["status", "version"])
                _after_commit("self_study.bridge_plan.superseded", plan_id=previous.id, successor_id=plan.id, tenant_id=plan.tenant_id)
            plan.status = BridgePlanStatus.ACTIVE; plan.activated_by = actor; plan.activated_at = timezone.now(); plan.version += 1; plan.save()
            _audit_after_commit(actor=actor, institution=plan.tenant, action="self_study.bridge_plan.activated", plan=plan, metadata={"version": plan.version})
            _after_commit("self_study.bridge_plan.activated", plan_id=plan.id, tenant_id=plan.tenant_id); return plan


class InvalidateBridgePlanService:
    def execute(self, plan_id, actor, expected_version, reason="BRIDGE_PLAN_INVALIDATED"):
        with transaction.atomic():
            plan = BridgePlan.objects.select_for_update().get(id=plan_id); _govern(actor, plan.tenant_id)
            if plan.version != expected_version: raise ValidationError("Plan version changed.", code="BRIDGE_PLAN_VERSION_CONFLICT")
            plan.status = BridgePlanStatus.INVALIDATED; plan.version += 1; plan.save(update_fields=["status", "version"])
            run = plan.run; run.status = BridgePlanningRunStatus.INVALIDATED; run.failure_code = reason; run.version += 1; run.save()
            _audit_after_commit(actor=actor, institution=plan.tenant, action="self_study.bridge_plan.invalidated", plan=plan, metadata={"reason": reason, "version": plan.version})
            _after_commit("self_study.bridge_plan.invalidated", plan_id=plan.id, tenant_id=plan.tenant_id); return plan


class RecalculateBridgePlanService:
    def execute(self, plan_id, actor, expected_version):
        plan = BridgePlan.objects.select_related("run").get(id=plan_id); _govern(actor, plan.tenant_id)
        if plan.version != expected_version: raise ValidationError("Plan version changed.", code="BRIDGE_PLAN_VERSION_CONFLICT")
        return CreateBridgePlanningRunService().execute(intent_id=plan.intent_id, target_node_ids=[item["id"] for item in plan.target_set_snapshot], actor=actor)


class GetCurrentBridgePlanService:
    def execute(self, intent_id, actor, target_set_fingerprint=None):
        intent = SelfStudyIntent.objects.get(id=intent_id)
        if actor.id != intent.learner_id: _govern(actor, intent.tenant_id)
        query = BridgePlan.objects.filter(intent=intent, status=BridgePlanStatus.ACTIVE).select_related("run", "graph_version")
        if target_set_fingerprint:
            query = query.filter(target_set_fingerprint=target_set_fingerprint)
        plans = list(query[:2])
        if len(plans) > 1:
            raise ValidationError("Target scope is required.", code="BRIDGE_ACTIVE_PLAN_CONFLICT")
        return plans[0] if plans else None


class GetBridgePlanHandoffService:
    def execute(self, intent_id, actor, target_set_fingerprint=None):
        plan = GetCurrentBridgePlanService().execute(intent_id, actor, target_set_fingerprint)
        if not plan: raise ValidationError("No active bridge plan.", code="BRIDGE_PLAN_NOT_ACTIVE")
        stale = _currentness(plan.run)
        if stale or plan.findings.filter(blocking=True).exists(): raise ValidationError((stale or ["BRIDGE_PLAN_BLOCKED"])[0], code=(stale or ["BRIDGE_PLAN_BLOCKED"])[0])
        nodes = plan.nodes.select_related("graph_node").order_by("topological_layer", "ordinal", "graph_node__stable_key")
        dependencies = plan.dependencies.order_by("predecessor_node__topological_layer", "graph_edge__ordinal", "graph_edge_id")
        return {
            "plan_id": str(plan.id), "plan_fingerprint": plan.plan_fingerprint, "graph_version_id": str(plan.graph_version_id), "graph_fingerprint": plan.graph_version.graph_fingerprint,
            "diagnostic_fingerprint": plan.run.input_manifest.get("diagnostic_fingerprint"), "coverage_fingerprint": plan.run.input_manifest.get("coverage_fingerprint"), "gap_set_fingerprint": plan.run.input_manifest.get("gap_set_fingerprint"),
            "targets": plan.target_set_snapshot, "algorithm_version": plan.algorithm_version, "policy_version": plan.policy_version,
            "nodes": [{"id": str(row.graph_node_id), "stable_key": row.graph_node.stable_key, "ordinal": row.ordinal, "topological_layer": row.topological_layer, "learner_disposition": row.learner_disposition, "material_feasibility": row.material_feasibility, "coverage_citations": row.coverage_citations} for row in nodes],
            "dependencies": [{"predecessor_node_id": str(row.predecessor_node.graph_node_id), "successor_node_id": str(row.successor_node.graph_node_id), "graph_edge_id": str(row.graph_edge_id), "requirement_type": row.requirement_type} for row in dependencies],
            "blockers": [],
        }
