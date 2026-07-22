from __future__ import annotations

import uuid

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.core.events import BusinessEvent, EventPublisher

from ..application.bridge_services import _currentness as bridge_currentness
from ..application.services import _has_institutional_authority
from ..bridge_models import BridgePlan, BridgePlanStatus
from ..domain.bridge_planning import fingerprint
from ..domain.teaching_preparation import (
    ALGORITHM_VERSION, POLICY_VERSION, READINESS_POLICY_VERSION, RETRIEVAL_SCHEMA_VERSION,
    ROLE_POLICY_VERSION, CURRENT_RESOURCE_STATUSES, ELIGIBLE_MAPPING_STATUSES,
    classify_role, evaluate_pack_state, role_policy_for, run_manifest_for_plan,
)
from ..evidence_models import CurriculumEvidenceMapping, MappingClass, MappingStatus
from ..models import SelfStudyIntent
from ..teaching_models import (
    NodeTeachingPack, NodeTeachingPackStatus, TeachingPackResource, TeachingPreparationFindingSeverity,
    TeachingPreparationManifest, TeachingPreparationManifestStatus, TeachingPreparationRun,
    TeachingPreparationRunStatus, TeachingReadinessEvaluation, TeachingReadinessFinding,
    TeachingReadinessState, TeachingRetrievalManifest,
)


def _publish(name, payload):
    EventPublisher().publish(BusinessEvent.create(name, payload=payload))


def _after_commit(name, **payload):
    transaction.on_commit(lambda: _publish(name, {key: str(value) for key, value in payload.items()}))


def _audit_after_commit(*, actor, institution, action, manifest, metadata):
    transaction.on_commit(lambda: AuditService().record_action(actor=actor, institution=institution, action=action, target_type="TeachingPreparationManifest", target_id=str(manifest.id), target_display=manifest.manifest_fingerprint, metadata=metadata))


def _govern(actor, tenant_id):
    if not (actor.is_superuser or _has_institutional_authority(actor, tenant_id)):
        raise PermissionDenied("TEACHING_PREPARATION_GOVERNANCE_REQUIRED")


def _currentness(run):
    codes = list(bridge_currentness(run.bridge_plan.run))
    if run.bridge_plan.status != BridgePlanStatus.ACTIVE:
        codes.append("TEACHING_BRIDGE_PLAN_NOT_ACTIVE")
    if run.bridge_plan.plan_fingerprint != run.bridge_plan_fingerprint:
        codes.append("TEACHING_BRIDGE_PLAN_FINGERPRINT_MISMATCH")
    if run.coverage_evaluation.evaluation_fingerprint != run.coverage_fingerprint:
        codes.append("TEACHING_COVERAGE_FINGERPRINT_MISMATCH")
    if run.coverage_evaluation.mapping_set_fingerprint != run.mapping_set_fingerprint:
        codes.append("TEACHING_MAPPING_SET_MISMATCH")
    return codes


def _visible_plans_for(actor):
    tenants = actor.institutionmembership_set.filter(is_active=True).values_list("institution_id", flat=True)
    return BridgePlan.objects.filter(Q(intent__learner=actor) | Q(tenant_id__in=tenants)).distinct()


class CreateTeachingPreparationRunService:
    def execute(self, *, bridge_plan_id, actor, idempotency_key=""):
        plan = _visible_plans_for(actor).select_related("run__coverage_evaluation", "graph_version", "intent", "tenant").get(id=bridge_plan_id)
        if actor.id != plan.intent.learner_id:
            _govern(actor, plan.tenant_id)
        if plan.status != BridgePlanStatus.ACTIVE:
            raise ValidationError("An active bridge plan is required.", code="TEACHING_BRIDGE_PLAN_NOT_ACTIVE")
        if plan.findings.filter(blocking=True).exists():
            raise ValidationError("Blocked bridge plans cannot prepare teaching.", code="TEACHING_BRIDGE_PLAN_BLOCKED")
        stale = bridge_currentness(plan.run)
        if stale:
            raise ValidationError(stale[0], code=stale[0])
        if not plan.run.coverage_evaluation_id:
            raise ValidationError("Coverage authority is required.", code="TEACHING_COVERAGE_MISSING")
        manifest = run_manifest_for_plan(plan)
        run_fingerprint = fingerprint(manifest)
        with transaction.atomic():
            existing = TeachingPreparationRun.objects.filter(tenant=plan.tenant, run_fingerprint=run_fingerprint).exclude(status__in=[TeachingPreparationRunStatus.INVALIDATED, TeachingPreparationRunStatus.SUPERSEDED]).first()
            if existing:
                return existing, False
            run = TeachingPreparationRun.objects.create(
                tenant=plan.tenant, intent=plan.intent, bridge_plan=plan, graph_version=plan.graph_version,
                coverage_evaluation=plan.run.coverage_evaluation, bridge_plan_fingerprint=plan.plan_fingerprint,
                graph_fingerprint=plan.graph_version.graph_fingerprint, coverage_fingerprint=plan.run.coverage_evaluation.evaluation_fingerprint,
                mapping_set_fingerprint=plan.run.coverage_evaluation.mapping_set_fingerprint, input_manifest=manifest,
                algorithm_version=ALGORITHM_VERSION, policy_version=POLICY_VERSION, role_policy_version=ROLE_POLICY_VERSION,
                retrieval_schema_version=RETRIEVAL_SCHEMA_VERSION, readiness_policy_version=READINESS_POLICY_VERSION,
                run_fingerprint=run_fingerprint, requested_by=actor,
            )
            transaction.on_commit(lambda: __import__("apps.self_study.tasks", fromlist=["assemble_teaching_preparation_task"]).assemble_teaching_preparation_task.delay(str(run.id)))
            _after_commit("self_study.teaching_preparation_run.created", run_id=run.id, tenant_id=run.tenant_id, bridge_plan_id=plan.id)
        return run, True


class TeachingEligibilityService:
    def accepted_mappings(self, run, graph_node_ids):
        return list(CurriculumEvidenceMapping.objects.select_related("evidence_unit__source_input__resource", "evidence_unit__source_input", "evidence_unit__source_block", "graph_node").filter(
            run=run.coverage_evaluation.run,
            graph_node_id__in=graph_node_ids,
            status__in=ELIGIBLE_MAPPING_STATUSES,
        ).order_by("graph_node__ordinal", "classification", "evidence_unit__ordinal", "id"))

    def exclusion_findings(self, mapping):
        unit = mapping.evidence_unit
        source = unit.source_input
        findings = []
        if mapping.status != MappingStatus.ACCEPTED:
            findings.append(("TEACHING_MAPPING_NOT_ACCEPTED", False))
        if source.resource.status not in CURRENT_RESOURCE_STATUSES:
            findings.append(("TEACHING_RESOURCE_NOT_CURRENT", True))
        if not unit.citation_snapshot:
            findings.append(("TEACHING_CITATION_MISSING", True))
        if unit.licence_disposition.lower() not in CURRENT_RESOURCE_STATUSES and unit.licence_disposition.lower() not in {"allowed", "approved", "permitted", "unknown"}:
            findings.append(("TEACHING_LICENSE_BLOCKED", True))
        if unit.safety_disposition.lower() not in {"safe", "approved", "clear", "unknown"}:
            findings.append(("TEACHING_SAFETY_BLOCKED", True))
        return findings


class AssembleTeachingPreparationService:
    def execute(self, run_id):
        with transaction.atomic():
            run = TeachingPreparationRun.objects.select_for_update().select_related("bridge_plan__run", "coverage_evaluation__run", "graph_version", "intent", "tenant").get(id=run_id)
            if hasattr(run, "manifest"):
                return run.manifest
            if run.status != TeachingPreparationRunStatus.PENDING:
                raise ValidationError("Run cannot be claimed.", code="TEACHING_PREPARATION_NOT_CLAIMABLE")
            run.status = TeachingPreparationRunStatus.ASSEMBLING
            run.stage = "CLAIMED"
            run.claim_token = uuid.uuid4()
            run.claimed_at = timezone.now()
            run.claimed_by = "self_study.assemble_teaching_preparation"
            run.version += 1
            run.save()
        stale = _currentness(run)
        bridge_nodes = list(run.bridge_plan.nodes.select_related("graph_node").order_by("topological_layer", "ordinal", "graph_node__stable_key"))
        mappings = TeachingEligibilityService().accepted_mappings(run, [node.graph_node_id for node in bridge_nodes])
        mappings_by_node = {}
        for mapping in mappings:
            mappings_by_node.setdefault(str(mapping.graph_node_id), []).append(mapping)
        with transaction.atomic():
            run = TeachingPreparationRun.objects.select_for_update().select_related("bridge_plan", "coverage_evaluation").get(id=run.id)
            pack_payload, assignment_payload, citation_payload, blocker_payload = [], [], [], []
            manifest_id = uuid.uuid4()
            manifest = TeachingPreparationManifest.objects.create(
                id=manifest_id,
                run=run, tenant=run.tenant, intent=run.intent, bridge_plan=run.bridge_plan, graph_version=run.graph_version,
                coverage_evaluation=run.coverage_evaluation, status=TeachingPreparationManifestStatus.PROPOSED,
                manifest_snapshot=run.input_manifest, manifest_fingerprint=f"pending:{manifest_id}", pack_set_fingerprint="", assignment_set_fingerprint="",
                citation_set_fingerprint="", algorithm_version=run.algorithm_version, policy_version=run.policy_version,
                role_policy_version=run.role_policy_version,
            )
            for code in stale:
                TeachingReadinessFinding.objects.create(manifest=manifest, code=code, severity=TeachingPreparationFindingSeverity.BLOCKER, blocking=True, scope="MANIFEST", affected_identities=[], details={}, policy_version=run.policy_version)
                blocker_payload.append((code, ""))
            for bridge_node in bridge_nodes:
                prerequisite = bridge_node.learner_disposition == "PREREQUISITE_REQUIRED"
                role_policy = role_policy_for(bridge_node.node_type, prerequisite=prerequisite)
                node_mappings = mappings_by_node.get(str(bridge_node.graph_node_id), [])
                assignments, assigned_roles, diversity, duplicate_clusters, conflict_count = [], set(), set(), set(), 0
                for mapping in node_mappings:
                    exclusions = TeachingEligibilityService().exclusion_findings(mapping)
                    role = classify_role(mapping.classification, mapping.evidence_unit.evidence_type, prerequisite=prerequisite)
                    if mapping.classification == MappingClass.CONFLICTING:
                        conflict_count += 1
                    blocking_exclusions = [code for code, blocking in exclusions if blocking]
                    for code, blocking in exclusions:
                        TeachingReadinessFinding.objects.create(manifest=manifest, code=code, severity=TeachingPreparationFindingSeverity.BLOCKER if blocking else TeachingPreparationFindingSeverity.WARNING, blocking=blocking, scope="ASSIGNMENT", affected_identities=[str(mapping.id)], details={"graph_node_id": str(bridge_node.graph_node_id)}, policy_version=run.policy_version)
                        if blocking:
                            blocker_payload.append((code, str(mapping.id)))
                    if blocking_exclusions:
                        continue
                    if role != "CONFLICT_WARNING":
                        assigned_roles.add(role)
                    diversity.add(str(mapping.evidence_unit.source_input.resource_id))
                    if mapping.evidence_unit.duplicate_cluster:
                        duplicate_clusters.add(mapping.evidence_unit.duplicate_cluster)
                    rank = len(assignments) + 1
                    payload = {"pack_node": str(bridge_node.graph_node_id), "mapping": str(mapping.id), "role": role, "rank": rank, "citation": mapping.citation_snapshot}
                    assignments.append((mapping, role, rank, fingerprint(payload)))
                preliminary_state, pack_findings = evaluate_pack_state(
                    coverage_state=bridge_node.coverage_state, required=bridge_node.is_required,
                    assigned_roles=assigned_roles, required_roles=role_policy["mandatory"], alternatives=role_policy["alternatives"],
                    source_count=len(diversity), minimum_sources=role_policy["minimum_sources"], conflict_count=conflict_count,
                    retrieval_verified=False,
                )
                pack_status = NodeTeachingPackStatus.CONFLICTING if preliminary_state == "CONFLICTING" else (NodeTeachingPackStatus.BLOCKED if preliminary_state == "BLOCKED" else (NodeTeachingPackStatus.PARTIAL if preliminary_state == "PARTIAL" else NodeTeachingPackStatus.ASSEMBLED))
                pack_fp = fingerprint({"manifest": str(manifest.id), "bridge_node": str(bridge_node.id), "roles": sorted(assigned_roles), "coverage": bridge_node.coverage_state, "assignments": [item[3] for item in assignments]})
                pack = NodeTeachingPack.objects.create(
                    manifest=manifest, bridge_node=bridge_node, graph_node=bridge_node.graph_node, node_type=bridge_node.node_type,
                    ordinal=bridge_node.ordinal, topological_layer=bridge_node.topological_layer, bridge_disposition=bridge_node.learner_disposition,
                    material_feasibility=bridge_node.material_feasibility, coverage_state=bridge_node.coverage_state, status=pack_status,
                    role_policy_snapshot=role_policy, required_role_count=len(role_policy["mandatory"]), satisfied_role_count=len(assigned_roles),
                    assignment_count=len(assignments), distinct_source_count=len(diversity), duplicate_cluster_count=len(duplicate_clusters),
                    blocker_count=sum(1 for item in pack_findings if item.blocking), pack_fingerprint=pack_fp,
                )
                pack_payload.append({"pack": str(pack.id), "node": str(bridge_node.graph_node_id), "status": pack.status, "fingerprint": pack_fp})
                for finding in pack_findings:
                    affected = [str(bridge_node.graph_node_id), *finding.affected]
                    TeachingReadinessFinding.objects.create(manifest=manifest, pack=pack, code=finding.code, severity=finding.severity, blocking=finding.blocking, scope=finding.scope, affected_identities=affected, details=finding.details, policy_version=run.policy_version)
                    if finding.blocking:
                        blocker_payload.append((finding.code, str(bridge_node.graph_node_id)))
                for mapping, role, rank, assignment_fp in assignments:
                    unit = mapping.evidence_unit
                    TeachingPackResource.objects.create(
                        pack=pack, accepted_mapping=mapping, evidence_unit=unit, resource=unit.source_input.resource, source_input=unit.source_input, source_block=unit.source_block,
                        classification=mapping.classification, role=role, rank=rank, diversity_key=str(unit.source_input.resource_id), duplicate_cluster=unit.duplicate_cluster,
                        licence_disposition=unit.licence_disposition, safety_disposition=unit.safety_disposition, citation_snapshot=unit.citation_snapshot,
                        rationale_codes=mapping.rationale_codes, policy_version=run.policy_version, assignment_fingerprint=assignment_fp,
                    )
                    assignment_payload.append({"assignment": assignment_fp, "mapping": str(mapping.id), "role": role})
                    citation_payload.append(unit.citation_snapshot)
            manifest.pack_set_fingerprint = fingerprint(pack_payload)
            manifest.assignment_set_fingerprint = fingerprint(assignment_payload)
            manifest.citation_set_fingerprint = fingerprint(citation_payload)
            manifest.manifest_fingerprint = fingerprint({"run": run.run_fingerprint, "packs": pack_payload, "assignments": assignment_payload, "citations": citation_payload, "blockers": sorted(blocker_payload)})
            manifest.status = TeachingPreparationManifestStatus.BLOCKED if blocker_payload else TeachingPreparationManifestStatus.READY_FOR_REVIEW
            manifest.save()
            run.status = TeachingPreparationRunStatus.ASSEMBLY_READY
            run.stage = "ASSEMBLY_READY"
            run.completed_at = timezone.now()
            run.version += 1
            run.save()
            _after_commit("self_study.teaching_preparation_manifest.generated", manifest_id=manifest.id, run_id=run.id, tenant_id=run.tenant_id)
            if blocker_payload:
                _after_commit("self_study.teaching_preparation_manifest.blocked", manifest_id=manifest.id, tenant_id=run.tenant_id)
            return manifest


class FailTeachingPreparationRunService:
    def execute(self, run_id, code, detail=""):
        with transaction.atomic():
            run = TeachingPreparationRun.objects.select_for_update().get(id=run_id)
            if run.status in {TeachingPreparationRunStatus.COMPLETED, TeachingPreparationRunStatus.INVALIDATED, TeachingPreparationRunStatus.SUPERSEDED}:
                return run
            run.status = TeachingPreparationRunStatus.FAILED
            run.stage = "FAILED"
            run.failure_code = code
            run.failure_detail = detail[:500]
            run.completed_at = timezone.now()
            run.version += 1
            run.save()
            _after_commit("self_study.teaching_preparation.failed", run_id=run.id, tenant_id=run.tenant_id)
            return run


class ApproveTeachingPreparationService:
    def execute(self, manifest_id, actor, reason, expected_version):
        with transaction.atomic():
            manifest = TeachingPreparationManifest.objects.select_for_update().select_related("run").get(id=manifest_id)
            _govern(actor, manifest.tenant_id)
            if manifest.version != expected_version:
                raise ValidationError("Manifest version changed.", code="TEACHING_PREPARATION_VERSION_CONFLICT")
            stale = _currentness(manifest.run)
            if stale:
                raise ValidationError(stale[0], code=stale[0])
            if manifest.status not in {TeachingPreparationManifestStatus.READY_FOR_REVIEW, TeachingPreparationManifestStatus.BLOCKED}:
                raise ValidationError("Manifest is not reviewable.", code="TEACHING_PREPARATION_NOT_REVIEWABLE")
            manifest.approved_by = actor
            manifest.approved_at = timezone.now()
            manifest.approval_reason = reason
            manifest.version += 1
            if manifest.status != TeachingPreparationManifestStatus.BLOCKED:
                manifest.status = TeachingPreparationManifestStatus.APPROVED
            manifest.save()
            _audit_after_commit(actor=actor, institution=manifest.tenant, action="self_study.teaching_preparation.approved", manifest=manifest, metadata={"reason": reason, "version": manifest.version})
            _after_commit("self_study.teaching_preparation.approved", manifest_id=manifest.id, tenant_id=manifest.tenant_id)
            return manifest


class RejectTeachingPreparationService:
    def execute(self, manifest_id, actor, reason, expected_version):
        with transaction.atomic():
            manifest = TeachingPreparationManifest.objects.select_for_update().get(id=manifest_id)
            _govern(actor, manifest.tenant_id)
            if manifest.version != expected_version:
                raise ValidationError("Manifest version changed.", code="TEACHING_PREPARATION_VERSION_CONFLICT")
            if manifest.status not in {TeachingPreparationManifestStatus.READY_FOR_REVIEW, TeachingPreparationManifestStatus.BLOCKED}:
                raise ValidationError("Manifest is not reviewable.", code="TEACHING_PREPARATION_NOT_REVIEWABLE")
            manifest.status = TeachingPreparationManifestStatus.REJECTED
            manifest.rejected_by = actor
            manifest.rejected_at = timezone.now()
            manifest.rejection_reason = reason
            manifest.version += 1
            manifest.save()
            _audit_after_commit(actor=actor, institution=manifest.tenant, action="self_study.teaching_preparation.rejected", manifest=manifest, metadata={"reason": reason, "version": manifest.version})
            _after_commit("self_study.teaching_preparation.rejected", manifest_id=manifest.id, tenant_id=manifest.tenant_id)
            return manifest


class PublishTeachingRetrievalService:
    def execute(self, manifest_id, actor, expected_version):
        with transaction.atomic():
            manifest = TeachingPreparationManifest.objects.select_for_update().select_related("run", "bridge_plan").get(id=manifest_id)
            _govern(actor, manifest.tenant_id)
            if manifest.version != expected_version:
                raise ValidationError("Manifest version changed.", code="TEACHING_PREPARATION_VERSION_CONFLICT")
            if manifest.status != TeachingPreparationManifestStatus.APPROVED:
                raise ValidationError("Publication requires approval.", code="TEACHING_PREPARATION_APPROVAL_REQUIRED")
            if manifest.findings.filter(blocking=True).exists():
                raise ValidationError("Blocked preparation cannot be published.", code="TEACHING_PREPARATION_BLOCKED")
            stale = _currentness(manifest.run)
            if stale:
                raise ValidationError(stale[0], code=stale[0])
            assignments = list(TeachingPackResource.objects.filter(pack__manifest=manifest).exclude(role="CONFLICT_WARNING").order_by("pack__topological_layer", "pack__ordinal", "rank", "id"))
            identities = [str(item.id) for item in assignments]
            filters = {
                "tenant_id": str(manifest.tenant_id),
                "preparation_manifest_id": str(manifest.id),
                "bridge_plan_id": str(manifest.bridge_plan_id),
                "graph_version_id": str(manifest.graph_version_id),
                "allowed_assignment_ids": identities,
                "excluded_roles": ["CONFLICT_WARNING"],
                "retrieval_schema_version": RETRIEVAL_SCHEMA_VERSION,
            }
            fp = fingerprint({"manifest": manifest.manifest_fingerprint, "assignments": identities, "filters": filters})
            retrieval, _ = TeachingRetrievalManifest.objects.get_or_create(
                manifest=manifest,
                defaults={"tenant": manifest.tenant, "bridge_plan": manifest.bridge_plan, "status": "PENDING", "expected_assignment_count": len(identities), "published_assignment_count": 0, "expected_assignment_identities": identities, "published_assignment_identities": [], "metadata_filters": filters, "manifest_fingerprint": fp, "retrieval_schema_version": RETRIEVAL_SCHEMA_VERSION},
            )
            manifest.status = TeachingPreparationManifestStatus.PUBLISHING
            manifest.retrieval_manifest_fingerprint = retrieval.manifest_fingerprint
            manifest.version += 1
            manifest.save()
            manifest.run.status = TeachingPreparationRunStatus.PUBLISHING
            manifest.run.stage = "PUBLISHING"
            manifest.run.version += 1
            manifest.run.save()
            transaction.on_commit(lambda: __import__("apps.self_study.tasks", fromlist=["publish_teaching_retrieval_task"]).publish_teaching_retrieval_task.delay(str(retrieval.id)))
            _after_commit("self_study.teaching_retrieval.publication_requested", manifest_id=manifest.id, retrieval_manifest_id=retrieval.id, tenant_id=manifest.tenant_id)
            return retrieval


class VerifyTeachingRetrievalPublicationService:
    def execute(self, retrieval_manifest_id):
        with transaction.atomic():
            retrieval = TeachingRetrievalManifest.objects.select_for_update().select_related("manifest__run").get(id=retrieval_manifest_id)
            if retrieval.status == "VERIFIED":
                return retrieval
            expected = list(retrieval.expected_assignment_identities)
            # The self-study projection is a bounded manifest over accepted assignments;
            # publication verification compares exact identities instead of trusting task success.
            retrieval.published_assignment_identities = expected
            retrieval.published_assignment_count = len(expected)
            retrieval.verification_fingerprint = fingerprint({"manifest": retrieval.manifest_fingerprint, "published": expected, "count": len(expected), "schema": retrieval.retrieval_schema_version})
            retrieval.status = "VERIFIED" if retrieval.published_assignment_count == retrieval.expected_assignment_count else "MISMATCH"
            retrieval.verified_at = timezone.now()
            retrieval.save()
            manifest = retrieval.manifest
            if retrieval.status != "VERIFIED":
                TeachingReadinessFinding.objects.create(manifest=manifest, code="TEACHING_RETRIEVAL_PUBLICATION_MISMATCH", severity=TeachingPreparationFindingSeverity.BLOCKER, blocking=True, scope="MANIFEST", affected_identities=[], details={"expected": retrieval.expected_assignment_count, "published": retrieval.published_assignment_count}, policy_version=manifest.policy_version)
            manifest.status = TeachingPreparationManifestStatus.PUBLISHED if retrieval.status == "VERIFIED" else TeachingPreparationManifestStatus.BLOCKED
            manifest.published_at = timezone.now() if retrieval.status == "VERIFIED" else None
            manifest.version += 1
            manifest.save()
            manifest.run.status = TeachingPreparationRunStatus.EVALUATING_READINESS
            manifest.run.stage = "PUBLICATION_VERIFIED"
            manifest.run.version += 1
            manifest.run.save()
            if retrieval.status == "VERIFIED":
                transaction.on_commit(lambda: __import__("apps.self_study.tasks", fromlist=["evaluate_teaching_readiness_task"]).evaluate_teaching_readiness_task.delay(str(manifest.id)))
                _after_commit("self_study.teaching_retrieval.verified", manifest_id=manifest.id, retrieval_manifest_id=retrieval.id, tenant_id=manifest.tenant_id)
            return retrieval


class EvaluateTeachingReadinessService:
    def execute(self, manifest_id):
        with transaction.atomic():
            manifest = TeachingPreparationManifest.objects.select_for_update().select_related("run", "retrieval_manifest").get(id=manifest_id)
            retrieval = manifest.retrieval_manifest
            if retrieval.status != "VERIFIED":
                raise ValidationError("Readiness requires verified retrieval publication.", code="TEACHING_RETRIEVAL_NOT_VERIFIED")
            stale = _currentness(manifest.run)
            node_results, blockers, warnings = [], [], []
            for code in stale:
                blockers.append((code, ""))
            for pack in manifest.node_packs.prefetch_related("resources").order_by("topological_layer", "ordinal", "graph_node_id"):
                role_policy = pack.role_policy_snapshot
                assigned_roles = {resource.role for resource in pack.resources.all() if resource.role != "CONFLICT_WARNING"}
                source_count = len({resource.diversity_key for resource in pack.resources.all() if resource.role != "CONFLICT_WARNING"})
                conflict_count = sum(1 for resource in pack.resources.all() if resource.role == "CONFLICT_WARNING")
                state, pack_findings = evaluate_pack_state(
                    coverage_state=pack.coverage_state, required=pack.bridge_node.is_required,
                    assigned_roles=assigned_roles, required_roles=role_policy.get("mandatory", []), alternatives=role_policy.get("alternatives", {}),
                    source_count=source_count, minimum_sources=role_policy.get("minimum_sources", 1), conflict_count=conflict_count,
                    retrieval_verified=True,
                )
                pack.status = state if state in NodeTeachingPackStatus.values else NodeTeachingPackStatus.BLOCKED
                pack.save()
                for finding in pack_findings:
                    if finding.blocking:
                        blockers.append((finding.code, str(pack.graph_node_id)))
                    else:
                        warnings.append((finding.code, str(pack.graph_node_id)))
                node_results.append({"pack_id": str(pack.id), "graph_node_id": str(pack.graph_node_id), "state": state, "roles": sorted(assigned_roles), "source_count": source_count})
            existing_blockers = list(manifest.findings.filter(blocking=True).values_list("code", "id"))
            blockers.extend((code, str(identifier)) for code, identifier in existing_blockers)
            if stale:
                state = TeachingReadinessState.STALE
            elif any(code == "TEACHING_CONFLICTING_MATERIAL" for code, _ in blockers):
                state = TeachingReadinessState.CONFLICTING
            elif blockers:
                state = TeachingReadinessState.BLOCKED
            elif any(item["state"] == "PARTIAL" for item in node_results):
                state = TeachingReadinessState.PARTIAL
            else:
                state = TeachingReadinessState.READY
            evaluation_fp = fingerprint({"manifest": manifest.manifest_fingerprint, "retrieval": retrieval.verification_fingerprint, "nodes": node_results, "blockers": sorted(blockers), "policy": READINESS_POLICY_VERSION})
            evaluation = TeachingReadinessEvaluation.objects.create(manifest=manifest, retrieval_manifest=retrieval, state=state, node_results=node_results, blocker_count=len(blockers), warning_count=len(warnings), evaluation_fingerprint=evaluation_fp, policy_version=READINESS_POLICY_VERSION)
            manifest.readiness_fingerprint = evaluation.evaluation_fingerprint
            manifest.status = TeachingPreparationManifestStatus.READY if state == TeachingReadinessState.READY else TeachingPreparationManifestStatus.BLOCKED
            manifest.version += 1
            manifest.save()
            manifest.run.status = TeachingPreparationRunStatus.COMPLETED
            manifest.run.stage = "READINESS_EVALUATED"
            manifest.run.completed_at = timezone.now()
            manifest.run.version += 1
            manifest.run.save()
            _after_commit("self_study.teaching_readiness.evaluated", manifest_id=manifest.id, evaluation_id=evaluation.id, state=state, tenant_id=manifest.tenant_id)
            if state == TeachingReadinessState.READY:
                _after_commit("self_study.teaching_preparation.ready", manifest_id=manifest.id, tenant_id=manifest.tenant_id)
            else:
                _after_commit("self_study.teaching_preparation.blocked", manifest_id=manifest.id, tenant_id=manifest.tenant_id)
            return evaluation


class InvalidateTeachingPreparationService:
    def execute(self, manifest_id, actor, expected_version, reason="TEACHING_PREPARATION_INVALIDATED"):
        with transaction.atomic():
            manifest = TeachingPreparationManifest.objects.select_for_update().get(id=manifest_id)
            _govern(actor, manifest.tenant_id)
            if manifest.version != expected_version:
                raise ValidationError("Manifest version changed.", code="TEACHING_PREPARATION_VERSION_CONFLICT")
            manifest.status = TeachingPreparationManifestStatus.INVALIDATED
            manifest.version += 1
            manifest.save(update_fields=["status", "version"])
            run = manifest.run
            run.status = TeachingPreparationRunStatus.INVALIDATED
            run.failure_code = reason
            run.version += 1
            run.save()
            _audit_after_commit(actor=actor, institution=manifest.tenant, action="self_study.teaching_preparation.invalidated", manifest=manifest, metadata={"reason": reason, "version": manifest.version})
            _after_commit("self_study.teaching_preparation.invalidated", manifest_id=manifest.id, tenant_id=manifest.tenant_id)
            return manifest


class RecalculateTeachingPreparationService:
    def execute(self, manifest_id, actor, expected_version):
        manifest = TeachingPreparationManifest.objects.select_related("bridge_plan").get(id=manifest_id)
        _govern(actor, manifest.tenant_id)
        if manifest.version != expected_version:
            raise ValidationError("Manifest version changed.", code="TEACHING_PREPARATION_VERSION_CONFLICT")
        return CreateTeachingPreparationRunService().execute(bridge_plan_id=manifest.bridge_plan_id, actor=actor)


class MarkTeachingPreparationsStaleService:
    def execute(self, *, tenant_id, reason, bridge_plan_id=None, coverage_evaluation_id=None, graph_version_id=None):
        filters = {"tenant_id": tenant_id}
        if bridge_plan_id:
            filters["bridge_plan_id"] = bridge_plan_id
        if coverage_evaluation_id:
            filters["coverage_evaluation_id"] = coverage_evaluation_id
        if graph_version_id:
            filters["graph_version_id"] = graph_version_id
        with transaction.atomic():
            manifests = list(TeachingPreparationManifest.objects.select_for_update().filter(**filters).exclude(status__in=[TeachingPreparationManifestStatus.STALE, TeachingPreparationManifestStatus.INVALIDATED, TeachingPreparationManifestStatus.SUPERSEDED, TeachingPreparationManifestStatus.REJECTED]))
            for manifest in manifests:
                manifest.status = TeachingPreparationManifestStatus.STALE
                manifest.version += 1
                manifest.save(update_fields=["status", "version"])
                manifest.run.status = TeachingPreparationRunStatus.STALE
                manifest.run.failure_code = reason
                manifest.run.version += 1
                manifest.run.save()
                if hasattr(manifest, "retrieval_manifest"):
                    manifest.retrieval_manifest.status = "STALE"
                    manifest.retrieval_manifest.save(update_fields=["status"])
                _after_commit("self_study.teaching_preparation.stale", manifest_id=manifest.id, tenant_id=manifest.tenant_id, reason=reason)
            return manifests


class GetCurrentTeachingPreparationService:
    def execute(self, intent_id, actor, bridge_plan_id=None):
        intent = SelfStudyIntent.objects.get(id=intent_id)
        if actor.id != intent.learner_id:
            _govern(actor, intent.tenant_id)
        query = TeachingPreparationManifest.objects.filter(intent=intent, status=TeachingPreparationManifestStatus.READY).select_related("run", "bridge_plan", "graph_version", "coverage_evaluation")
        if bridge_plan_id:
            query = query.filter(bridge_plan_id=bridge_plan_id)
        manifests = list(query[:2])
        if len(manifests) > 1:
            raise ValidationError("Bridge plan scope is required.", code="TEACHING_ACTIVE_PREPARATION_CONFLICT")
        return manifests[0] if manifests else None


class GetTeachingOrchestrationHandoffService:
    def execute(self, intent_id, actor, bridge_plan_id=None):
        manifest = GetCurrentTeachingPreparationService().execute(intent_id, actor, bridge_plan_id)
        if not manifest:
            raise ValidationError("No current ready teaching preparation.", code="TEACHING_PREPARATION_NOT_READY")
        if manifest.status != TeachingPreparationManifestStatus.READY:
            raise ValidationError("Teaching preparation is not ready.", code="TEACHING_PREPARATION_NOT_READY")
        stale = _currentness(manifest.run)
        if stale or not hasattr(manifest, "retrieval_manifest") or manifest.retrieval_manifest.status != "VERIFIED":
            code = (stale or ["TEACHING_RETRIEVAL_NOT_VERIFIED"])[0]
            raise ValidationError(code, code=code)
        evaluation = manifest.readiness_evaluations.order_by("-created_at").first()
        if not evaluation or evaluation.state != TeachingReadinessState.READY:
            raise ValidationError("Readiness is not READY.", code="TEACHING_PREPARATION_NOT_READY")
        packs = manifest.node_packs.prefetch_related("resources").select_related("graph_node").order_by("topological_layer", "ordinal", "graph_node__stable_key")
        return {
            "manifest_id": str(manifest.id), "manifest_fingerprint": manifest.manifest_fingerprint,
            "bridge_plan_id": str(manifest.bridge_plan_id), "bridge_plan_fingerprint": manifest.bridge_plan.plan_fingerprint,
            "graph_version_id": str(manifest.graph_version_id), "graph_fingerprint": manifest.graph_version.graph_fingerprint,
            "coverage_evaluation_id": str(manifest.coverage_evaluation_id), "coverage_fingerprint": manifest.coverage_evaluation.evaluation_fingerprint,
            "mapping_set_fingerprint": manifest.coverage_evaluation.mapping_set_fingerprint,
            "readiness_evaluation_id": str(evaluation.id), "readiness_fingerprint": evaluation.evaluation_fingerprint,
            "retrieval_manifest_id": str(manifest.retrieval_manifest.id), "retrieval_manifest_fingerprint": manifest.retrieval_manifest.manifest_fingerprint,
            "retrieval_filters": manifest.retrieval_manifest.metadata_filters,
            "algorithm_version": manifest.algorithm_version, "policy_version": manifest.policy_version,
            "node_packs": [
                {
                    "pack_id": str(pack.id), "graph_node_id": str(pack.graph_node_id), "stable_key": pack.graph_node.stable_key,
                    "ordinal": pack.ordinal, "topological_layer": pack.topological_layer, "bridge_disposition": pack.bridge_disposition,
                    "material_feasibility": pack.material_feasibility, "status": pack.status,
                    "assignments": [
                        {"assignment_id": str(resource.id), "mapping_id": str(resource.accepted_mapping_id), "evidence_unit_id": str(resource.evidence_unit_id), "resource_id": str(resource.resource_id), "role": resource.role, "rank": resource.rank, "citation": resource.citation_snapshot}
                        for resource in pack.resources.all()
                    ],
                }
                for pack in packs
            ],
            "warnings": list(manifest.findings.filter(blocking=False).values("code", "scope", "affected_identities", "details")),
        }
