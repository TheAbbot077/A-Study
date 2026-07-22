from __future__ import annotations

import hashlib
import json
from collections import deque

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.core.events import BusinessEvent, EventPublisher

from ..application.services import _has_institutional_authority, ensure_access
from ..curriculum_models import CompositeStatus, CurriculumResolutionAttempt, CurriculumVersionStatus, ResolutionAttemptStatus
from ..domain.curriculum_graph import (
    BUILDER_ALGORITHM_VERSION,
    STABLE_KEY_ALGORITHM_VERSION,
    VALIDATION_ALGORITHM_VERSION,
    CurriculumGraphSpecification,
    graph_fingerprint,
    stable_edge_key,
    stable_node_key,
)
from ..graph_models import (
    CitationType,
    ConstructionMethod,
    CurriculumEdge,
    CurriculumGraph,
    CurriculumGraphCitation,
    CurriculumGraphFinding,
    CurriculumGraphSpecificationRecord,
    CurriculumGraphValidationRun,
    CurriculumGraphVersion,
    CurriculumNode,
    EdgeType,
    FindingSeverity,
    GraphStatus,
    GraphVersionStatus,
    NodeType,
    RequirementType,
    ValidationRunStatus,
)
from ..models import LearningMode, SelfStudyIntent


def _publish(events, name, payload):
    events.publish(BusinessEvent.create(name, payload=payload))


def _authoritative_sources(attempt: CurriculumResolutionAttempt):
    if attempt.status != ResolutionAttemptStatus.SELECTED:
        raise ValidationError("Curriculum selection is not terminal.", code="CURRICULUM_SELECTION_NOT_TERMINAL")
    if hasattr(attempt, "selection"):
        return [attempt.selection.curriculum_version], attempt.selection, None
    if hasattr(attempt, "composite_proposal") and attempt.composite_proposal.status == CompositeStatus.APPROVED:
        versions = [item.curriculum_version for item in attempt.composite_proposal.components.select_related("curriculum_version").order_by("priority")]
        return versions, None, attempt.composite_proposal
    raise ValidationError("A selection or approved composite is required.", code="CURRICULUM_SELECTION_REQUIRED")


def _selection_fingerprint(attempt, versions):
    return hashlib.sha256(json.dumps({
        "attempt": str(attempt.id), "intent_version": attempt.intent_version,
        "registry": attempt.registry_snapshot_identifier,
        "resolver": attempt.algorithm_version,
        "versions": [str(item.id) for item in versions],
    }, sort_keys=True).encode()).hexdigest()


class StartCurriculumGraphBuildService:
    def __init__(self, events=None):
        self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, *, attempt_id, actor, construction_method):
        attempt = CurriculumResolutionAttempt.objects.select_for_update().get(id=attempt_id)
        intent = SelfStudyIntent.objects.get(id=attempt.intent_id)
        ensure_access(actor, intent, mutate=True)
        versions, decision, composite = _authoritative_sources(attempt)
        if any(item.status != CurriculumVersionStatus.ACTIVE for item in versions):
            raise ValidationError("Selected curriculum source is not active.", code="CURRICULUM_GRAPH_SOURCE_CHANGED")
        expected_method = ConstructionMethod.COMPOSITE_ASSEMBLY if composite else construction_method
        if composite and construction_method != ConstructionMethod.COMPOSITE_ASSEMBLY:
            raise ValidationError("Composite construction method is required.", code="COMPOSITE_APPROVAL_REQUIRED")
        existing = CurriculumGraph.objects.filter(selection_decision=decision).first() if decision else CurriculumGraph.objects.filter(composite_proposal=composite).first()
        if existing:
            return existing, existing.current_version, True
        graph = CurriculumGraph.objects.create(
            tenant=intent.tenant, intent=intent, selection_decision=decision, composite_proposal=composite,
        )
        version = CurriculumGraphVersion.objects.create(
            graph=graph, version_number=1, source_selection_fingerprint=_selection_fingerprint(attempt, versions),
            builder_algorithm_version=BUILDER_ALGORITHM_VERSION,
            validation_algorithm_version=VALIDATION_ALGORITHM_VERSION,
            stable_key_algorithm_version=STABLE_KEY_ALGORITHM_VERSION,
            source_language=versions[0].language, construction_method=expected_method, created_by=actor,
        )
        graph.current_version = version
        graph.save(update_fields=["current_version", "updated_at"])
        transaction.on_commit(lambda: _publish(self.events, "curriculum_graph.build_started", {"graph_id": str(graph.id), "graph_version_id": str(version.id)}))
        return graph, version, False


class PersistCurriculumGraphSpecificationService:
    def __init__(self, events=None, enqueue=True):
        self.events = events or EventPublisher(); self.enqueue = enqueue

    @transaction.atomic
    def execute(self, *, graph_version_id, payload, actor):
        version = CurriculumGraphVersion.objects.select_for_update().get(id=graph_version_id)
        graph = CurriculumGraph.objects.get(id=version.graph_id)
        if not (actor.is_superuser or _has_institutional_authority(actor, graph.tenant_id)):
            raise PermissionDenied("CURRICULUM_GRAPH_ACCESS_DENIED")
        if version.status != GraphVersionStatus.DRAFT:
            existing = CurriculumGraphSpecificationRecord.objects.filter(graph_version=version).first()
            if existing:
                return existing, True
            raise ValidationError("Graph build is already in progress.", code="CURRICULUM_GRAPH_BUILD_IN_PROGRESS")
        attempt = graph.selection_decision.attempt if graph.selection_decision_id else graph.composite_proposal.attempt
        sources, _, _ = _authoritative_sources(attempt)
        try:
            specification = CurriculumGraphSpecification.from_payload(payload)
            specification.validate_shape({str(item.id) for item in sources})
        except ValueError as exc:
            raise ValidationError(str(exc), code="CURRICULUM_GRAPH_SPECIFICATION_INVALID") from exc
        if specification.construction_method != version.construction_method:
            raise ValidationError("Construction method does not match the graph version.", code="CURRICULUM_GRAPH_SPECIFICATION_INVALID")
        checksum = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        record = CurriculumGraphSpecificationRecord.objects.create(
            graph_version=version, payload=payload, specification_checksum=checksum,
            submitted_by=actor, producer=specification.producer,
        )
        transaction.on_commit(lambda: self._after_commit(record))
        return record, False

    def _after_commit(self, record):
        _publish(self.events, "curriculum_graph.specification_persisted", {"graph_version_id": str(record.graph_version_id), "specification_id": str(record.id)})
        if self.enqueue:
            from ..infrastructure.celery.tasks import build_curriculum_graph_task
            build_curriculum_graph_task.delay(str(record.graph_version_id))


class CreateCurriculumGraphVersionService:
    """Create a correction version without mutating a historical graph version."""

    @transaction.atomic
    def execute(self, *, graph_id, actor, construction_method):
        graph = CurriculumGraph.objects.select_for_update().select_related("intent", "current_version").get(id=graph_id)
        ensure_access(actor, graph.intent, mutate=True)
        if not (actor.is_superuser or _has_institutional_authority(actor, graph.tenant_id)):
            raise PermissionDenied("CURRICULUM_GRAPH_ACCESS_DENIED")
        current = graph.current_version
        if current and current.status not in {
            GraphVersionStatus.PUBLISHED, GraphVersionStatus.INVALID, GraphVersionStatus.INVALIDATED
        }:
            raise ValidationError("The current graph version is not terminal.", code="CURRICULUM_GRAPH_BUILD_IN_PROGRESS")
        attempt = graph.selection_decision.attempt if graph.selection_decision_id else graph.composite_proposal.attempt
        sources, _, composite = _authoritative_sources(attempt)
        required_method = ConstructionMethod.COMPOSITE_ASSEMBLY if composite else construction_method
        if composite and construction_method != required_method:
            raise ValidationError("Composite construction method is required.", code="COMPOSITE_APPROVAL_REQUIRED")
        version = CurriculumGraphVersion.objects.create(
            graph=graph, version_number=(current.version_number + 1 if current else 1), supersedes=current,
            source_selection_fingerprint=_selection_fingerprint(attempt, sources),
            builder_algorithm_version=BUILDER_ALGORITHM_VERSION,
            validation_algorithm_version=VALIDATION_ALGORITHM_VERSION,
            stable_key_algorithm_version=STABLE_KEY_ALGORITHM_VERSION,
            source_language=sources[0].language, construction_method=required_method, created_by=actor,
        )
        graph.current_version = version; graph.status = GraphStatus.DRAFT
        graph.save(update_fields=["current_version", "status", "updated_at"])
        return version


def _fingerprint_version(version):
    nodes = [{
        "stable_key": item.stable_key, "type": item.node_type, "title": item.title,
        "description": item.description, "depth": item.depth, "source": str(item.source_curriculum_version_id),
        "namespace": item.authority_namespace, "external_identifier": item.external_identifier,
        "external_status": item.external_prerequisite_status, "metadata": item.metadata,
    } for item in version.nodes.order_by("stable_key")]
    edges = [{
        "stable_key": item.stable_key, "type": item.edge_type,
        "source": item.source_node.stable_key, "target": item.target_node.stable_key,
        "requirement": item.requirement, "strength": str(item.strength),
        "source_version": str(item.source_curriculum_version_id), "metadata": item.metadata,
    } for item in version.edges.select_related("source_node", "target_node").order_by("stable_key")]
    citations = [{
        "target_key": item.node.stable_key if item.node_id else item.edge.stable_key,
        "citation_type": item.citation_type, "source_version": str(item.curriculum_version_id),
        "source_uri": item.source_uri, "source_locator": item.source_locator,
        "excerpt": item.normalized_excerpt, "language": item.source_language,
    } for item in version.citations.select_related("node", "edge").order_by("id")]
    component_ids = sorted({str(item.source_curriculum_version_id) for item in version.nodes.all()})
    return graph_fingerprint(
        source_selection_fingerprint=version.source_selection_fingerprint,
        component_version_ids=component_ids, nodes=nodes, edges=edges, citations=citations,
        construction_method=version.construction_method,
    )


class BuildCurriculumGraphService:
    def __init__(self, events=None, enqueue_validation=True):
        self.events = events or EventPublisher(); self.enqueue_validation = enqueue_validation

    @transaction.atomic
    def execute(self, graph_version_id):
        version = CurriculumGraphVersion.objects.select_for_update().get(id=graph_version_id)
        if version.status in {GraphVersionStatus.VALIDATING, GraphVersionStatus.VALID, GraphVersionStatus.INVALID, GraphVersionStatus.PUBLISHED, GraphVersionStatus.SUPERSEDED, GraphVersionStatus.INVALIDATED}:
            return version
        if version.status == GraphVersionStatus.BUILDING:
            return version
        try:
            record = version.specification
        except CurriculumGraphSpecificationRecord.DoesNotExist as exc:
            raise ValidationError("Graph specification is required.", code="CURRICULUM_GRAPH_SPECIFICATION_INVALID") from exc
        graph = CurriculumGraph.objects.select_for_update().get(id=version.graph_id)
        attempt = graph.selection_decision.attempt if graph.selection_decision_id else graph.composite_proposal.attempt
        sources, _, _ = _authoritative_sources(attempt)
        if _selection_fingerprint(attempt, sources) != version.source_selection_fingerprint:
            raise ValidationError("Source selection changed.", code="CURRICULUM_GRAPH_SOURCE_CHANGED")
        specification = CurriculumGraphSpecification.from_payload(record.payload)
        specification.validate_shape({str(item.id) for item in sources})
        version.status = GraphVersionStatus.BUILDING; graph.status = GraphStatus.BUILDING
        version.save(update_fields=["status"]); graph.save(update_fields=["status", "updated_at"])
        nodes = {}
        stable_keys = set()
        for spec in specification.nodes:
            key = stable_node_key(
                source_version_id=spec.source_curriculum_version_id, authority_namespace=spec.authority_namespace,
                external_identifier=spec.external_identifier, node_type=spec.node_type,
                structural_path=spec.structural_path, title=spec.title,
            )
            if key in stable_keys:
                raise ValidationError("Node identity collision.", code="GRAPH_NODE_IDENTITY_COLLISION")
            stable_keys.add(key)
            nodes[spec.local_key] = CurriculumNode.objects.create(
                graph_version=version, stable_key=key, node_type=spec.node_type, title=spec.title,
                description=spec.description, ordinal=spec.ordinal, depth=spec.depth,
                source_curriculum_version_id=spec.source_curriculum_version_id,
                authority_namespace=spec.authority_namespace, external_identifier=spec.external_identifier,
                external_prerequisite_status=spec.external_prerequisite_status, metadata=spec.metadata,
            )
        edges = {}
        edge_keys = set()
        for spec in specification.edges:
            key = stable_edge_key(
                edge_type=spec.edge_type, source_key=nodes[spec.source_local_key].stable_key,
                target_key=nodes[spec.target_local_key].stable_key, requirement=spec.requirement,
            )
            if key in edge_keys:
                raise ValidationError("Edge identity collision.", code="GRAPH_EDGE_IDENTITY_COLLISION")
            edge_keys.add(key)
            metadata = {**spec.metadata, "derivation": spec.derivation}
            edges[spec.local_key] = CurriculumEdge.objects.create(
                graph_version=version, stable_key=key, edge_type=spec.edge_type,
                source_node=nodes[spec.source_local_key], target_node=nodes[spec.target_local_key],
                ordinal=spec.ordinal, requirement=spec.requirement, strength=spec.strength,
                source_curriculum_version_id=spec.source_curriculum_version_id, metadata=metadata,
            )
        for spec in specification.citations:
            target = nodes[spec.target_local_key] if spec.target_kind == "NODE" else edges[spec.target_local_key]
            CurriculumGraphCitation.objects.create(
                graph_version=version, node=target if spec.target_kind == "NODE" else None,
                edge=target if spec.target_kind == "EDGE" else None,
                curriculum_version_id=spec.curriculum_version_id,
                source_document_id=spec.source_document_id or None, source_uri=spec.source_uri,
                source_locator=spec.source_locator, normalized_excerpt=spec.normalized_excerpt,
                source_language=spec.source_language, citation_type=spec.citation_type,
                confidence=spec.confidence, rationale=spec.rationale,
                builder_algorithm_version=version.builder_algorithm_version,
            )
        version.node_count=len(nodes); version.edge_count=len(edges)
        version.root_count=sum(1 for item in nodes.values() if item.node_type == NodeType.CURRICULUM_ROOT)
        version.outcome_count=sum(1 for item in nodes.values() if item.node_type == NodeType.OUTCOME)
        version.graph_fingerprint=_fingerprint_version(version)
        version.status=GraphVersionStatus.VALIDATING; graph.status=GraphStatus.VALIDATING
        version.save(update_fields=["node_count", "edge_count", "root_count", "outcome_count", "graph_fingerprint", "status"])
        graph.save(update_fields=["status", "updated_at"])
        transaction.on_commit(lambda: self._after_commit(version))
        return version

    def _after_commit(self, version):
        _publish(self.events, "curriculum_graph.build_completed", {"graph_id": str(version.graph_id), "graph_version_id": str(version.id), "fingerprint": version.graph_fingerprint})
        if self.enqueue_validation:
            from ..infrastructure.celery.tasks import validate_curriculum_graph_task
            validate_curriculum_graph_task.delay(str(version.id))


def _has_cycle(nodes, adjacency):
    visiting, visited = set(), set()
    def visit(node):
        if node in visiting: return True
        if node in visited: return False
        visiting.add(node)
        for child in adjacency.get(node, ()):
            if visit(child): return True
        visiting.remove(node); visited.add(node); return False
    return any(visit(node) for node in nodes)


class ValidateCurriculumGraphService:
    def __init__(self, events=None): self.events = events or EventPublisher()

    @transaction.atomic
    def execute(self, graph_version_id):
        version = CurriculumGraphVersion.objects.select_for_update().get(id=graph_version_id)
        if version.status in {GraphVersionStatus.VALID, GraphVersionStatus.INVALID, GraphVersionStatus.PUBLISHED, GraphVersionStatus.SUPERSEDED, GraphVersionStatus.INVALIDATED}:
            return version.validation_runs.order_by("-created_at").first()
        if version.status != GraphVersionStatus.VALIDATING:
            raise ValidationError("Graph is not ready for validation.", code="CURRICULUM_GRAPH_VALIDATION_REQUIRED")
        current_fingerprint = _fingerprint_version(version)
        if current_fingerprint != version.graph_fingerprint:
            raise ValidationError("Graph fingerprint changed.", code="CURRICULUM_GRAPH_FINGERPRINT_CHANGED")
        run, created = CurriculumGraphValidationRun.objects.get_or_create(
            graph_version=version, graph_fingerprint=current_fingerprint,
            algorithm_version=VALIDATION_ALGORITHM_VERSION,
        )
        if not created and run.status in {ValidationRunStatus.PASSED, ValidationRunStatus.FAILED}:
            return run
        run.status=ValidationRunStatus.RUNNING; run.started_at=timezone.now(); run.save(update_fields=["status", "started_at"])
        findings = self._findings(version)
        CurriculumGraphFinding.objects.bulk_create([
            CurriculumGraphFinding(validation_run=run, **item) for item in findings
        ])
        blockers=sum(1 for item in findings if item["severity"] == FindingSeverity.BLOCKER)
        warnings=sum(1 for item in findings if item["severity"] == FindingSeverity.WARNING)
        run.status=ValidationRunStatus.FAILED if blockers else ValidationRunStatus.PASSED
        run.completed_at=timezone.now(); run.summary={"blockers": blockers, "warnings": warnings, "findings": len(findings)}
        run.save(update_fields=["status", "completed_at", "summary"])
        graph=CurriculumGraph.objects.select_for_update().get(id=version.graph_id)
        version.status=GraphVersionStatus.INVALID if blockers else GraphVersionStatus.VALID
        version.validation_summary=run.summary
        graph.status=GraphStatus.BLOCKED if blockers else GraphStatus.READY_FOR_PUBLICATION
        version.save(update_fields=["status", "validation_summary"]); graph.save(update_fields=["status", "updated_at"])
        event="curriculum_graph.validation_failed" if blockers else "curriculum_graph.ready_for_publication"
        transaction.on_commit(lambda: _publish(self.events, event, {"graph_id": str(graph.id), "graph_version_id": str(version.id), "validation_run_id": str(run.id)}))
        return run

    def _findings(self, version):
        nodes=list(version.nodes.all()); edges=list(version.edges.select_related("source_node", "target_node")); findings=[]
        def add(code, severity, message, node=None, edge=None, related_node=None, details=None):
            findings.append({"code":code,"severity":severity,"message":message,"node":node,"edge":edge,"related_node":related_node,"details":details or {}})
        roots=[item for item in nodes if item.node_type == NodeType.CURRICULUM_ROOT]
        if not roots: add("GRAPH_ROOT_MISSING", FindingSeverity.BLOCKER, "A curriculum root is required.")
        if len(roots)>1: add("GRAPH_ROOT_MULTIPLE", FindingSeverity.BLOCKER, "Only one curriculum root is permitted.")
        outcomes=[item for item in nodes if item.node_type == NodeType.OUTCOME]
        if not outcomes: add("GRAPH_OUTCOME_MISSING", FindingSeverity.BLOCKER, "At least one curriculum outcome is required.")
        structural=[item for item in edges if item.edge_type == EdgeType.PART_OF]
        structural_adj={}
        for edge in structural: structural_adj.setdefault(edge.source_node_id,set()).add(edge.target_node_id)
        if _has_cycle([item.id for item in nodes], structural_adj): add("GRAPH_STRUCTURAL_CYCLE", FindingSeverity.BLOCKER, "Structural hierarchy contains a cycle.")
        parent_counts={}
        for edge in structural: parent_counts[edge.source_node_id]=parent_counts.get(edge.source_node_id,0)+1
        for node_id, count in parent_counts.items():
            if count > 1:
                add("GRAPH_STRUCTURAL_PARENT_MULTIPLE", FindingSeverity.BLOCKER, "A structural node has multiple parents.", node=next(item for item in nodes if item.id == node_id))
        if len(roots) == 1:
            children={}
            for edge in structural: children.setdefault(edge.target_node_id,set()).add(edge.source_node_id)
            reachable={roots[0].id}; queue=deque([roots[0].id])
            while queue:
                for child in children.get(queue.popleft(), ()):
                    if child not in reachable: reachable.add(child); queue.append(child)
            for node in nodes:
                if node.node_type != NodeType.EXTERNAL_PREREQUISITE and node.id not in reachable:
                    add("GRAPH_NODE_UNREACHABLE", FindingSeverity.BLOCKER, "Node is not structurally reachable from the curriculum root.", node=node)
        required=[item for item in edges if item.edge_type == EdgeType.REQUIRES and item.requirement == RequirementType.REQUIRED]
        req_adj={}
        for edge in required: req_adj.setdefault(edge.source_node_id,set()).add(edge.target_node_id)
        if _has_cycle([item.id for item in nodes], req_adj): add("GRAPH_PREREQUISITE_CYCLE", FindingSeverity.BLOCKER, "Required prerequisites contain a cycle.")
        parented={item.source_node_id for item in structural}
        for node in nodes:
            if node.node_type not in {NodeType.CURRICULUM_ROOT, NodeType.EXTERNAL_PREREQUISITE} and node.id not in parented:
                add("GRAPH_ORPHAN_NODE", FindingSeverity.BLOCKER, "Node has no structural parent.", node=node)
        satisfies={item.target_node_id for item in edges if item.edge_type == EdgeType.SATISFIES and item.source_node.node_type in {NodeType.CONCEPT, NodeType.COMPETENCY}}
        for outcome in outcomes:
            if outcome.id not in satisfies: add("GRAPH_OUTCOME_UNSUPPORTED", FindingSeverity.BLOCKER, "Outcome has no supporting concept or competency.", node=outcome)
        for competency in [item for item in nodes if item.node_type == NodeType.COMPETENCY]:
            if not any(edge.edge_type == EdgeType.SATISFIES and edge.source_node_id == competency.id for edge in edges):
                add("GRAPH_COMPETENCY_UNALIGNED", FindingSeverity.BLOCKER, "Competency satisfies no outcome.", node=competency)
        citation_nodes=set(version.citations.exclude(node_id=None).values_list("node_id",flat=True)); citation_edges=set(version.citations.exclude(edge_id=None).values_list("edge_id",flat=True))
        for node in nodes:
            if node.id not in citation_nodes: add("GRAPH_CITATION_MISSING", FindingSeverity.BLOCKER, "Authoritative node lacks a citation.", node=node)
            if node.node_type == NodeType.EXTERNAL_PREREQUISITE and node.external_prerequisite_status == "UNRESOLVED":
                add("GRAPH_EXTERNAL_PREREQUISITE_UNRESOLVED", FindingSeverity.WARNING, "External prerequisite remains unresolved.", node=node)
        consequential={EdgeType.REQUIRES,EdgeType.SATISFIES,EdgeType.ASSESSED_BY,EdgeType.EQUIVALENT_TO,EdgeType.SPECIALIZES,EdgeType.BRIDGES_TO,EdgeType.CONFLICTS_WITH}
        for edge in edges:
            if edge.edge_type in consequential and edge.id not in citation_edges:
                add("GRAPH_CITATION_MISSING", FindingSeverity.BLOCKER, "Consequential edge lacks a citation.", edge=edge)
            if edge.edge_type == EdgeType.REQUIRES and edge.requirement == RequirementType.REQUIRED and edge.metadata.get("derivation") == "DOCUMENT_ADJACENCY":
                add("GRAPH_DERIVATION_UNSUPPORTED", FindingSeverity.BLOCKER, "Document adjacency cannot establish a required prerequisite.", edge=edge)
            if edge.edge_type == EdgeType.CONFLICTS_WITH:
                add("GRAPH_COMPOSITE_CONFLICT", FindingSeverity.BLOCKER, "Composite conflict requires governance resolution.", edge=edge)
        allowed_versions={str(item) for item in version.nodes.values_list("source_curriculum_version_id",flat=True)}
        for citation in version.citations.all():
            if str(citation.curriculum_version_id) not in allowed_versions or not citation.source_locator:
                add("GRAPH_CITATION_INVALID", FindingSeverity.BLOCKER, "Citation source is outside the selected curriculum or lacks a locator.", node=citation.node, edge=citation.edge)
            if citation.citation_type == CitationType.EXPLICIT and citation.rationale.startswith("DERIVED:"):
                add("GRAPH_CITATION_INVALID", FindingSeverity.BLOCKER, "Derived content cannot be marked explicit.", node=citation.node, edge=citation.edge)
        return findings


class PublishCurriculumGraphService:
    def __init__(self, events=None): self.events=events or EventPublisher()
    @transaction.atomic
    def execute(self, *, graph_version_id, actor, expected_fingerprint):
        version=CurriculumGraphVersion.objects.select_for_update().get(id=graph_version_id); graph=CurriculumGraph.objects.select_for_update().get(id=version.graph_id)
        ensure_access(actor, graph.intent, mutate=True)
        if version.status == GraphVersionStatus.PUBLISHED: return version
        if version.status != GraphVersionStatus.VALID or graph.status != GraphStatus.READY_FOR_PUBLICATION:
            raise ValidationError("Passed validation is required.", code="CURRICULUM_GRAPH_VALIDATION_REQUIRED")
        if version.graph_fingerprint != expected_fingerprint or _fingerprint_version(version) != expected_fingerprint:
            raise ValidationError("Graph fingerprint changed.", code="CURRICULUM_GRAPH_FINGERPRINT_CHANGED")
        run=version.validation_runs.filter(status=ValidationRunStatus.PASSED,graph_fingerprint=expected_fingerprint).order_by("-created_at").first()
        if not run or run.findings.filter(severity=FindingSeverity.BLOCKER,resolved_at__isnull=True).exists():
            raise ValidationError("Unresolved validation blockers remain.", code="CURRICULUM_GRAPH_VALIDATION_REQUIRED")
        if graph.intent.mode == LearningMode.INSTITUTION_GOVERNED and not _has_institutional_authority(actor,graph.tenant_id):
            raise PermissionDenied("CURRICULUM_GRAPH_PUBLICATION_NOT_AUTHORIZED")
        prior=graph.current_version
        if prior and prior.id != version.id and prior.status == GraphVersionStatus.PUBLISHED:
            prior.status=GraphVersionStatus.SUPERSEDED; prior.save(update_fields=["status"])
            transaction.on_commit(lambda prior_id=prior.id: self._stale_mapping_runs(prior_id))
        version.status=GraphVersionStatus.PUBLISHED; version.published_at=timezone.now(); version.published_by=actor
        version.save(update_fields=["status","published_at","published_by"])
        graph.status=GraphStatus.PUBLISHED; graph.current_version=version; graph.version+=1
        graph.save(update_fields=["status","current_version","version","updated_at"])
        transaction.on_commit(lambda:_publish(self.events,"curriculum_graph.published",{"graph_id":str(graph.id),"graph_version_id":str(version.id),"fingerprint":version.graph_fingerprint}))
        return version

    @staticmethod
    def _stale_mapping_runs(graph_version_id):
        from .evidence_services import InvalidateMappingsForGraphService
        InvalidateMappingsForGraphService().execute(graph_version_id, "COVERAGE_GRAPH_SUPERSEDED")


class InvalidateCurriculumGraphService:
    ALLOWED={"SOURCE_SELECTION_INVALIDATED","SOURCE_CURRICULUM_WITHDRAWN","CRITICAL_GRAPH_ERROR","PROVENANCE_INVALID","VALIDATION_POLICY_CHANGED","INSTITUTIONAL_INVALIDATION"}
    def __init__(self,events=None): self.events=events or EventPublisher()
    @transaction.atomic
    def execute(self,*,graph_version_id,actor,reason):
        version=CurriculumGraphVersion.objects.select_for_update().get(id=graph_version_id); graph=CurriculumGraph.objects.select_for_update().get(id=version.graph_id)
        if not (actor.is_superuser or _has_institutional_authority(actor,graph.tenant_id)): raise PermissionDenied("CURRICULUM_GRAPH_ACCESS_DENIED")
        if reason not in self.ALLOWED: raise ValidationError("Invalid invalidation reason.",code="CURRICULUM_GRAPH_INVALIDATED")
        version.status=GraphVersionStatus.INVALIDATED; version.invalidated_at=timezone.now(); version.invalidated_by=actor; version.invalidation_reason=reason
        version.save(update_fields=["status","invalidated_at","invalidated_by","invalidation_reason"])
        graph.status=GraphStatus.INVALIDATED; graph.save(update_fields=["status","updated_at"])
        transaction.on_commit(lambda: self._invalidate_mapping_runs(version.id))
        transaction.on_commit(lambda:_publish(self.events,"curriculum_graph.invalidated",{"graph_id":str(graph.id),"graph_version_id":str(version.id),"reason":reason}))
        return version

    @staticmethod
    def _invalidate_mapping_runs(graph_version_id):
        from .evidence_services import InvalidateMappingsForGraphService
        InvalidateMappingsForGraphService().execute(graph_version_id, "MAPPING_GRAPH_INVALIDATED")


class CurriculumGraphTraversalService:
    def immediate_prerequisites(self, version, node):
        return list(version.edges.filter(source_node=node,edge_type=EdgeType.REQUIRES).select_related("target_node").order_by("ordinal","target_node__stable_key"))
    def required_closure(self, version, node, maximum_depth):
        maximum_depth=max(1,min(int(maximum_depth),25)); result=[]; seen={node.id}; queue=deque([(node,0,None)])
        while queue:
            current,depth,predecessor=queue.popleft()
            if depth>=maximum_depth: continue
            edges=version.edges.filter(source_node=current,edge_type=EdgeType.REQUIRES,requirement=RequirementType.REQUIRED).select_related("target_node").order_by("ordinal","target_node__stable_key")
            for edge in edges:
                target=edge.target_node
                if target.id in seen: continue
                seen.add(target.id); result.append({"node":target,"depth":depth+1,"predecessor_id":current.id,"requirement":edge.requirement}); queue.append((target,depth+1,current.id))
        return result
    def structural_descendants(self, version, node, maximum_depth):
        maximum_depth=max(1,min(int(maximum_depth),25)); result=[]; seen={node.id}; queue=deque([(node,0)])
        while queue:
            current,depth=queue.popleft()
            if depth>=maximum_depth: continue
            edges=version.edges.filter(target_node=current,edge_type=EdgeType.PART_OF).select_related("source_node").order_by("ordinal","source_node__stable_key")
            for edge in edges:
                child=edge.source_node
                if child.id in seen: continue
                seen.add(child.id); result.append({"node":child,"depth":depth+1}); queue.append((child,depth+1))
        return result
