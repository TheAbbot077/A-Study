from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


def _ensure_graph_version_mutable(graph_version_id):
    status = CurriculumGraphVersion.objects.only("status").get(id=graph_version_id).status
    if status in {GraphVersionStatus.PUBLISHED, GraphVersionStatus.SUPERSEDED, GraphVersionStatus.INVALIDATED}:
        raise ValidationError("Published graph content is immutable.", code="CURRICULUM_GRAPH_FINGERPRINT_CHANGED")


class ImmutableGraphContentMixin:
    def save(self, *args, **kwargs):
        if self.graph_version_id:
            _ensure_graph_version_mutable(self.graph_version_id)
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        _ensure_graph_version_mutable(self.graph_version_id)
        return super().delete(*args, **kwargs)


class GraphStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    BUILDING = "BUILDING", "Building"
    VALIDATING = "VALIDATING", "Validating"
    READY_FOR_PUBLICATION = "READY_FOR_PUBLICATION", "Ready for publication"
    PUBLISHED = "PUBLISHED", "Published"
    BLOCKED = "BLOCKED", "Blocked"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    INVALIDATED = "INVALIDATED", "Invalidated"


class GraphVersionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    BUILDING = "BUILDING", "Building"
    VALIDATING = "VALIDATING", "Validating"
    VALID = "VALID", "Valid"
    INVALID = "INVALID", "Invalid"
    PUBLISHED = "PUBLISHED", "Published"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    INVALIDATED = "INVALIDATED", "Invalidated"


class ConstructionMethod(models.TextChoices):
    STRUCTURED_IMPORT = "STRUCTURED_IMPORT", "Structured import"
    GOVERNED_EXTRACTION = "GOVERNED_EXTRACTION", "Governed extraction"
    CURATED_AUTHORING = "CURATED_AUTHORING", "Curated authoring"
    COMPOSITE_ASSEMBLY = "COMPOSITE_ASSEMBLY", "Composite assembly"


class CurriculumGraph(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="curriculum_graphs")
    intent = models.ForeignKey("self_study.SelfStudyIntent", on_delete=models.PROTECT, related_name="curriculum_graphs")
    selection_decision = models.OneToOneField(
        "self_study.CurriculumSelectionDecision", null=True, blank=True, on_delete=models.PROTECT, related_name="curriculum_graph"
    )
    composite_proposal = models.OneToOneField(
        "self_study.CompositeCurriculumProposal", null=True, blank=True, on_delete=models.PROTECT, related_name="curriculum_graph"
    )
    status = models.CharField(max_length=32, choices=GraphStatus.choices, default=GraphStatus.DRAFT)
    current_version = models.OneToOneField(
        "self_study.CurriculumGraphVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "self_study_curriculum_graph"
        constraints = [
            models.CheckConstraint(
                condition=(Q(selection_decision__isnull=False, composite_proposal__isnull=True) | Q(selection_decision__isnull=True, composite_proposal__isnull=False)),
                name="self_study_graph_one_authoritative_source",
            )
        ]


class CurriculumGraphVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    graph = models.ForeignKey(CurriculumGraph, on_delete=models.PROTECT, related_name="versions")
    version_number = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=GraphVersionStatus.choices, default=GraphVersionStatus.DRAFT)
    source_selection_fingerprint = models.CharField(max_length=128)
    graph_fingerprint = models.CharField(max_length=128, blank=True)
    builder_algorithm_version = models.CharField(max_length=32)
    validation_algorithm_version = models.CharField(max_length=32)
    stable_key_algorithm_version = models.CharField(max_length=32)
    source_language = models.CharField(max_length=16)
    construction_method = models.CharField(max_length=32, choices=ConstructionMethod.choices)
    node_count = models.PositiveIntegerField(default=0)
    edge_count = models.PositiveIntegerField(default=0)
    root_count = models.PositiveIntegerField(default=0)
    outcome_count = models.PositiveIntegerField(default=0)
    validation_summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="created_curriculum_graph_versions")
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="published_curriculum_graph_versions"
    )
    supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by")
    invalidated_at = models.DateTimeField(null=True, blank=True)
    invalidated_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="invalidated_curriculum_graph_versions"
    )
    invalidation_reason = models.CharField(max_length=64, blank=True)

    class Meta:
        db_table = "self_study_curriculum_graph_version"
        constraints = [models.UniqueConstraint(fields=["graph", "version_number"], name="self_study_graph_version_unique")]
        indexes = [models.Index(fields=["graph", "status"], name="ssi_graph_version_status_idx")]

    def save(self, *args, **kwargs):
        if self.pk:
            prior = type(self).objects.filter(pk=self.pk).first()
            if prior and prior.status in {GraphVersionStatus.PUBLISHED, GraphVersionStatus.SUPERSEDED, GraphVersionStatus.INVALIDATED}:
                immutable = [
                    "source_selection_fingerprint", "graph_fingerprint", "builder_algorithm_version",
                    "validation_algorithm_version", "stable_key_algorithm_version", "source_language",
                    "construction_method", "node_count", "edge_count", "root_count", "outcome_count",
                ]
                if any(getattr(prior, field) != getattr(self, field) for field in immutable):
                    raise ValidationError("Published graph versions are immutable.", code="CURRICULUM_GRAPH_INVALIDATED")
        return super().save(*args, **kwargs)


class NodeType(models.TextChoices):
    CURRICULUM_ROOT = "CURRICULUM_ROOT", "Curriculum root"
    STAGE = "STAGE", "Stage"
    OUTCOME = "OUTCOME", "Outcome"
    MODULE = "MODULE", "Module"
    TOPIC = "TOPIC", "Topic"
    CONCEPT = "CONCEPT", "Concept"
    COMPETENCY = "COMPETENCY", "Competency"
    ASSESSMENT_OBJECTIVE = "ASSESSMENT_OBJECTIVE", "Assessment objective"
    EXTERNAL_PREREQUISITE = "EXTERNAL_PREREQUISITE", "External prerequisite"


class ExternalPrerequisiteStatus(models.TextChoices):
    UNRESOLVED = "UNRESOLVED", "Unresolved"
    MATCHED_TO_REGISTERED_NODE = "MATCHED_TO_REGISTERED_NODE", "Matched to registered node"
    REQUIRES_CURRICULUM_EXTENSION = "REQUIRES_CURRICULUM_EXTENSION", "Requires curriculum extension"


class CurriculumNode(ImmutableGraphContentMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    graph_version = models.ForeignKey(CurriculumGraphVersion, on_delete=models.CASCADE, related_name="nodes")
    stable_key = models.CharField(max_length=128)
    node_type = models.CharField(max_length=32, choices=NodeType.choices)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    ordinal = models.PositiveIntegerField()
    depth = models.PositiveIntegerField(default=0)
    source_curriculum_version = models.ForeignKey("self_study.CurriculumVersion", on_delete=models.PROTECT, related_name="graph_nodes")
    authority_namespace = models.CharField(max_length=255)
    external_identifier = models.CharField(max_length=255, blank=True)
    external_prerequisite_status = models.CharField(max_length=40, choices=ExternalPrerequisiteStatus.choices, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_curriculum_node"
        constraints = [
            models.UniqueConstraint(fields=["graph_version", "stable_key"], name="self_study_graph_node_key_unique"),
            models.UniqueConstraint(fields=["graph_version", "authority_namespace", "external_identifier"], condition=~Q(external_identifier=""), name="self_study_graph_external_id_unique"),
        ]
        indexes = [
            models.Index(fields=["graph_version", "node_type"], name="ssi_graph_node_type_idx"),
            models.Index(fields=["graph_version", "ordinal"], name="ssi_graph_node_order_idx"),
        ]


class EdgeType(models.TextChoices):
    PART_OF = "PART_OF", "Part of"
    REQUIRES = "REQUIRES", "Requires"
    SATISFIES = "SATISFIES", "Satisfies"
    ASSESSED_BY = "ASSESSED_BY", "Assessed by"
    PRECEDES = "PRECEDES", "Precedes"
    EQUIVALENT_TO = "EQUIVALENT_TO", "Equivalent to"
    SPECIALIZES = "SPECIALIZES", "Specializes"
    BRIDGES_TO = "BRIDGES_TO", "Bridges to"
    CONFLICTS_WITH = "CONFLICTS_WITH", "Conflicts with"


class RequirementType(models.TextChoices):
    REQUIRED = "REQUIRED", "Required"
    RECOMMENDED = "RECOMMENDED", "Recommended"
    OPTIONAL = "OPTIONAL", "Optional"


class CurriculumEdge(ImmutableGraphContentMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    graph_version = models.ForeignKey(CurriculumGraphVersion, on_delete=models.CASCADE, related_name="edges")
    stable_key = models.CharField(max_length=128)
    edge_type = models.CharField(max_length=24, choices=EdgeType.choices)
    source_node = models.ForeignKey(CurriculumNode, on_delete=models.CASCADE, related_name="outgoing_edges")
    target_node = models.ForeignKey(CurriculumNode, on_delete=models.CASCADE, related_name="incoming_edges")
    ordinal = models.PositiveIntegerField()
    requirement = models.CharField(max_length=16, choices=RequirementType.choices, blank=True)
    strength = models.DecimalField(max_digits=5, decimal_places=4, default=1)
    source_curriculum_version = models.ForeignKey("self_study.CurriculumVersion", on_delete=models.PROTECT, related_name="graph_edges")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_curriculum_edge"
        constraints = [
            models.UniqueConstraint(fields=["graph_version", "stable_key"], name="self_study_graph_edge_key_unique"),
            models.CheckConstraint(condition=~Q(source_node=models.F("target_node")), name="self_study_graph_no_self_edge"),
        ]
        indexes = [
            models.Index(fields=["graph_version", "edge_type"], name="ssi_graph_edge_type_idx"),
            models.Index(fields=["graph_version", "source_node"], name="ssi_graph_edge_source_idx"),
            models.Index(fields=["graph_version", "target_node"], name="ssi_graph_edge_target_idx"),
        ]


class CitationType(models.TextChoices):
    EXPLICIT = "EXPLICIT", "Explicit"
    STRUCTURAL = "STRUCTURAL", "Structural"
    DERIVED = "DERIVED", "Derived"
    CURATED = "CURATED", "Curated"
    COMPOSITE_ALIGNMENT = "COMPOSITE_ALIGNMENT", "Composite alignment"


class CurriculumGraphCitation(ImmutableGraphContentMixin, models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    graph_version = models.ForeignKey(CurriculumGraphVersion, on_delete=models.CASCADE, related_name="citations")
    node = models.ForeignKey(CurriculumNode, null=True, blank=True, on_delete=models.CASCADE, related_name="citations")
    edge = models.ForeignKey(CurriculumEdge, null=True, blank=True, on_delete=models.CASCADE, related_name="citations")
    curriculum_version = models.ForeignKey("self_study.CurriculumVersion", on_delete=models.PROTECT, related_name="graph_citations")
    source_document_id = models.UUIDField(null=True, blank=True)
    source_uri = models.URLField(max_length=2048)
    source_locator = models.JSONField(default=dict)
    normalized_excerpt = models.TextField(blank=True)
    source_language = models.CharField(max_length=16)
    citation_type = models.CharField(max_length=32, choices=CitationType.choices)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    rationale = models.TextField(blank=True)
    builder_algorithm_version = models.CharField(max_length=32)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_curriculum_graph_citation"
        constraints = [models.CheckConstraint(condition=(Q(node__isnull=False, edge__isnull=True) | Q(node__isnull=True, edge__isnull=False)), name="self_study_graph_citation_one_target")]
        indexes = [models.Index(fields=["graph_version", "citation_type"], name="ssi_graph_citation_type_idx")]


class CurriculumGraphSpecificationRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    graph_version = models.OneToOneField(CurriculumGraphVersion, on_delete=models.PROTECT, related_name="specification")
    payload = models.JSONField()
    specification_checksum = models.CharField(max_length=128)
    submitted_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="curriculum_graph_specifications")
    producer = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_curriculum_graph_specification"

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Graph specifications are immutable.", code="CURRICULUM_GRAPH_SPECIFICATION_INVALID")
        return super().save(*args, **kwargs)


class ValidationRunStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    RUNNING = "RUNNING", "Running"
    PASSED = "PASSED", "Passed"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"


class CurriculumGraphValidationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    graph_version = models.ForeignKey(CurriculumGraphVersion, on_delete=models.PROTECT, related_name="validation_runs")
    status = models.CharField(max_length=16, choices=ValidationRunStatus.choices, default=ValidationRunStatus.PENDING)
    algorithm_version = models.CharField(max_length=32)
    graph_fingerprint = models.CharField(max_length=128)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_curriculum_graph_validation_run"
        constraints = [models.UniqueConstraint(fields=["graph_version", "graph_fingerprint", "algorithm_version"], name="self_study_graph_validation_unique")]
        indexes = [models.Index(fields=["graph_version", "status"], name="ssi_graph_validation_idx")]


class FindingSeverity(models.TextChoices):
    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    BLOCKER = "BLOCKER", "Blocker"


class CurriculumGraphFinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    validation_run = models.ForeignKey(CurriculumGraphValidationRun, on_delete=models.CASCADE, related_name="findings")
    code = models.CharField(max_length=64)
    severity = models.CharField(max_length=16, choices=FindingSeverity.choices)
    node = models.ForeignKey(CurriculumNode, null=True, blank=True, on_delete=models.PROTECT, related_name="validation_findings")
    edge = models.ForeignKey(CurriculumEdge, null=True, blank=True, on_delete=models.PROTECT, related_name="validation_findings")
    related_node = models.ForeignKey(CurriculumNode, null=True, blank=True, on_delete=models.PROTECT, related_name="related_validation_findings")
    message = models.CharField(max_length=500)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="resolved_graph_findings")
    resolution_note = models.TextField(blank=True)

    class Meta:
        db_table = "self_study_curriculum_graph_finding"
        indexes = [models.Index(fields=["validation_run", "severity"], name="ssi_graph_finding_idx")]
