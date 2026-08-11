from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


# ============================================================================
# Enums
# ============================================================================

class ArielIdentityStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    ARCHIVED = "archived", "Archived"


class ArielRelationshipStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    TERMINATED = "terminated", "Terminated"


class ConsentState(models.TextChoices):
    PENDING = "pending", "Pending"
    GRANTED = "granted", "Granted"
    WITHDRAWN = "withdrawn", "Withdrawn"


class InstitutionalVisibility(models.TextChoices):
    PRIVATE = "private", "Private"
    METADATA_ONLY = "metadata_only", "Metadata Only"
    AGGREGATE = "aggregate", "Aggregate"


class TeachingSessionStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    COMPLETED = "completed", "Completed"
    ABANDONED = "abandoned", "Abandoned"


class TeachingTurnActor(models.TextChoices):
    LEARNER = "learner", "Learner"
    ARIEL = "ariel", "Ariel"


class TeachingTurnDisposition(models.TextChoices):
    CONVERSATION = "conversation", "Conversation"
    TEACHING = "teaching", "Teaching"
    CORRECTION = "correction", "Correction"
    REINFORCEMENT = "reinforcement", "Reinforcement"
    FORGETTING = "forgetting", "Forgetting"
    INSPECTION = "inspection", "Inspection"
    QUESTION = "question", "Question"


class TeachBackInteractionType(models.TextChoices):
    RESTATEMENT = "restatement", "Restatement"
    NEW_EXAMPLE = "new_example", "New Example"
    DRAW_OR_DIAGRAM = "draw_or_diagram", "Draw Or Diagram"
    LABEL_DIAGRAM = "label_diagram", "Label Diagram"
    COMPARE_CASES = "compare_cases", "Compare Cases"
    WHAT_IF = "what_if", "What If"
    CORRECT_ARIEL = "correct_ariel", "Correct Ariel"
    RETEACH_AFTER_DELAY = "reteach_after_delay", "Reteach After Delay"
    UNFAMILIAR_APPLICATION = "unfamiliar_application", "Unfamiliar Application"
    CLARIFY_TERM = "clarify_term", "Clarify Term"
    EXPLAIN_STEP = "explain_step", "Explain Step"
    CONNECT_IDEAS = "connect_ideas", "Connect Ideas"
    RESOLVE_CONTRADICTION = "resolve_contradiction", "Resolve Contradiction"


class TeachBackInteractionStatus(models.TextChoices):
    PROPOSED = "proposed", "Proposed"
    ACTIVE = "active", "Active"
    AWAITING_LEARNER = "awaiting_learner", "Awaiting Learner"
    AWAITING_ARTEFACT = "awaiting_artefact", "Awaiting Artefact"
    RESOLVED = "resolved", "Resolved"
    SKIPPED = "skipped", "Skipped"
    EXPIRED = "expired", "Expired"
    CANCELLED = "cancelled", "Cancelled"


class TeachBackIntensity(models.TextChoices):
    LIGHT = "light", "Light"
    STANDARD = "standard", "Standard"
    DEEP = "deep", "Deep"


class TeachingInputProvenance(models.TextChoices):
    DIRECT_TYPED_EXPLANATION = "direct_typed_explanation", "Direct Typed Explanation"
    PASTED_TEXT = "pasted_text", "Pasted Text"
    IMPORTED_ARTEFACT = "imported_artefact", "Imported Artefact"
    STUDY_LAB_ARTEFACT = "study_lab_artefact", "Study Lab Artefact"
    VOICE_TRANSCRIPT = "voice_transcript", "Voice Transcript"
    UNKNOWN = "unknown", "Unknown"


class TeachingTransformationType(models.TextChoices):
    RESTATED_EXPLANATION = "restated_explanation", "Restated Explanation"
    ORIGINAL_EXAMPLE = "original_example", "Original Example"
    DIAGRAM = "diagram", "Diagram"
    LABELLING = "labelling", "Labelling"
    COMPARISON = "comparison", "Comparison"
    WHAT_IF_EXPLANATION = "what_if_explanation", "What If Explanation"
    CORRECTION = "correction", "Correction"
    APPLICATION = "application", "Application"


class TeachingTransformationStatus(models.TextChoices):
    REQUESTED = "requested", "Requested"
    SUBMITTED = "submitted", "Submitted"
    ACCEPTED = "accepted", "Accepted"
    SKIPPED = "skipped", "Skipped"
    EXPIRED = "expired", "Expired"


class MemoryState(models.TextChoices):
    NEW = "new", "New"
    FRAGILE = "fragile", "Fragile"
    REINFORCED = "reinforced", "Reinforced"
    STABLE = "stable", "Stable"
    CONFLICTED = "conflicted", "Conflicted"
    MISCONCEIVED = "misconceived", "Misconceived"
    FORGOTTEN = "forgotten", "Forgotten"
    SUPERSEDED = "superseded", "Superseded"
    RETRACTED = "retracted", "Retracted"


class KnowledgeProvenance(models.TextChoices):
    LEARNER_TEACHING = "learner_teaching", "Learner Teaching"
    LEARNER_CORRECTION = "learner_correction", "Learner Correction"
    LEARNER_REINFORCEMENT = "learner_reinforcement", "Learner Reinforcement"


class ConstitutionRule(models.TextChoices):
    ARIEL_LEARNS_ONLY_FROM_LEARNER = "ARIEL_LEARNS_ONLY_FROM_LEARNER"
    ARIEL_DOES_NOT_TEACH = "ARIEL_DOES_NOT_TEACH"
    ARIEL_DOES_NOT_GRADE = "ARIEL_DOES_NOT_GRADE"
    ARIEL_DOES_NOT_CONFIRM_MASTERY = "ARIEL_DOES_NOT_CONFIRM_MASTERY"
    ARIEL_DOES_NOT_ACCESS_RETRIEVAL = "ARIEL_DOES_NOT_ACCESS_RETRIEVAL"
    ARIEL_DOES_NOT_ACCESS_CURRICULUM = "ARIEL_DOES_NOT_ACCESS_CURRICULUM"
    ARIEL_DOES_NOT_ACCESS_ANSWER_KEYS = "ARIEL_DOES_NOT_ACCESS_ANSWER_KEYS"
    ARIEL_MAY_BE_UNCERTAIN = "ARIEL_MAY_BE_UNCERTAIN"
    ARIEL_MAY_FORGET = "ARIEL_MAY_FORGET"
    ARIEL_MAY_RETAIN_MISCONCEPTIONS = "ARIEL_MAY_RETAIN_MISCONCEPTIONS"
    ARIEL_MEMORY_REQUIRES_PROVENANCE = "ARIEL_MEMORY_REQUIRES_PROVENANCE"


class ArielCapability(models.TextChoices):
    ARIEL_USE = "ariel.use"
    ARIEL_VIEW_MEMORY = "ariel.view_memory"
    ARIEL_CORRECT_MEMORY = "ariel.correct_memory"
    ARIEL_FORGET_MEMORY = "ariel.forget_memory"
    ARIEL_RESET = "ariel.reset"
    ARIEL_EXPORT = "ariel.export"
    ARIEL_SUSPEND = "ariel.suspend"
    ARIEL_ADMIN_STATUS = "ariel.admin_status"
    ARIEL_ADMIN_SUSPEND = "ariel.admin_suspend"
    ARIEL_ADMIN_RESTORE = "ariel.admin_restore"
    ARIEL_ADMIN_VIEW_AUDIT = "ariel.admin_view_audit"


# ============================================================================
# Constitution
# ============================================================================

class ArielConstitution(models.Model):
    """Versioned Ariel Constitution that governs all Ariel sessions."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    version = models.CharField(max_length=32, unique=True)
    rules = models.JSONField(default=list, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ariel_constitution"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Constitution v{self.version}"

    @property
    def rule_codes(self) -> list[str]:
        return [r.get("code", "") for r in (self.rules or []) if isinstance(r, dict)]

    def has_rule(self, rule_code: str) -> bool:
        return rule_code in self.rule_codes


# ============================================================================
# Identity & Relationship
# ============================================================================

class ArielIdentity(models.Model):
    """The governed learner companion. One active Ariel per learner."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_identities")
    institution = models.ForeignKey(
        "users.Institution",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ariel_identities",
    )
    constitution = models.ForeignKey(ArielConstitution, on_delete=models.PROTECT, related_name="ariel_identities")
    status = models.CharField(max_length=24, choices=ArielIdentityStatus.choices, default=ArielIdentityStatus.DRAFT)
    display_name = models.CharField(max_length=100, default="Ariel")
    metadata = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ariel_identity"
        indexes = [
            models.Index(fields=["learner", "status"], name="ariel_id_learner_status_idx"),
            models.Index(fields=["institution", "status"], name="ariel_id_inst_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["learner"],
                condition=Q(status=ArielIdentityStatus.ACTIVE),
                name="ariel_one_active_per_learner",
            ),
        ]

    def __str__(self) -> str:
        return f"Ariel for {self.learner_id} ({self.status})"

    def clean(self):
        super().clean()
        if self.status == ArielIdentityStatus.ACTIVE and not self.activated_at:
            raise ValidationError("Active Ariel must record activated_at.", code="ARIEL_ACTIVATED_AT_REQUIRED")
        if self.status == ArielIdentityStatus.SUSPENDED and not self.suspended_at:
            raise ValidationError("Suspended Ariel must record suspended_at.", code="ARIEL_SUSPENDED_AT_REQUIRED")
        if self.status == ArielIdentityStatus.ARCHIVED and not self.archived_at:
            raise ValidationError("Archived Ariel must record archived_at.", code="ARIEL_ARCHIVED_AT_REQUIRED")

    def activate(self, *, when=None) -> bool:
        if self.status == ArielIdentityStatus.ACTIVE:
            return False
        self.status = ArielIdentityStatus.ACTIVE
        self.activated_at = when or timezone.now()
        self.version += 1
        return True

    def suspend(self, *, when=None) -> bool:
        if self.status == ArielIdentityStatus.SUSPENDED:
            return False
        self.status = ArielIdentityStatus.SUSPENDED
        self.suspended_at = when or timezone.now()
        self.version += 1
        return True

    def archive(self, *, when=None) -> bool:
        if self.status == ArielIdentityStatus.ARCHIVED:
            return False
        self.status = ArielIdentityStatus.ARCHIVED
        self.archived_at = when or timezone.now()
        self.version += 1
        return True


class ArielRelationship(models.Model):
    """Explicit learner-Ariel relationship with privacy and consent."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.OneToOneField(ArielIdentity, on_delete=models.PROTECT, related_name="relationship")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_relationships")
    consent_state = models.CharField(max_length=24, choices=ConsentState.choices, default=ConsentState.PENDING)
    institutional_visibility = models.CharField(
        max_length=24,
        choices=InstitutionalVisibility.choices,
        default=InstitutionalVisibility.PRIVATE,
    )
    status = models.CharField(max_length=24, choices=ArielRelationshipStatus.choices, default=ArielRelationshipStatus.ACTIVE)
    privacy_policy = models.JSONField(default=dict, blank=True)
    retention_policy = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    consent_granted_at = models.DateTimeField(null=True, blank=True)
    consent_withdrawn_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ariel_relationship"
        indexes = [
            models.Index(fields=["learner", "status"], name="ariel_rel_learner_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Relationship: {self.learner_id} <-> Ariel {self.identity_id}"

    def grant_consent(self, *, when=None) -> bool:
        if self.consent_state == ConsentState.GRANTED:
            return False
        self.consent_state = ConsentState.GRANTED
        self.consent_granted_at = when or timezone.now()
        self.version += 1
        return True

    def withdraw_consent(self, *, when=None) -> bool:
        if self.consent_state == ConsentState.WITHDRAWN:
            return False
        self.consent_state = ConsentState.WITHDRAWN
        self.consent_withdrawn_at = when or timezone.now()
        self.version += 1
        return True


# ============================================================================
# Teaching Sessions & Turns
# ============================================================================

class ArielTeachingSession(models.Model):
    """Durable learner teaching session."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(ArielIdentity, on_delete=models.PROTECT, related_name="teaching_sessions")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_teaching_sessions")
    constitution = models.ForeignKey(ArielConstitution, on_delete=models.PROTECT, related_name="teaching_sessions")
    learning_journey = models.ForeignKey(
        "learning_journeys.LearningJourney",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ariel_teaching_sessions",
    )
    subject = models.ForeignKey(
        "academic.Subject",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ariel_teaching_sessions",
    )
    concept_reference = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=24, choices=TeachingSessionStatus.choices, default=TeachingSessionStatus.ACTIVE)
    metadata = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ariel_teaching_session"
        indexes = [
            models.Index(fields=["identity", "status"], name="ariel_ts_identity_status_idx"),
            models.Index(fields=["learner", "status"], name="ariel_ts_learner_status_idx"),
            models.Index(fields=["learning_journey"], name="ariel_ts_journey_idx"),
        ]

    def __str__(self) -> str:
        return f"Teaching Session {self.id} for {self.learner_id}"

    def complete(self, *, when=None) -> bool:
        if self.status == TeachingSessionStatus.COMPLETED:
            return False
        self.status = TeachingSessionStatus.COMPLETED
        self.completed_at = when or timezone.now()
        self.version += 1
        return True

    def abandon(self, *, when=None) -> bool:
        if self.status == TeachingSessionStatus.ABANDONED:
            return False
        self.status = TeachingSessionStatus.ABANDONED
        self.version += 1
        return True


class ArielTeachingTurn(models.Model):
    """Learner-visible conversation turn. Never stores hidden reasoning."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ArielTeachingSession, on_delete=models.PROTECT, related_name="turns")
    actor = models.CharField(max_length=16, choices=TeachingTurnActor.choices)
    content = models.TextField()
    sequence_number = models.PositiveIntegerField()
    disposition = models.CharField(max_length=24, choices=TeachingTurnDisposition.choices, default=TeachingTurnDisposition.CONVERSATION)
    provenance = models.CharField(max_length=48, choices=KnowledgeProvenance.choices, blank=True)
    resulting_memory_effect = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ariel_teaching_turn"
        ordering = ["session_id", "sequence_number"]
        indexes = [
            models.Index(fields=["session", "sequence_number"], name="ariel_tt_session_seq_idx"),
            models.Index(fields=["actor", "disposition"], name="ariel_tt_actor_disp_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["session", "sequence_number"], name="ariel_tt_unique_session_seq"),
        ]

    def __str__(self) -> str:
        return f"Turn {self.sequence_number} ({self.actor})"


class ArielTeachBackInteraction(models.Model):
    """Deterministic teach-back interaction subordinate to the teaching session."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(ArielIdentity, on_delete=models.PROTECT, related_name="teach_back_interactions")
    teaching_session = models.ForeignKey(
        ArielTeachingSession,
        on_delete=models.PROTECT,
        related_name="teach_back_interactions",
    )
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_teach_back_interactions")
    workspace_id = models.UUIDField(null=True, blank=True)
    learning_journey = models.ForeignKey(
        "learning_journeys.LearningJourney",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ariel_teach_back_interactions",
    )
    subject = models.ForeignKey(
        "academic.Subject",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ariel_teach_back_interactions",
    )
    concept_reference = models.CharField(max_length=255, blank=True)
    source_memory_unit = models.ForeignKey(
        "ArielKnowledgeUnit",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="teach_back_interactions",
    )
    learner_response_turn = models.ForeignKey(
        ArielTeachingTurn,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="teach_back_interactions",
    )
    interaction_type = models.CharField(max_length=48, choices=TeachBackInteractionType.choices)
    status = models.CharField(
        max_length=32,
        choices=TeachBackInteractionStatus.choices,
        default=TeachBackInteractionStatus.PROPOSED,
    )
    strategy_reason_code = models.CharField(max_length=64, blank=True)
    intensity = models.CharField(max_length=16, choices=TeachBackIntensity.choices, default=TeachBackIntensity.STANDARD)
    prompt_template_key = models.CharField(max_length=128)
    prompt_template_version = models.CharField(max_length=32, default="1")
    input_provenance = models.CharField(
        max_length=48,
        choices=TeachingInputProvenance.choices,
        default=TeachingInputProvenance.UNKNOWN,
    )
    requires_artefact = models.BooleanField(default=False)
    required_artefact_type = models.CharField(max_length=64, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    presented_at = models.DateTimeField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    skipped_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ariel_teach_back_interaction"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["identity", "status"], name="ariel_tbi_identity_status_idx"),
            models.Index(fields=["teaching_session", "status"], name="ariel_tbi_session_status_idx"),
            models.Index(fields=["learner", "status"], name="ariel_tbi_learner_status_idx"),
            models.Index(fields=["source_memory_unit"], name="ariel_tbi_source_memory_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["teaching_session", "prompt_template_key", "version"],
                name="ariel_tbi_session_prompt_version_unique",
            ),
        ]

    def __str__(self) -> str:
        return f"Teach-back {self.interaction_type} ({self.status})"

    def _transition(self, status, *, when_field=None, when=None) -> bool:
        if self.status == status:
            return False
        if self.status in {
            TeachBackInteractionStatus.RESOLVED,
            TeachBackInteractionStatus.SKIPPED,
            TeachBackInteractionStatus.EXPIRED,
            TeachBackInteractionStatus.CANCELLED,
        }:
            return False
        self.status = status
        if when_field:
            setattr(self, when_field, when or timezone.now())
        self.version += 1
        return True

    def present(self, *, when=None) -> bool:
        if self.status == TeachBackInteractionStatus.PROPOSED:
            self.presented_at = when or timezone.now()
            self.status = TeachBackInteractionStatus.ACTIVE
            self.version += 1
            return True
        if self.status == TeachBackInteractionStatus.ACTIVE:
            return False
        return False

    def await_learner(self, *, when=None) -> bool:
        if self.status != TeachBackInteractionStatus.ACTIVE:
            return False
        return self._transition(TeachBackInteractionStatus.AWAITING_LEARNER, when_field=None, when=when)

    def await_artefact(self, *, when=None) -> bool:
        if self.status not in {
            TeachBackInteractionStatus.PROPOSED,
            TeachBackInteractionStatus.ACTIVE,
            TeachBackInteractionStatus.AWAITING_LEARNER,
        }:
            return False
        if self.status == TeachBackInteractionStatus.AWAITING_ARTEFACT:
            return False
        self.status = TeachBackInteractionStatus.AWAITING_ARTEFACT
        self.requires_artefact = True
        self.version += 1
        return True

    def resolve(self, *, when=None) -> bool:
        if self.status == TeachBackInteractionStatus.RESOLVED:
            return False
        if self.status in {
            TeachBackInteractionStatus.SKIPPED,
            TeachBackInteractionStatus.EXPIRED,
            TeachBackInteractionStatus.CANCELLED,
        }:
            return False
        self.status = TeachBackInteractionStatus.RESOLVED
        self.resolved_at = when or timezone.now()
        self.version += 1
        return True

    def skip(self, *, when=None) -> bool:
        if self.status == TeachBackInteractionStatus.SKIPPED:
            return False
        if self.status in {
            TeachBackInteractionStatus.RESOLVED,
            TeachBackInteractionStatus.EXPIRED,
            TeachBackInteractionStatus.CANCELLED,
        }:
            return False
        self.status = TeachBackInteractionStatus.SKIPPED
        self.skipped_at = when or timezone.now()
        self.version += 1
        return True

    def cancel(self, *, when=None) -> bool:
        if self.status == TeachBackInteractionStatus.CANCELLED:
            return False
        if self.status in {
            TeachBackInteractionStatus.RESOLVED,
            TeachBackInteractionStatus.SKIPPED,
            TeachBackInteractionStatus.EXPIRED,
        }:
            return False
        self.status = TeachBackInteractionStatus.CANCELLED
        self.cancelled_at = when or timezone.now()
        self.version += 1
        return True

    def expire(self, *, when=None) -> bool:
        if self.status == TeachBackInteractionStatus.EXPIRED:
            return False
        if self.status in {
            TeachBackInteractionStatus.RESOLVED,
            TeachBackInteractionStatus.SKIPPED,
            TeachBackInteractionStatus.CANCELLED,
        }:
            return False
        self.status = TeachBackInteractionStatus.EXPIRED
        self.expires_at = when or timezone.now()
        self.version += 1
        return True


# ============================================================================
# Knowledge & Memory
# ============================================================================

class ArielKnowledgeUnit(models.Model):
    """Every knowledge item originates from explicit learner teaching."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(ArielIdentity, on_delete=models.PROTECT, related_name="knowledge_units")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_knowledge_units")
    teaching_turn = models.ForeignKey(ArielTeachingTurn, on_delete=models.PROTECT, related_name="knowledge_units")
    session = models.ForeignKey(ArielTeachingSession, on_delete=models.PROTECT, related_name="knowledge_units")
    normalized_statement = models.TextField()
    confidence = models.DecimalField(max_digits=4, decimal_places=3, default=0.5)
    memory_state = models.CharField(max_length=24, choices=MemoryState.choices, default=MemoryState.NEW)
    provenance = models.CharField(max_length=48, choices=KnowledgeProvenance.choices, default=KnowledgeProvenance.LEARNER_TEACHING)
    subject = models.ForeignKey(
        "academic.Subject",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="ariel_knowledge_units",
    )
    concept_reference = models.CharField(max_length=255, blank=True)
    superseded_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="supersedes")
    forgetting_metadata = models.JSONField(default=dict, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    forgotten_at = models.DateTimeField(null=True, blank=True)
    retracted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "ariel_knowledge_unit"
        indexes = [
            models.Index(fields=["identity", "memory_state"], name="ariel_ku_identity_state_idx"),
            models.Index(fields=["learner", "memory_state"], name="ariel_ku_learner_state_idx"),
            models.Index(fields=["subject"], name="ariel_ku_subject_idx"),
            models.Index(fields=["provenance"], name="ariel_ku_provenance_idx"),
        ]

    def __str__(self) -> str:
        return f"Knowledge {self.id} ({self.memory_state})"

    def clean(self):
        super().clean()
        if self.provenance not in KnowledgeProvenance.values:
            raise ValidationError("Knowledge provenance must be learner-originated.", code="ARIEL_PROVENANCE_INVALID")
        if not 0 <= float(self.confidence) <= 1:
            raise ValidationError("Confidence must be between 0 and 1.", code="ARIEL_CONFIDENCE_INVALID")

    def reinforce(self, *, new_confidence=None, when=None) -> bool:
        if self.memory_state in {MemoryState.FORGOTTEN, MemoryState.RETRACTED}:
            return False
        if self.memory_state == MemoryState.NEW:
            self.memory_state = MemoryState.FRAGILE
        elif self.memory_state == MemoryState.FRAGILE:
            self.memory_state = MemoryState.REINFORCED
        elif self.memory_state == MemoryState.REINFORCED:
            self.memory_state = MemoryState.STABLE
        if new_confidence is not None:
            self.confidence = new_confidence
        self.version += 1
        return True

    def forget(self, *, when=None) -> bool:
        if self.memory_state == MemoryState.FORGOTTEN:
            return False
        self.memory_state = MemoryState.FORGOTTEN
        self.forgotten_at = when or timezone.now()
        self.version += 1
        return True

    def mark_conflicted(self, *, when=None) -> bool:
        if self.memory_state == MemoryState.CONFLICTED:
            return False
        self.memory_state = MemoryState.CONFLICTED
        self.version += 1
        return True

    def mark_misconceived(self, *, when=None) -> bool:
        if self.memory_state == MemoryState.MISCONCEIVED:
            return False
        self.memory_state = MemoryState.MISCONCEIVED
        self.version += 1
        return True

    def supersede(self, *, successor, when=None) -> bool:
        if self.memory_state == MemoryState.SUPERSEDED:
            return False
        self.memory_state = MemoryState.SUPERSEDED
        self.superseded_by = successor
        self.superseded_at = when or timezone.now()
        self.version += 1
        return True

    def retract(self, *, when=None) -> bool:
        if self.memory_state == MemoryState.RETRACTED:
            return False
        self.memory_state = MemoryState.RETRACTED
        self.retracted_at = when or timezone.now()
        self.version += 1
        return True


class ArielMemoryRecord(models.Model):
    """Memory record tracking state transitions and history."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(ArielIdentity, on_delete=models.PROTECT, related_name="memory_records")
    knowledge_unit = models.ForeignKey(ArielKnowledgeUnit, on_delete=models.PROTECT, related_name="memory_records")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_memory_records")
    previous_state = models.CharField(max_length=24, choices=MemoryState.choices)
    new_state = models.CharField(max_length=24, choices=MemoryState.choices)
    previous_confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    new_confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    transition_reason = models.CharField(max_length=64, blank=True)
    provenance = models.CharField(max_length=48, choices=KnowledgeProvenance.choices)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ariel_memory_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["identity", "created_at"], name="ariel_mr_identity_time_idx"),
            models.Index(fields=["knowledge_unit", "created_at"], name="ariel_mr_ku_time_idx"),
            models.Index(fields=["learner", "created_at"], name="ariel_mr_learner_time_idx"),
        ]

    def __str__(self) -> str:
        return f"Memory: {self.previous_state} -> {self.new_state}"


# ============================================================================
# Misconceptions, Corrections, Reinforcements
# ============================================================================

class ArielMisconception(models.Model):
    """Preserves incorrect learner teaching as educational history."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(ArielIdentity, on_delete=models.PROTECT, related_name="misconceptions")
    knowledge_unit = models.ForeignKey(ArielKnowledgeUnit, on_delete=models.PROTECT, related_name="misconceptions")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_misconceptions")
    original_explanation = models.TextField()
    resulting_belief = models.TextField()
    contradiction_history = models.JSONField(default=list, blank=True)
    correction_history = models.JSONField(default=list, blank=True)
    current_state = models.CharField(max_length=24, choices=MemoryState.choices, default=MemoryState.MISCONCEIVED)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ariel_misconception"
        indexes = [
            models.Index(fields=["identity", "current_state"], name="ariel_mc_identity_state_idx"),
            models.Index(fields=["knowledge_unit"], name="ariel_mc_ku_idx"),
        ]

    def __str__(self) -> str:
        return f"Misconception {self.id} ({self.current_state})"


class ArielCorrectionRecord(models.Model):
    """Durable correction record preserving provenance and history."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(ArielIdentity, on_delete=models.PROTECT, related_name="correction_records")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_correction_records")
    superseded_knowledge = models.ForeignKey(
        ArielKnowledgeUnit,
        on_delete=models.PROTECT,
        related_name="corrections_superseding",
    )
    replacement_knowledge = models.ForeignKey(
        ArielKnowledgeUnit,
        on_delete=models.PROTECT,
        related_name="corrections_replacing",
    )
    teaching_turn = models.ForeignKey(ArielTeachingTurn, on_delete=models.PROTECT, related_name="correction_records")
    correction_reason = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ariel_correction_record"
        indexes = [
            models.Index(fields=["identity", "created_at"], name="ariel_cr_identity_time_idx"),
            models.Index(fields=["superseded_knowledge"], name="ariel_cr_superseded_idx"),
        ]

    def __str__(self) -> str:
        return f"Correction {self.id}"


class ArielReinforcementRecord(models.Model):
    """Tracks reinforcement history independent from learner evidence."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    identity = models.ForeignKey(ArielIdentity, on_delete=models.PROTECT, related_name="reinforcement_records")
    knowledge_unit = models.ForeignKey(ArielKnowledgeUnit, on_delete=models.PROTECT, related_name="reinforcement_records")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ariel_reinforcement_records")
    teaching_turn = models.ForeignKey(ArielTeachingTurn, on_delete=models.PROTECT, related_name="reinforcement_records")
    previous_confidence = models.DecimalField(max_digits=4, decimal_places=3)
    updated_confidence = models.DecimalField(max_digits=4, decimal_places=3)
    previous_state = models.CharField(max_length=24, choices=MemoryState.choices)
    new_state = models.CharField(max_length=24, choices=MemoryState.choices)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ariel_reinforcement_record"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["knowledge_unit", "created_at"], name="ariel_rr_ku_time_idx"),
            models.Index(fields=["identity", "created_at"], name="ariel_rr_identity_time_idx"),
        ]

    def __str__(self) -> str:
        return f"Reinforcement {self.id}"


# ============================================================================
# User Capabilities (Ariel-specific)
# ============================================================================

class ArielUserCapability(models.Model):
    """Ariel-specific capabilities for learners and administrators."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ariel_capabilities")
    identity = models.ForeignKey(ArielIdentity, on_delete=models.CASCADE, related_name="user_capabilities")
    capability_code = models.CharField(max_length=64, choices=ArielCapability.choices)
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="granted_ariel_capabilities",
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "ariel_user_capability"
        indexes = [
            models.Index(fields=["user", "capability_code"], name="ariel_uc_user_cap_idx"),
            models.Index(fields=["identity", "capability_code"], name="ariel_uc_identity_cap_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["user", "identity", "capability_code"], name="ariel_uc_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} : {self.capability_code}"

    @property
    def is_active(self) -> bool:
        if self.expires_at and self.expires_at <= timezone.now():
            return False
        return True


__all__ = [
    "ArielConstitution",
    "ArielIdentity",
    "ArielRelationship",
    "ArielTeachingSession",
    "ArielTeachingTurn",
    "ArielKnowledgeUnit",
    "ArielMemoryRecord",
    "ArielMisconception",
    "ArielCorrectionRecord",
    "ArielReinforcementRecord",
    "ArielUserCapability",
    "ArielIdentityStatus",
    "ArielRelationshipStatus",
    "ConsentState",
    "InstitutionalVisibility",
    "TeachingSessionStatus",
    "TeachingTurnActor",
    "TeachingTurnDisposition",
    "TeachBackInteractionType",
    "TeachBackInteractionStatus",
    "TeachBackIntensity",
    "TeachingInputProvenance",
    "TeachingTransformationType",
    "TeachingTransformationStatus",
    "MemoryState",
    "KnowledgeProvenance",
    "ConstitutionRule",
    "ArielCapability",
    "ArielTeachBackInteraction",
]
