from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class TeachingPreparationRunStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ASSEMBLING = "ASSEMBLING", "Assembling"
    ASSEMBLY_READY = "ASSEMBLY_READY", "Assembly ready"
    PUBLISHING = "PUBLISHING", "Publishing"
    EVALUATING_READINESS = "EVALUATING_READINESS", "Evaluating readiness"
    COMPLETED = "COMPLETED", "Completed"
    FAILED = "FAILED", "Failed"
    STALE = "STALE", "Stale"
    INVALIDATED = "INVALIDATED", "Invalidated"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class TeachingPreparationManifestStatus(models.TextChoices):
    PROPOSED = "PROPOSED", "Proposed"
    READY_FOR_REVIEW = "READY_FOR_REVIEW", "Ready for review"
    APPROVED = "APPROVED", "Approved"
    PUBLISHING = "PUBLISHING", "Publishing"
    PUBLISHED = "PUBLISHED", "Published"
    READY = "READY", "Ready"
    BLOCKED = "BLOCKED", "Blocked"
    REJECTED = "REJECTED", "Rejected"
    STALE = "STALE", "Stale"
    INVALIDATED = "INVALIDATED", "Invalidated"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class NodeTeachingPackStatus(models.TextChoices):
    UNEVALUATED = "UNEVALUATED", "Unevaluated"
    ASSEMBLED = "ASSEMBLED", "Assembled"
    PARTIAL = "PARTIAL", "Partial"
    BLOCKED = "BLOCKED", "Blocked"
    CONFLICTING = "CONFLICTING", "Conflicting"
    PUBLISHED = "PUBLISHED", "Published"
    READY = "READY", "Ready"
    STALE = "STALE", "Stale"
    NOT_APPLICABLE = "NOT_APPLICABLE", "Not applicable"


class TeachingResourceRole(models.TextChoices):
    PRIMARY_EXPLANATION = "PRIMARY_EXPLANATION", "Primary explanation"
    SUPPORTING_EXPLANATION = "SUPPORTING_EXPLANATION", "Supporting explanation"
    PREREQUISITE_SUPPORT = "PREREQUISITE_SUPPORT", "Prerequisite support"
    DEFINITION = "DEFINITION", "Definition"
    WORKED_EXAMPLE = "WORKED_EXAMPLE", "Worked example"
    PROCEDURE = "PROCEDURE", "Procedure"
    PRACTICE = "PRACTICE", "Practice"
    ASSESSMENT_SUPPORT = "ASSESSMENT_SUPPORT", "Assessment support"
    REFERENCE = "REFERENCE", "Reference"
    ENRICHMENT = "ENRICHMENT", "Enrichment"
    CONFLICT_WARNING = "CONFLICT_WARNING", "Conflict warning"


class TeachingReadinessState(models.TextChoices):
    NOT_EVALUATED = "NOT_EVALUATED", "Not evaluated"
    READY = "READY", "Ready"
    PARTIAL = "PARTIAL", "Partial"
    BLOCKED = "BLOCKED", "Blocked"
    CONFLICTING = "CONFLICTING", "Conflicting"
    STALE = "STALE", "Stale"
    INVALIDATED = "INVALIDATED", "Invalidated"


class TeachingPreparationFindingSeverity(models.TextChoices):
    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    BLOCKER = "BLOCKER", "Blocker"


class TeachingPreparationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="teaching_preparation_runs")
    intent = models.ForeignKey("self_study.SelfStudyIntent", on_delete=models.PROTECT, related_name="teaching_preparation_runs")
    bridge_plan = models.ForeignKey("self_study.BridgePlan", on_delete=models.PROTECT, related_name="teaching_preparation_runs")
    graph_version = models.ForeignKey("self_study.CurriculumGraphVersion", on_delete=models.PROTECT, related_name="teaching_preparation_runs")
    coverage_evaluation = models.ForeignKey("self_study.CurriculumCoverageEvaluation", on_delete=models.PROTECT, related_name="teaching_preparation_runs")
    bridge_plan_fingerprint = models.CharField(max_length=128)
    graph_fingerprint = models.CharField(max_length=128)
    coverage_fingerprint = models.CharField(max_length=128)
    mapping_set_fingerprint = models.CharField(max_length=128)
    input_manifest = models.JSONField()
    algorithm_version = models.CharField(max_length=64)
    policy_version = models.CharField(max_length=64)
    role_policy_version = models.CharField(max_length=64)
    retrieval_schema_version = models.CharField(max_length=64)
    readiness_policy_version = models.CharField(max_length=64)
    run_fingerprint = models.CharField(max_length=128)
    status = models.CharField(max_length=24, choices=TeachingPreparationRunStatus.choices, default=TeachingPreparationRunStatus.PENDING)
    stage = models.CharField(max_length=32, default="CREATED")
    claim_token = models.UUIDField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    claimed_by = models.CharField(max_length=128, blank=True)
    requested_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="requested_teaching_preparation_runs")
    predecessor = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="successors")
    failure_code = models.CharField(max_length=96, blank=True)
    failure_detail = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "self_study_teaching_preparation_run"
        constraints = [models.UniqueConstraint(fields=["tenant", "run_fingerprint"], condition=~Q(status__in=["INVALIDATED", "SUPERSEDED"]), name="ssi_teach_run_fp_unique")]
        indexes = [models.Index(fields=["intent", "status"], name="ssi_teach_run_status_idx"), models.Index(fields=["bridge_plan", "status"], name="ssi_teach_run_plan_idx")]

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            frozen = ("tenant_id", "intent_id", "bridge_plan_id", "graph_version_id", "coverage_evaluation_id", "bridge_plan_fingerprint", "graph_fingerprint", "coverage_fingerprint", "mapping_set_fingerprint", "input_manifest", "algorithm_version", "policy_version", "role_policy_version", "retrieval_schema_version", "readiness_policy_version", "run_fingerprint")
            if old and old.status != TeachingPreparationRunStatus.PENDING and any(getattr(old, field) != getattr(self, field) for field in frozen):
                raise ValidationError("Teaching preparation inputs are immutable.", code="TEACHING_PREPARATION_INPUT_IMMUTABLE")
        return super().save(*args, **kwargs)


class TeachingPreparationManifest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.OneToOneField(TeachingPreparationRun, on_delete=models.PROTECT, related_name="manifest")
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="teaching_preparation_manifests")
    intent = models.ForeignKey("self_study.SelfStudyIntent", on_delete=models.PROTECT, related_name="teaching_preparation_manifests")
    bridge_plan = models.ForeignKey("self_study.BridgePlan", on_delete=models.PROTECT, related_name="teaching_preparation_manifests")
    graph_version = models.ForeignKey("self_study.CurriculumGraphVersion", on_delete=models.PROTECT, related_name="teaching_preparation_manifests")
    coverage_evaluation = models.ForeignKey("self_study.CurriculumCoverageEvaluation", on_delete=models.PROTECT, related_name="teaching_preparation_manifests")
    status = models.CharField(max_length=24, choices=TeachingPreparationManifestStatus.choices, default=TeachingPreparationManifestStatus.PROPOSED)
    manifest_snapshot = models.JSONField()
    manifest_fingerprint = models.CharField(max_length=128)
    pack_set_fingerprint = models.CharField(max_length=128)
    assignment_set_fingerprint = models.CharField(max_length=128)
    citation_set_fingerprint = models.CharField(max_length=128)
    retrieval_manifest_fingerprint = models.CharField(max_length=128, blank=True)
    readiness_fingerprint = models.CharField(max_length=128, blank=True)
    algorithm_version = models.CharField(max_length=64)
    policy_version = models.CharField(max_length=64)
    role_policy_version = models.CharField(max_length=64)
    approved_by = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="approved_teaching_preparations")
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_reason = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="rejected_teaching_preparations")
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    predecessor = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="successors")
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "self_study_teaching_preparation_manifest"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "manifest_fingerprint"], name="ssi_teach_manifest_fp_unique"),
            models.UniqueConstraint(fields=["tenant", "intent", "bridge_plan"], condition=Q(status="READY"), name="ssi_teach_one_ready_scope"),
        ]
        indexes = [models.Index(fields=["intent", "status"], name="ssi_teach_manifest_status_idx")]

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            frozen = ("run_id", "tenant_id", "intent_id", "bridge_plan_id", "graph_version_id", "coverage_evaluation_id", "manifest_snapshot", "manifest_fingerprint", "pack_set_fingerprint", "assignment_set_fingerprint", "citation_set_fingerprint", "algorithm_version", "policy_version", "role_policy_version")
            if old and old.manifest_fingerprint and not old.manifest_fingerprint.startswith("pending:") and any(getattr(old, field) != getattr(self, field) for field in frozen):
                raise ValidationError("Teaching preparation manifests are immutable.", code="TEACHING_PREPARATION_IMMUTABLE")
        return super().save(*args, **kwargs)


class NodeTeachingPack(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manifest = models.ForeignKey(TeachingPreparationManifest, on_delete=models.PROTECT, related_name="node_packs")
    bridge_node = models.ForeignKey("self_study.BridgePlanNode", on_delete=models.PROTECT, related_name="teaching_packs")
    graph_node = models.ForeignKey("self_study.CurriculumNode", on_delete=models.PROTECT, related_name="teaching_packs")
    node_type = models.CharField(max_length=32)
    ordinal = models.PositiveIntegerField()
    topological_layer = models.PositiveIntegerField()
    bridge_disposition = models.CharField(max_length=32)
    material_feasibility = models.CharField(max_length=24)
    coverage_state = models.CharField(max_length=16)
    status = models.CharField(max_length=24, choices=NodeTeachingPackStatus.choices, default=NodeTeachingPackStatus.UNEVALUATED)
    role_policy_snapshot = models.JSONField(default=dict)
    required_role_count = models.PositiveIntegerField(default=0)
    satisfied_role_count = models.PositiveIntegerField(default=0)
    assignment_count = models.PositiveIntegerField(default=0)
    distinct_source_count = models.PositiveIntegerField(default=0)
    duplicate_cluster_count = models.PositiveIntegerField(default=0)
    blocker_count = models.PositiveIntegerField(default=0)
    pack_fingerprint = models.CharField(max_length=128)

    class Meta:
        db_table = "self_study_node_teaching_pack"
        constraints = [models.UniqueConstraint(fields=["manifest", "bridge_node"], name="ssi_teach_pack_node_unique"), models.UniqueConstraint(fields=["manifest", "pack_fingerprint"], name="ssi_teach_pack_fp_unique")]
        indexes = [models.Index(fields=["manifest", "topological_layer", "ordinal"], name="ssi_teach_pack_order_idx")]

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            frozen = ("manifest_id", "bridge_node_id", "graph_node_id", "node_type", "ordinal", "topological_layer", "bridge_disposition", "material_feasibility", "coverage_state", "role_policy_snapshot", "required_role_count", "assignment_count", "distinct_source_count", "duplicate_cluster_count", "pack_fingerprint")
            if old and any(getattr(old, field) != getattr(self, field) for field in frozen):
                raise ValidationError("Node teaching pack authority is immutable.", code="TEACHING_PREPARATION_IMMUTABLE")
        return super().save(*args, **kwargs)


class TeachingPackResource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack = models.ForeignKey(NodeTeachingPack, on_delete=models.PROTECT, related_name="resources")
    accepted_mapping = models.ForeignKey("self_study.CurriculumEvidenceMapping", on_delete=models.PROTECT, related_name="teaching_assignments")
    evidence_unit = models.ForeignKey("self_study.ContentEvidenceUnit", on_delete=models.PROTECT, related_name="teaching_assignments")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="self_study_teaching_assignments")
    source_input = models.ForeignKey("self_study.EvidenceMappingRunResource", on_delete=models.PROTECT, related_name="teaching_assignments")
    source_block = models.ForeignKey("content_processing.ExtractedBlock", on_delete=models.PROTECT, related_name="teaching_assignments")
    classification = models.CharField(max_length=32)
    role = models.CharField(max_length=32, choices=TeachingResourceRole.choices)
    rank = models.PositiveSmallIntegerField()
    diversity_key = models.CharField(max_length=128, blank=True)
    duplicate_cluster = models.CharField(max_length=128, blank=True)
    licence_disposition = models.CharField(max_length=32)
    safety_disposition = models.CharField(max_length=32)
    citation_snapshot = models.JSONField(default=dict)
    rationale_codes = models.JSONField(default=list)
    policy_version = models.CharField(max_length=64)
    assignment_fingerprint = models.CharField(max_length=128)

    class Meta:
        db_table = "self_study_teaching_pack_resource"
        constraints = [
            models.UniqueConstraint(fields=["pack", "accepted_mapping"], name="ssi_teach_asg_map_unique"),
            models.UniqueConstraint(fields=["pack", "assignment_fingerprint"], name="ssi_teach_assignment_fp_unique"),
        ]
        indexes = [models.Index(fields=["pack", "role", "rank"], name="ssi_teach_assignment_role_idx"), models.Index(fields=["resource", "role"], name="ssi_teach_asg_resource_idx")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Teaching pack resources are immutable.", code="TEACHING_PREPARATION_IMMUTABLE")
        return super().save(*args, **kwargs)


class TeachingRetrievalManifest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manifest = models.OneToOneField(TeachingPreparationManifest, on_delete=models.PROTECT, related_name="retrieval_manifest")
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="teaching_retrieval_manifests")
    bridge_plan = models.ForeignKey("self_study.BridgePlan", on_delete=models.PROTECT, related_name="teaching_retrieval_manifests")
    status = models.CharField(max_length=24, default="PENDING")
    expected_assignment_count = models.PositiveIntegerField(default=0)
    published_assignment_count = models.PositiveIntegerField(default=0)
    expected_assignment_identities = models.JSONField(default=list)
    published_assignment_identities = models.JSONField(default=list)
    metadata_filters = models.JSONField(default=dict)
    manifest_fingerprint = models.CharField(max_length=128)
    verification_fingerprint = models.CharField(max_length=128, blank=True)
    retrieval_schema_version = models.CharField(max_length=64)
    index_version = models.CharField(max_length=64, default="self-study-teaching-retrieval-v1")
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_teaching_retrieval_manifest"
        constraints = [models.UniqueConstraint(fields=["tenant", "manifest_fingerprint"], name="ssi_teach_retrieval_fp_unique")]
        indexes = [models.Index(fields=["bridge_plan", "status"], name="ssi_teach_retrieval_status_idx")]


class TeachingReadinessEvaluation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manifest = models.ForeignKey(TeachingPreparationManifest, on_delete=models.PROTECT, related_name="readiness_evaluations")
    retrieval_manifest = models.ForeignKey(TeachingRetrievalManifest, on_delete=models.PROTECT, related_name="readiness_evaluations")
    state = models.CharField(max_length=24, choices=TeachingReadinessState.choices)
    node_results = models.JSONField(default=list)
    blocker_count = models.PositiveIntegerField(default=0)
    warning_count = models.PositiveIntegerField(default=0)
    evaluation_fingerprint = models.CharField(max_length=128, unique=True)
    policy_version = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_teaching_readiness_evaluation"
        indexes = [models.Index(fields=["manifest", "state"], name="ssi_teach_ready_state_idx")]


class TeachingReadinessFinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manifest = models.ForeignKey(TeachingPreparationManifest, on_delete=models.PROTECT, related_name="findings")
    pack = models.ForeignKey(NodeTeachingPack, null=True, blank=True, on_delete=models.PROTECT, related_name="findings")
    code = models.CharField(max_length=96)
    severity = models.CharField(max_length=16, choices=TeachingPreparationFindingSeverity.choices)
    blocking = models.BooleanField(default=False)
    scope = models.CharField(max_length=32)
    affected_identities = models.JSONField(default=list)
    details = models.JSONField(default=dict)
    policy_version = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_teaching_readiness_finding"
        indexes = [models.Index(fields=["manifest", "blocking", "severity"], name="ssi_teach_finding_idx"), models.Index(fields=["code"], name="ssi_teach_finding_code_idx")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Teaching readiness findings are immutable.", code="TEACHING_PREPARATION_IMMUTABLE")
        return super().save(*args, **kwargs)
