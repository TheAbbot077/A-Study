from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models


class TeachingOrchestrationRunStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    PREPARING_CONTEXT = "PREPARING_CONTEXT", "Preparing context"
    GENERATING_TURN = "GENERATING_TURN", "Generating turn"
    AWAITING_LEARNER = "AWAITING_LEARNER", "Awaiting learner"
    CAPTURING_EVIDENCE = "CAPTURING_EVIDENCE", "Capturing evidence"
    TRANSITIONING = "TRANSITIONING", "Transitioning"
    COMPLETED = "COMPLETED", "Completed"
    PAUSED = "PAUSED", "Paused"
    BLOCKED = "BLOCKED", "Blocked"
    STALE = "STALE", "Stale"
    INVALIDATED = "INVALIDATED", "Invalidated"
    FAILED = "FAILED", "Failed"


class SelfStudyTeachingSessionState(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    AWAITING_LEARNER = "AWAITING_LEARNER", "Awaiting learner"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE", "Awaiting evidence"
    NODE_COMPLETE = "NODE_COMPLETE", "Node complete"
    BLOCKED = "BLOCKED", "Blocked"
    STALE = "STALE", "Stale"
    INVALIDATED = "INVALIDATED", "Invalidated"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class TeachingSessionNodeState(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACTIVE = "ACTIVE", "Active"
    PAUSED = "PAUSED", "Paused"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE", "Awaiting evidence"
    NODE_COMPLETE = "NODE_COMPLETE", "Node complete"
    BLOCKED = "BLOCKED", "Blocked"
    STALE = "STALE", "Stale"
    SKIPPED_BY_POLICY = "SKIPPED_BY_POLICY", "Skipped by policy"
    CANCELLED = "CANCELLED", "Cancelled"


class TeachingTurnActor(models.TextChoices):
    LEARNER = "LEARNER", "Learner"
    ABBOT = "ABBOT", "Abbot"
    SYSTEM = "SYSTEM", "System"


class TeachingTurnAction(models.TextChoices):
    INTRODUCE = "INTRODUCE", "Introduce"
    EXPLAIN = "EXPLAIN", "Explain"
    ILLUSTRATE = "ILLUSTRATE", "Illustrate"
    ASK = "ASK", "Ask"
    PRACTICE = "PRACTICE", "Practice"
    CHECK_UNDERSTANDING = "CHECK_UNDERSTANDING", "Check understanding"
    PROVIDE_FEEDBACK = "PROVIDE_FEEDBACK", "Provide feedback"
    REFLECT = "REFLECT", "Reflect"
    RECAP = "RECAP", "Recap"
    PAUSE = "PAUSE", "Pause"
    REQUEST_REVIEW = "REQUEST_REVIEW", "Request review"
    REQUEST_EVALUATION = "REQUEST_EVALUATION", "Request evaluation"


class TeachingSafetyStatus(models.TextChoices):
    SAFE = "SAFE", "Safe"
    BLOCKED = "BLOCKED", "Blocked"
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"


class TeachingTransitionType(models.TextChoices):
    START = "START", "Start"
    PAUSE = "PAUSE", "Pause"
    RESUME = "RESUME", "Resume"
    REVISIT = "REVISIT", "Revisit"
    ADVANCE = "ADVANCE", "Advance"
    REQUEST_EVIDENCE = "REQUEST_EVIDENCE", "Request evidence"
    COMPLETE_NODE = "COMPLETE_NODE", "Complete node"
    BLOCK = "BLOCK", "Block"
    STALE = "STALE", "Stale"
    INVALIDATE = "INVALIDATE", "Invalidate"
    CANCEL = "CANCEL", "Cancel"


class TeachingFindingSeverity(models.TextChoices):
    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    BLOCKER = "BLOCKER", "Blocker"


class SelfStudyTeachingSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="self_study_teaching_sessions")
    learner = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="self_study_teaching_sessions")
    intent = models.ForeignKey("self_study.SelfStudyIntent", on_delete=models.PROTECT, related_name="teaching_sessions")
    bridge_plan = models.ForeignKey("self_study.BridgePlan", on_delete=models.PROTECT, related_name="teaching_sessions")
    preparation_manifest = models.ForeignKey("self_study.TeachingPreparationManifest", on_delete=models.PROTECT, related_name="teaching_sessions")
    current_session_node = models.ForeignKey("self_study.TeachingSessionNode", null=True, blank=True, on_delete=models.PROTECT, related_name="current_for_sessions")
    state = models.CharField(max_length=24, choices=SelfStudyTeachingSessionState.choices, default=SelfStudyTeachingSessionState.PENDING)
    session_fingerprint = models.CharField(max_length=128)
    privacy_policy_version = models.CharField(max_length=64)
    disclosure_policy_version = models.CharField(max_length=64)
    current_turn_sequence = models.PositiveIntegerField(default=0)
    cancellation_reason = models.CharField(max_length=96, blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True)
    version = models.PositiveIntegerField(default=1)
    started_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "self_study_teaching_session"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "session_fingerprint"], name="ssi_tsess_fp_unique"),
            models.UniqueConstraint(fields=["intent", "idempotency_key"], name="ssi_tsess_idem_unique"),
        ]
        indexes = [
            models.Index(fields=["learner", "state"], name="ssi_tsess_learner_idx"),
            models.Index(fields=["intent", "state"], name="ssi_tsess_intent_idx"),
        ]


class TeachingSessionNode(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(SelfStudyTeachingSession, on_delete=models.PROTECT, related_name="nodes")
    bridge_node = models.ForeignKey("self_study.BridgePlanNode", on_delete=models.PROTECT, related_name="teaching_session_nodes")
    graph_node = models.ForeignKey("self_study.CurriculumNode", on_delete=models.PROTECT, related_name="teaching_session_nodes")
    teaching_pack = models.ForeignKey("self_study.NodeTeachingPack", on_delete=models.PROTECT, related_name="teaching_session_nodes")
    graph_version = models.ForeignKey("self_study.CurriculumGraphVersion", on_delete=models.PROTECT, related_name="teaching_session_nodes")
    plan_ordinal = models.PositiveIntegerField()
    topological_layer = models.PositiveIntegerField()
    bridge_disposition = models.CharField(max_length=32)
    permitted_roles = models.JSONField(default=list)
    state = models.CharField(max_length=24, choices=TeachingSessionNodeState.choices, default=TeachingSessionNodeState.PENDING)
    context_fingerprint = models.CharField(max_length=128)
    transition_metadata = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_teaching_session_node"
        constraints = [
            models.UniqueConstraint(fields=["session", "bridge_node"], name="ssi_tnode_unique"),
            models.UniqueConstraint(fields=["session", "context_fingerprint"], name="ssi_tnode_ctx_unique"),
        ]
        indexes = [models.Index(fields=["session", "topological_layer", "plan_ordinal"], name="ssi_tnode_order_idx")]

    def save(self, *args, **kwargs):
        if self.pk:
            old = type(self).objects.filter(pk=self.pk).first()
            frozen = ("session_id", "bridge_node_id", "graph_node_id", "teaching_pack_id", "graph_version_id", "plan_ordinal", "topological_layer", "bridge_disposition", "permitted_roles", "context_fingerprint")
            if old and any(getattr(old, field) != getattr(self, field) for field in frozen):
                raise ValidationError("Teaching session nodes are immutable projections.", code="TEACHING_SESSION_NODE_IMMUTABLE")
        return super().save(*args, **kwargs)


class TeachingOrchestrationRun(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="teaching_orchestration_runs")
    learner = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="teaching_orchestration_runs")
    intent = models.ForeignKey("self_study.SelfStudyIntent", on_delete=models.PROTECT, related_name="teaching_orchestration_runs")
    session = models.ForeignKey(SelfStudyTeachingSession, on_delete=models.PROTECT, related_name="orchestration_runs")
    bridge_plan = models.ForeignKey("self_study.BridgePlan", on_delete=models.PROTECT, related_name="teaching_orchestration_runs")
    preparation_manifest = models.ForeignKey("self_study.TeachingPreparationManifest", on_delete=models.PROTECT, related_name="teaching_orchestration_runs")
    graph_version = models.ForeignKey("self_study.CurriculumGraphVersion", on_delete=models.PROTECT, related_name="teaching_orchestration_runs")
    retrieval_manifest = models.ForeignKey("self_study.TeachingRetrievalManifest", on_delete=models.PROTECT, related_name="teaching_orchestration_runs")
    orchestration_version = models.CharField(max_length=64)
    model_version = models.CharField(max_length=64)
    prompt_policy_version = models.CharField(max_length=64)
    run_fingerprint = models.CharField(max_length=128)
    status = models.CharField(max_length=24, choices=TeachingOrchestrationRunStatus.choices, default=TeachingOrchestrationRunStatus.PENDING)
    stage = models.CharField(max_length=32, default="CREATED")
    claim_token = models.UUIDField(null=True, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    claimed_by = models.CharField(max_length=128, blank=True)
    failure_code = models.CharField(max_length=96, blank=True)
    failure_detail = models.CharField(max_length=500, blank=True)
    predecessor = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="successors")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "self_study_teaching_orchestration_run"
        constraints = [models.UniqueConstraint(fields=["tenant", "run_fingerprint"], name="ssi_torun_fp_unique")]
        indexes = [models.Index(fields=["session", "status"], name="ssi_torun_status_idx")]


class TeachingContextSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(SelfStudyTeachingSession, on_delete=models.PROTECT, related_name="context_snapshots")
    session_node = models.ForeignKey(TeachingSessionNode, on_delete=models.PROTECT, related_name="context_snapshots")
    graph_version = models.ForeignKey("self_study.CurriculumGraphVersion", on_delete=models.PROTECT)
    bridge_plan_fingerprint = models.CharField(max_length=128)
    preparation_fingerprint = models.CharField(max_length=128)
    retrieval_fingerprint = models.CharField(max_length=128)
    permitted_roles = models.JSONField(default=list)
    current_learner_input = models.TextField(blank=True)
    prior_turn_references = models.JSONField(default=list)
    retrieval_filters = models.JSONField(default=dict)
    safety_policy_version = models.CharField(max_length=64)
    disclosure_policy_version = models.CharField(max_length=64)
    model_version = models.CharField(max_length=64)
    prompt_policy_version = models.CharField(max_length=64)
    context_snapshot = models.JSONField()
    context_fingerprint = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_teaching_context_snapshot"
        indexes = [models.Index(fields=["session", "created_at"], name="ssi_tctx_session_idx")]


class TeachingTurn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(SelfStudyTeachingSession, on_delete=models.PROTECT, related_name="turns")
    session_node = models.ForeignKey(TeachingSessionNode, on_delete=models.PROTECT, related_name="turns")
    sequence_number = models.PositiveIntegerField()
    actor = models.CharField(max_length=16, choices=TeachingTurnActor.choices)
    action = models.CharField(max_length=32, choices=TeachingTurnAction.choices)
    learner_input_reference = models.CharField(max_length=128, blank=True)
    generated_response_reference = models.CharField(max_length=128, blank=True)
    context_snapshot = models.ForeignKey(TeachingContextSnapshot, on_delete=models.PROTECT, related_name="turns")
    response_text = models.TextField(blank=True)
    provider_version = models.CharField(max_length=64)
    model_version = models.CharField(max_length=64)
    prompt_policy_version = models.CharField(max_length=64)
    generation_fingerprint = models.CharField(max_length=128)
    idempotency_key = models.CharField(max_length=128, blank=True)
    safety_status = models.CharField(max_length=16, choices=TeachingSafetyStatus.choices, default=TeachingSafetyStatus.SAFE)
    failure_code = models.CharField(max_length=96, blank=True)
    interruption_code = models.CharField(max_length=96, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_teaching_turn"
        constraints = [
            models.UniqueConstraint(fields=["session", "sequence_number"], name="ssi_tturn_seq_unique"),
            models.UniqueConstraint(fields=["session", "generation_fingerprint"], name="ssi_tturn_fp_unique"),
            models.UniqueConstraint(fields=["session", "idempotency_key"], name="ssi_tturn_idem_unique"),
        ]
        indexes = [models.Index(fields=["session", "created_at"], name="ssi_tturn_session_idx")]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Teaching turns are immutable.", code="TEACHING_TURN_IMMUTABLE")
        return super().save(*args, **kwargs)


class TeachingTurnCitation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    turn = models.ForeignKey(TeachingTurn, on_delete=models.PROTECT, related_name="citations")
    teaching_pack_resource = models.ForeignKey("self_study.TeachingPackResource", on_delete=models.PROTECT, related_name="turn_citations")
    evidence_unit = models.ForeignKey("self_study.ContentEvidenceUnit", on_delete=models.PROTECT, related_name="turn_citations")
    resource = models.ForeignKey("academic.LearningResource", on_delete=models.PROTECT, related_name="self_study_turn_citations")
    extraction_provenance = models.JSONField(default=dict)
    mapping_classification = models.CharField(max_length=32)
    teaching_role = models.CharField(max_length=32)
    retrieval_record_identity = models.CharField(max_length=128)
    citation = models.JSONField(default=dict)
    citation_fingerprint = models.CharField(max_length=128)

    class Meta:
        db_table = "self_study_teaching_turn_citation"
        constraints = [models.UniqueConstraint(fields=["turn", "citation_fingerprint"], name="ssi_tcite_fp_unique")]


class TeachingTransition(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(SelfStudyTeachingSession, on_delete=models.PROTECT, related_name="transitions")
    source_state = models.CharField(max_length=24)
    target_state = models.CharField(max_length=24)
    source_node = models.ForeignKey(TeachingSessionNode, null=True, blank=True, on_delete=models.PROTECT, related_name="source_transitions")
    target_node = models.ForeignKey(TeachingSessionNode, null=True, blank=True, on_delete=models.PROTECT, related_name="target_transitions")
    transition_type = models.CharField(max_length=24, choices=TeachingTransitionType.choices)
    actor = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="self_study_teaching_transitions")
    authority = models.CharField(max_length=64)
    reason_code = models.CharField(max_length=96)
    expected_version = models.PositiveIntegerField()
    transition_fingerprint = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_teaching_transition"
        constraints = [models.UniqueConstraint(fields=["session", "transition_fingerprint"], name="ssi_ttrans_fp_unique")]
        indexes = [models.Index(fields=["session", "created_at"], name="ssi_ttrans_session_idx")]


class TeachingSessionFinding(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(SelfStudyTeachingSession, on_delete=models.PROTECT, related_name="findings")
    session_node = models.ForeignKey(TeachingSessionNode, null=True, blank=True, on_delete=models.PROTECT, related_name="findings")
    code = models.CharField(max_length=96)
    severity = models.CharField(max_length=16, choices=TeachingFindingSeverity.choices)
    blocking = models.BooleanField(default=False)
    scope = models.CharField(max_length=32)
    affected_identities = models.JSONField(default=list)
    details = models.JSONField(default=dict)
    policy_version = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_teaching_session_finding"
        indexes = [models.Index(fields=["session", "blocking", "severity"], name="ssi_tsfind_idx")]
