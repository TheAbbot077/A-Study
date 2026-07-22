from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class BridgePlanningRunStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PLANNING = "PLANNING", "Planning"
    PLAN_READY = "PLAN_READY", "Plan ready"
    FAILED = "FAILED", "Failed"
    STALE = "STALE", "Stale"
    INVALIDATED = "INVALIDATED", "Invalidated"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class BridgePlanStatus(models.TextChoices):
    PROPOSED = "PROPOSED", "Proposed"
    READY_FOR_REVIEW = "READY_FOR_REVIEW", "Ready for review"
    APPROVED = "APPROVED", "Approved"
    ACTIVE = "ACTIVE", "Active"
    BLOCKED = "BLOCKED", "Blocked"
    REJECTED = "REJECTED", "Rejected"
    STALE = "STALE", "Stale"
    INVALIDATED = "INVALIDATED", "Invalidated"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class LearnerPathDisposition(models.TextChoices):
    ENTRY = "ENTRY", "Entry"
    PREREQUISITE_REQUIRED = "PREREQUISITE_REQUIRED", "Prerequisite required"
    TARGET_REQUIRED = "TARGET_REQUIRED", "Target required"
    REINFORCEMENT = "REINFORCEMENT", "Reinforcement"
    DIAGNOSTIC_REVIEW = "DIAGNOSTIC_REVIEW", "Diagnostic review"
    DEFERRED = "DEFERRED", "Deferred"
    NOT_APPLICABLE = "NOT_APPLICABLE", "Not applicable"


class BridgeRequirementType(models.TextChoices):
    MANDATORY = "MANDATORY", "Mandatory"
    CONDITIONAL = "CONDITIONAL", "Conditional"
    OPTIONAL = "OPTIONAL", "Optional"
    REINFORCEMENT_ONLY = "REINFORCEMENT_ONLY", "Reinforcement only"


class MaterialFeasibility(models.TextChoices):
    FEASIBLE = "FEASIBLE", "Feasible"
    PARTIALLY_FEASIBLE = "PARTIALLY_FEASIBLE", "Partially feasible"
    MATERIAL_MISSING = "MATERIAL_MISSING", "Material missing"
    MATERIAL_CONFLICTING = "MATERIAL_CONFLICTING", "Material conflicting"
    EVIDENCE_STALE = "EVIDENCE_STALE", "Evidence stale"
    POLICY_BLOCKED = "POLICY_BLOCKED", "Policy blocked"
    NOT_APPLICABLE = "NOT_APPLICABLE", "Not applicable"


class BridgeFindingSeverity(models.TextChoices):
    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    BLOCKER = "BLOCKER", "Blocker"


class BridgePlanningRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="bridge_planning_runs")
    intent = models.ForeignKey("self_study.SelfStudyIntent", on_delete=models.PROTECT, related_name="bridge_planning_runs")
    selection_decision = models.ForeignKey("self_study.CurriculumSelectionDecision", null=True, blank=True, on_delete=models.PROTECT, related_name="bridge_planning_runs")
    graph_version = models.ForeignKey("self_study.CurriculumGraphVersion", on_delete=models.PROTECT, related_name="bridge_planning_runs")
    diagnostic_profile = models.ForeignKey("self_study.DiagnosticPlacementProfile", null=True, blank=True, on_delete=models.PROTECT, related_name="bridge_planning_runs")
    coverage_evaluation = models.ForeignKey("self_study.CurriculumCoverageEvaluation", null=True, blank=True, on_delete=models.PROTECT, related_name="bridge_planning_runs")
    target_manifest = models.JSONField()
    input_manifest = models.JSONField()
    algorithm_version = models.CharField(max_length=64)
    policy_version = models.CharField(max_length=64)
    approval_policy_version = models.CharField(max_length=64)
    applicability_version = models.CharField(max_length=64)
    run_fingerprint = models.CharField(max_length=128)
    status = models.CharField(max_length=16, choices=BridgePlanningRunStatus.choices, default=BridgePlanningRunStatus.PENDING)
    stage = models.CharField(max_length=32, default="CREATED")
    claim_token = models.UUIDField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    claimed_by = models.CharField(max_length=128, blank=True)
    requested_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="requested_bridge_planning_runs")
    predecessor = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="successors")
    failure_code = models.CharField(max_length=96, blank=True)
    failure_detail = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "self_study_bridge_planning_run"
        constraints = [models.UniqueConstraint(fields=["tenant", "run_fingerprint"], condition=~Q(status__in=["INVALIDATED", "SUPERSEDED"]), name="ssi_bridge_run_fp_unique")]
        indexes = [models.Index(fields=["intent", "status"], name="ssi_bridge_run_status_idx"), models.Index(fields=["graph_version", "status"], name="ssi_bridge_run_graph_idx")]

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            frozen = ("tenant_id", "intent_id", "selection_decision_id", "graph_version_id", "diagnostic_profile_id", "coverage_evaluation_id", "target_manifest", "input_manifest", "algorithm_version", "policy_version", "approval_policy_version", "applicability_version", "run_fingerprint")
            if old and old.status != BridgePlanningRunStatus.PENDING and any(getattr(old, field) != getattr(self, field) for field in frozen):
                raise ValidationError("Bridge planning inputs are immutable.", code="BRIDGE_INPUT_MANIFEST_INVALID")
        return super().save(*args, **kwargs)


class BridgePlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.OneToOneField(BridgePlanningRun, on_delete=models.PROTECT, related_name="plan")
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="bridge_plans")
    intent = models.ForeignKey("self_study.SelfStudyIntent", on_delete=models.PROTECT, related_name="bridge_plans")
    graph_version = models.ForeignKey("self_study.CurriculumGraphVersion", on_delete=models.PROTECT, related_name="bridge_plans")
    target_set_snapshot = models.JSONField()
    target_set_fingerprint = models.CharField(max_length=128)
    node_set_fingerprint = models.CharField(max_length=128)
    dependency_set_fingerprint = models.CharField(max_length=128)
    blocker_set_fingerprint = models.CharField(max_length=128)
    plan_fingerprint = models.CharField(max_length=128)
    algorithm_version = models.CharField(max_length=64)
    policy_version = models.CharField(max_length=64)
    status = models.CharField(max_length=24, choices=BridgePlanStatus.choices, default=BridgePlanStatus.PROPOSED)
    generated_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="approved_bridge_plans")
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_reason = models.TextField(blank=True)
    activated_by = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="activated_bridge_plans")
    activated_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="rejected_bridge_plans")
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    predecessor = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="successors")
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "self_study_bridge_plan"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "plan_fingerprint"], name="ssi_bridge_plan_fp_unique"),
            models.UniqueConstraint(fields=["tenant", "intent", "target_set_fingerprint"], condition=Q(status="ACTIVE"), name="ssi_bridge_one_active_scope"),
        ]
        indexes = [models.Index(fields=["intent", "status"], name="ssi_bridge_plan_status_idx")]

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            frozen = ("run_id", "tenant_id", "intent_id", "graph_version_id", "target_set_snapshot", "target_set_fingerprint", "node_set_fingerprint", "dependency_set_fingerprint", "blocker_set_fingerprint", "plan_fingerprint", "algorithm_version", "policy_version")
            if old and any(getattr(old, field) != getattr(self, field) for field in frozen):
                raise ValidationError("Generated bridge plans are immutable.", code="BRIDGE_PLAN_IMMUTABLE")
        return super().save(*args, **kwargs)


class BridgePlanNode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BridgePlan, on_delete=models.PROTECT, related_name="nodes")
    graph_node = models.ForeignKey("self_study.CurriculumNode", on_delete=models.PROTECT, related_name="bridge_plan_nodes")
    node_type = models.CharField(max_length=32)
    ordinal = models.PositiveIntegerField()
    topological_layer = models.PositiveIntegerField()
    learner_disposition = models.CharField(max_length=32, choices=LearnerPathDisposition.choices)
    requirement_type = models.CharField(max_length=24, choices=BridgeRequirementType.choices)
    inclusion_rationale = models.JSONField(default=list)
    placement_band = models.CharField(max_length=32)
    coverage = models.ForeignKey("self_study.CurriculumNodeCoverage", null=True, blank=True, on_delete=models.PROTECT, related_name="bridge_plan_nodes")
    coverage_state = models.CharField(max_length=16)
    material_feasibility = models.CharField(max_length=24, choices=MaterialFeasibility.choices)
    is_target = models.BooleanField(default=False)
    is_entry = models.BooleanField(default=False)
    is_required = models.BooleanField(default=True)
    blocker_count = models.PositiveIntegerField(default=0)
    dependency_count = models.PositiveIntegerField(default=0)
    coverage_citations = models.JSONField(default=list)
    fingerprint = models.CharField(max_length=128)

    class Meta:
        db_table = "self_study_bridge_plan_node"
        constraints = [models.UniqueConstraint(fields=["plan", "graph_node"], name="ssi_bridge_plan_node_unique"), models.UniqueConstraint(fields=["plan", "fingerprint"], name="ssi_bridge_node_fp_unique")]
        indexes = [models.Index(fields=["plan", "topological_layer", "ordinal"], name="ssi_bridge_node_order_idx")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Bridge plan nodes are immutable.", code="BRIDGE_PLAN_IMMUTABLE")
        return super().save(*args, **kwargs)


class BridgePlanDependency(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BridgePlan, on_delete=models.PROTECT, related_name="dependencies")
    predecessor_node = models.ForeignKey(BridgePlanNode, on_delete=models.PROTECT, related_name="outgoing_dependencies")
    successor_node = models.ForeignKey(BridgePlanNode, on_delete=models.PROTECT, related_name="incoming_dependencies")
    graph_edge = models.ForeignKey("self_study.CurriculumEdge", on_delete=models.PROTECT, related_name="bridge_dependencies")
    edge_type = models.CharField(max_length=24)
    requirement_type = models.CharField(max_length=24, choices=BridgeRequirementType.choices)
    affects_ordering = models.BooleanField(default=True)
    rationale = models.JSONField(default=list)
    fingerprint = models.CharField(max_length=128)

    class Meta:
        db_table = "self_study_bridge_plan_dependency"
        constraints = [models.UniqueConstraint(fields=["plan", "graph_edge"], name="ssi_bridge_dependency_edge_unique"), models.UniqueConstraint(fields=["plan", "fingerprint"], name="ssi_bridge_dependency_fp_unique")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Bridge plan dependencies are immutable.", code="BRIDGE_PLAN_IMMUTABLE")
        return super().save(*args, **kwargs)


class BridgePlanFinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plan = models.ForeignKey(BridgePlan, on_delete=models.PROTECT, related_name="findings")
    code = models.CharField(max_length=96)
    severity = models.CharField(max_length=16, choices=BridgeFindingSeverity.choices)
    blocking = models.BooleanField(default=False)
    scope = models.CharField(max_length=32)
    affected_identities = models.JSONField(default=list)
    details = models.JSONField(default=dict)
    algorithm_version = models.CharField(max_length=64)
    policy_version = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_bridge_plan_finding"
        indexes = [models.Index(fields=["plan", "blocking", "severity"], name="ssi_bridge_finding_idx")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Bridge plan findings are immutable.", code="BRIDGE_PLAN_IMMUTABLE")
        return super().save(*args, **kwargs)
