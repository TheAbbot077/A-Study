from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class LearningMode(models.TextChoices):
    INSTITUTION_GOVERNED = "INSTITUTION_GOVERNED", "Institution governed"
    SELF_STUDY = "SELF_STUDY", "Self study"


class IntentStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    READY = "READY", "Ready"
    ACTIVE = "ACTIVE", "Active"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    CANCELLED = "CANCELLED", "Cancelled"


class RequestedDepth(models.TextChoices):
    FOUNDATIONAL = "FOUNDATIONAL", "Foundational"
    GENERAL = "GENERAL", "General"
    ACADEMIC = "ACADEMIC", "Academic"
    PROFESSIONAL = "PROFESSIONAL", "Professional"
    EXAM_PREPARATION = "EXAM_PREPARATION", "Exam preparation"
    SPECIALIST = "SPECIALIST", "Specialist"


class SourceCategory(models.TextChoices):
    OFFICIAL_CURRICULUM_AUTHORITY = "OFFICIAL_CURRICULUM_AUTHORITY", "Official curriculum authority"
    ACCREDITED_INSTITUTION = "ACCREDITED_INSTITUTION", "Accredited institution"
    GOVERNMENT_EDUCATION = "GOVERNMENT_EDUCATION", "Government education"
    PROFESSIONAL_BODY = "PROFESSIONAL_BODY", "Professional body"
    OPEN_EDUCATIONAL_RESOURCE = "OPEN_EDUCATIONAL_RESOURCE", "Open educational resource"
    PEER_REVIEWED_PUBLICATION = "PEER_REVIEWED_PUBLICATION", "Peer reviewed publication"
    APPROVED_PUBLISHER = "APPROVED_PUBLISHER", "Approved publisher"
    USER_SUPPLIED = "USER_SUPPLIED", "User supplied"
    UNVERIFIED_WEB = "UNVERIFIED_WEB", "Unverified web"


class RetentionPolicy(models.TextChoices):
    DO_NOT_RETAIN = "DO_NOT_RETAIN", "Do not retain"
    RETAIN_UNTIL_JOURNEY_END = "RETAIN_UNTIL_JOURNEY_END", "Retain until journey end"
    RETAIN_WITH_JOURNEY = "RETAIN_WITH_JOURNEY", "Retain with journey"


CURRICULUM_SOURCE_PRECEDENCE = [
    "LEARNER_SUPPLIED_OFFICIAL",
    "INSTITUTION_OR_QUALIFICATION",
    "NATIONAL_OR_REGIONAL",
    "PROFESSIONAL_OR_ACCREDITATION",
    "APPROVED_CURATED_REFERENCE",
    "GOVERNED_COMPOSITE",
    "AUTONOMOUS_FALLBACK",
]


def default_curriculum_source_precedence():
    return list(CURRICULUM_SOURCE_PRECEDENCE)


class PolicyFields(models.Model):
    automatic_acquisition_enabled = models.BooleanField(default=True)
    allowed_provider_ids = models.JSONField(default=list)
    allowed_source_categories = models.JSONField(default=list)
    allowed_licence_categories = models.JSONField(default=list)
    allowed_mime_types = models.JSONField(default=list)
    allowed_languages = models.JSONField(default=list)
    maximum_resource_count = models.PositiveIntegerField(null=True, blank=True)
    maximum_single_file_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    maximum_total_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    maximum_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cost_currency = models.CharField(max_length=3, default="USD")
    paid_content_allowed = models.BooleanField(default=False)
    unknown_licence_allowed = models.BooleanField(default=False)
    link_only_when_restricted = models.BooleanField(default=True)
    user_approval_threshold = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    retention_policy = models.CharField(max_length=64, choices=RetentionPolicy.choices, default=RetentionPolicy.RETAIN_WITH_JOURNEY)
    external_network_access_enabled = models.BooleanField(default=False)
    autonomous_curriculum_fallback_allowed = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def clean(self):
        super().clean()
        collection_fields = (
            "allowed_provider_ids",
            "allowed_source_categories",
            "allowed_licence_categories",
            "allowed_mime_types",
            "allowed_languages",
        )
        for field in collection_fields:
            value = getattr(self, field)
            if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
                raise ValidationError({field: "Must be a list of non-blank strings."}, code="ACQUISITION_POLICY_INVALID")
            if len(value) != len(set(value)):
                raise ValidationError({field: "Duplicate values are not allowed."}, code="ACQUISITION_POLICY_INVALID")
        invalid_sources = set(self.allowed_source_categories) - set(SourceCategory.values)
        if invalid_sources or SourceCategory.UNVERIFIED_WEB in self.allowed_source_categories:
            raise ValidationError(
                {"allowed_source_categories": "Unsupported or unsafe source category."},
                code="ACQUISITION_POLICY_INVALID",
            )
        if self.maximum_cost is not None and not self.cost_currency:
            raise ValidationError({"cost_currency": "Currency is required for cost limits."}, code="ACQUISITION_POLICY_INVALID")
        if self.user_approval_threshold is not None and self.maximum_cost is not None:
            if self.user_approval_threshold > self.maximum_cost:
                raise ValidationError(
                    {"user_approval_threshold": "Approval threshold cannot exceed maximum cost."},
                    code="ACQUISITION_POLICY_INVALID",
                )


class LearningPolicyRuleSet(PolicyFields):
    class Authority(models.TextChoices):
        PLATFORM = "PLATFORM", "Platform"
        TENANT = "TENANT", "Tenant"
        LEARNER = "LEARNER", "Learner"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    authority = models.CharField(max_length=16, choices=Authority.choices)
    tenant = models.ForeignKey("users.Institution", null=True, blank=True, on_delete=models.CASCADE, related_name="self_study_policies")
    learner = models.ForeignKey("users.User", null=True, blank=True, on_delete=models.CASCADE, related_name="self_study_policies")
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "self_study_policy_rule_set"
        constraints = [
            models.UniqueConstraint(
                fields=["authority", "tenant", "learner", "version"],
                name="self_study_policy_authority_version_unique",
            ),
            models.UniqueConstraint(
                fields=["authority"],
                condition=Q(authority="PLATFORM", is_active=True),
                name="self_study_one_active_platform_policy",
            ),
            models.UniqueConstraint(
                fields=["authority", "tenant"],
                condition=Q(authority="TENANT", is_active=True),
                name="self_study_one_active_tenant_policy",
            ),
            models.UniqueConstraint(
                fields=["authority", "tenant", "learner"],
                condition=Q(authority="LEARNER", is_active=True),
                name="self_study_one_active_learner_policy",
            ),
        ]

    def clean(self):
        super().clean()
        expected = {
            self.Authority.PLATFORM: (False, False),
            self.Authority.TENANT: (True, False),
            self.Authority.LEARNER: (True, True),
        }[self.authority]
        if (bool(self.tenant_id), bool(self.learner_id)) != expected:
            raise ValidationError("Policy authority scope is invalid.", code="ACQUISITION_POLICY_INVALID")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class EffectiveLearningPolicySnapshot(PolicyFields):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    policy_version = models.PositiveIntegerField()
    source_policy_ids = models.JSONField(default=list)
    purpose_disclosure_required = models.BooleanField(default=True)
    raw_scores_visible = models.BooleanField(default=False)
    comparative_ranking_allowed = models.BooleanField(default=False)
    learner_can_retake = models.BooleanField(default=True)
    learner_can_challenge = models.BooleanField(default=True)
    learner_can_attempt_checkpoint = models.BooleanField(default=True)
    formal_grade_effect = models.BooleanField(default=False)
    transcript_effect = models.BooleanField(default=False)
    curriculum_source_precedence = models.JSONField(default=default_curriculum_source_precedence)
    external_content_untrusted = models.BooleanField(default=True)
    external_content_can_alter_policy = models.BooleanField(default=False)
    external_content_can_alter_curriculum = models.BooleanField(default=False)
    external_content_can_invoke_tools = models.BooleanField(default=False)
    external_content_can_initiate_downloads = models.BooleanField(default=False)
    external_content_can_grant_trust = models.BooleanField(default=False)
    external_content_can_bypass_governance = models.BooleanField(default=False)
    external_content_can_become_official_without_validation = models.BooleanField(default=False)
    external_content_can_execute = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_effective_policy_snapshot"

    def clean(self):
        super().clean()
        if not self.purpose_disclosure_required:
            raise ValidationError("Diagnostic purpose disclosure is mandatory.", code="EFFECTIVE_POLICY_INVALID")
        if self.raw_scores_visible or self.comparative_ranking_allowed:
            raise ValidationError("Internal scores and rankings cannot be learner-visible.", code="EFFECTIVE_POLICY_INVALID")
        if self.formal_grade_effect or self.transcript_effect:
            raise ValidationError("Diagnostic placement cannot affect grades or transcripts.", code="EFFECTIVE_POLICY_INVALID")
        if self.curriculum_source_precedence != CURRICULUM_SOURCE_PRECEDENCE:
            raise ValidationError("Curriculum source precedence is invalid.", code="EFFECTIVE_POLICY_INVALID")
        unsafe_external_content = (
            not self.external_content_untrusted
            or self.external_content_can_alter_policy
            or self.external_content_can_alter_curriculum
            or self.external_content_can_invoke_tools
            or self.external_content_can_initiate_downloads
            or self.external_content_can_grant_trust
            or self.external_content_can_bypass_governance
            or self.external_content_can_become_official_without_validation
            or self.external_content_can_execute
        )
        if unsafe_external_content:
            raise ValidationError("External content safety restrictions cannot be relaxed.", code="EFFECTIVE_POLICY_INVALID")

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Effective policy snapshots are immutable.", code="EFFECTIVE_POLICY_INVALID")
        self.full_clean()
        return super().save(*args, **kwargs)


class SelfStudyIntent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learner = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="self_study_intents")
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="self_study_intents")
    subject = models.ForeignKey("academic.Subject", on_delete=models.PROTECT, related_name="self_study_intents")
    mode = models.CharField(max_length=32, choices=LearningMode.choices)
    goal_statement = models.TextField(blank=True)
    target_title = models.CharField(max_length=255, blank=True)
    target_outcomes = models.JSONField(default=list, blank=True)
    target_credential = models.CharField(max_length=255, blank=True)
    preferred_curriculum_authority = models.CharField(max_length=255, blank=True)
    jurisdiction = models.CharField(max_length=64, blank=True)
    preferred_language = models.CharField(max_length=16, blank=True)
    learner_age_band = models.CharField(max_length=32, blank=True)
    accessibility_requirements = models.JSONField(default=list, blank=True)
    desired_depth = models.CharField(max_length=32, choices=RequestedDepth.choices, default=RequestedDepth.GENERAL)
    pace_preference = models.CharField(max_length=32, blank=True)
    time_budget_minutes_per_week = models.PositiveIntegerField(null=True, blank=True)
    target_completion_date = models.DateField(null=True, blank=True)
    policy_acknowledged_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=IntentStatus.choices, default=IntentStatus.DRAFT)
    effective_policy_snapshot = models.OneToOneField(
        EffectiveLearningPolicySnapshot,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="intent",
    )
    created_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="created_self_study_intents")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "self_study_intent"
        indexes = [
            models.Index(fields=["learner", "status"], name="ssi_learner_status_idx"),
            models.Index(fields=["tenant", "status"], name="ssi_tenant_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~Q(status=IntentStatus.ACTIVE) | Q(effective_policy_snapshot__isnull=False),
                name="ssi_active_requires_policy_snapshot",
            )
        ]

    def readiness_blockers(self) -> list[str]:
        blockers = []
        if len(self.goal_statement.strip()) < 10:
            blockers.append("LEARNING_GOAL_REQUIRED")
        if not self.mode:
            blockers.append("LEARNING_MODE_REQUIRED")
        if not self.preferred_language.strip():
            blockers.append("LANGUAGE_REQUIRED")
        if not self.policy_acknowledged_at:
            blockers.append("POLICY_ACKNOWLEDGEMENT_REQUIRED")
        return blockers

    def mark_ready(self):
        if self.status != IntentStatus.DRAFT:
            raise ValidationError("Intent cannot be marked ready.", code="INVALID_INTENT_TRANSITION")
        blockers = self.readiness_blockers()
        if blockers:
            raise ValidationError(
                [ValidationError(code, code=code) for code in blockers]
            )
        self.status = IntentStatus.READY
        self.version += 1

    def return_to_draft(self):
        if self.status != IntentStatus.READY:
            raise ValidationError("Intent cannot return to draft.", code="INVALID_INTENT_TRANSITION")
        self.status = IntentStatus.DRAFT
        self.version += 1

    def activate(self, snapshot):
        if self.status != IntentStatus.READY:
            raise ValidationError("Only a ready intent can be activated.", code="INVALID_INTENT_TRANSITION")
        if snapshot is None:
            raise ValidationError("An effective policy snapshot is required.", code="POLICY_SNAPSHOT_REQUIRED")
        self.effective_policy_snapshot = snapshot
        self.status = IntentStatus.ACTIVE
        self.version += 1

    def cancel(self):
        if self.status in {IntentStatus.CANCELLED, IntentStatus.SUPERSEDED}:
            return False
        self.status = IntentStatus.CANCELLED
        self.version += 1
        return True

    def supersede(self):
        if self.status != IntentStatus.ACTIVE:
            raise ValidationError("Only an active intent can be superseded.", code="INVALID_INTENT_TRANSITION")
        self.status = IntentStatus.SUPERSEDED
        self.version += 1


class CurriculumResolutionFailure(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.ForeignKey(SelfStudyIntent, on_delete=models.PROTECT, related_name="curriculum_resolution_failures")
    attempt = models.OneToOneField(
        "self_study.CurriculumResolutionAttempt",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="resolution_failure",
    )
    policy_snapshot = models.ForeignKey(
        EffectiveLearningPolicySnapshot,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="curriculum_resolution_failures",
    )
    reason_codes = models.JSONField(default=list)
    algorithm_version = models.CharField(max_length=32, blank=True)
    registry_snapshot_identifier = models.CharField(max_length=128, blank=True)
    recorded_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="recorded_curriculum_failures")
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_curriculum_resolution_failure"

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Curriculum resolution failures are immutable.", code="CURRICULUM_RESOLUTION_FAILED")
        return super().save(*args, **kwargs)


class ResourceAcquisitionDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.ForeignKey(SelfStudyIntent, on_delete=models.PROTECT, related_name="acquisition_decisions")
    policy_snapshot = models.ForeignKey(
        EffectiveLearningPolicySnapshot, on_delete=models.PROTECT, related_name="acquisition_decisions"
    )
    decision = models.CharField(max_length=32)
    reason_codes = models.JSONField(default=list)
    candidate_metadata = models.JSONField(default=dict)
    candidate_fingerprint = models.CharField(max_length=64)
    canonical_uri = models.URLField(max_length=2048, blank=True)
    provider_id = models.CharField(max_length=255)
    content_hash = models.CharField(max_length=128, blank=True)
    acquisition_method = models.CharField(max_length=32, default="POLICY_AUTHORIZATION_ONLY")
    decided_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="resource_acquisition_decisions")
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_resource_acquisition_decision"
        constraints = [
            models.UniqueConstraint(fields=["intent", "idempotency_key"], name="ssi_acquisition_idempotency_unique")
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Acquisition decisions are immutable.", code="RESOURCE_ACQUISITION_NOT_ALLOWED")
        return super().save(*args, **kwargs)


class AutonomousFallbackDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.ForeignKey(SelfStudyIntent, on_delete=models.PROTECT, related_name="autonomous_fallback_decisions")
    policy_snapshot = models.ForeignKey(
        EffectiveLearningPolicySnapshot, on_delete=models.PROTECT, related_name="autonomous_fallback_decisions"
    )
    resolution_failure = models.ForeignKey(
        CurriculumResolutionFailure, null=True, blank=True, on_delete=models.PROTECT, related_name="fallback_decisions"
    )
    authorized = models.BooleanField(default=False)
    reason_codes = models.JSONField(default=list)
    decided_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="autonomous_fallback_decisions")
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_autonomous_fallback_decision"
        constraints = [
            models.UniqueConstraint(fields=["intent", "idempotency_key"], name="ssi_fallback_idempotency_unique")
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Fallback decisions are immutable.", code="AUTONOMOUS_FALLBACK_NOT_ALLOWED")
        return super().save(*args, **kwargs)


from .curriculum_models import (  # noqa: E402,F401
    CompositeCurriculumComponent,
    CompositeCurriculumProposal,
    CurriculumAuthority,
    CurriculumReference,
    CurriculumResolutionAttempt,
    CurriculumResolutionCandidate,
    CurriculumSelectionDecision,
    CurriculumVersion,
)
from .graph_models import (  # noqa: E402,F401
    CurriculumEdge,
    CurriculumGraph,
    CurriculumGraphCitation,
    CurriculumGraphFinding,
    CurriculumGraphSpecificationRecord,
    CurriculumGraphValidationRun,
    CurriculumGraphVersion,
    CurriculumNode,
)
from .diagnostic_models import (  # noqa: E402,F401
    DiagnosticBlueprint, DiagnosticBlueprintNode, DiagnosticCompetencyEstimate, DiagnosticItem,
    DiagnosticItemNode, DiagnosticItemPresentation, DiagnosticPlacementChallenge,
    DiagnosticPlacementNode, DiagnosticPlacementProfile, DiagnosticResponse, EntryDiagnostic,
)
from .evidence_models import *  # noqa: E402,F401,F403
from .bridge_models import *  # noqa: E402,F401,F403
from .teaching_models import *  # noqa: E402,F401,F403
from .orchestration_models import *  # noqa: E402,F401,F403
from .workspace_models import *  # noqa: E402,F401,F403
