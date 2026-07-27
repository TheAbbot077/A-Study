from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .enums import (
    AttributeClassification,
    DeclarationSynchronizationResultCode,
    DeclarationSynchronizationStatus,
    EvidenceAuthorityClass,
    EvidenceLinkStatus,
    EvidenceRelationship,
    EvidenceSourceDomain,
    EvidenceSourceType,
    AttributeSourceType,
    AttributeVisibility,
    LearningAttributeType,
    LearnerPreferenceKey,
    LearnerPreferenceStatus,
    LearningProfileStatus,
    LearningIdentityReviewAction,
    LearningIdentityReviewStatus,
    LearningObservationStatus,
    LearningObservationType,
    ObservationSynchronizationResultCode,
    ObservationSynchronizationStatus,
    ProfileVersionStatus,
)
from .validators import validate_attribute_value


class LearnerLearningProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="learning_identity_profiles")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="learning_identity_profiles")
    status = models.CharField(
        max_length=24,
        choices=LearningProfileStatus.choices,
        default=LearningProfileStatus.DRAFT,
    )
    current_version = models.ForeignKey(
        "learning_identity.LearningProfileVersion",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="current_for_profiles",
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    restricted_at = models.DateTimeField(null=True, blank=True)
    restriction_reason = models.CharField(max_length=160, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "learner", "status"], name="li_profile_tenant_learner_idx"),
            models.Index(fields=["learner", "status"], name="li_profile_learner_status_idx"),
            models.Index(fields=["current_version"], name="li_profile_current_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "learner"],
                condition=~Q(status=LearningProfileStatus.ARCHIVED),
                name="li_one_open_profile_per_learner",
            ),
            models.CheckConstraint(
                condition=Q(status__in=LearningProfileStatus.values),
                name="li_profile_status_valid",
            ),
        ]

    def clean(self):
        super().clean()
        if self.status == LearningProfileStatus.ACTIVE and self.current_version_id is None:
            raise ValidationError("An active profile must reference a current published version.", code="PROFILE_CURRENT_VERSION_REQUIRED")
        if self.status == LearningProfileStatus.ARCHIVED and self.archived_at is None:
            raise ValidationError("Archived profiles must record archived_at.", code="PROFILE_ARCHIVED_AT_REQUIRED")
        if self.status == LearningProfileStatus.RESTRICTED and self.restricted_at is None:
            raise ValidationError("Restricted profiles must record restricted_at.", code="PROFILE_RESTRICTED_AT_REQUIRED")
        if self.current_version and self.current_version.profile_id != self.id:
            raise ValidationError("Current version must belong to the profile.", code="PROFILE_CURRENT_VERSION_MISMATCH")

    @property
    def is_archived(self) -> bool:
        return self.status == LearningProfileStatus.ARCHIVED

    @property
    def is_restricted(self) -> bool:
        return self.status == LearningProfileStatus.RESTRICTED

    def ensure_can_receive_draft(self):
        if self.is_archived:
            raise ValidationError("Archived profiles cannot receive draft versions.", code="PROFILE_ARCHIVED")

    def restrict(self, *, reason: str = ""):
        if self.is_archived:
            raise ValidationError("Archived profiles cannot be restricted.", code="PROFILE_ARCHIVED")
        self.status = LearningProfileStatus.RESTRICTED
        self.restricted_at = timezone.now()
        self.restriction_reason = reason[:160]
        self.version += 1

    def archive(self):
        if self.is_archived:
            return
        self.status = LearningProfileStatus.ARCHIVED
        self.archived_at = timezone.now()
        self.version += 1


class LearningProfileVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(LearnerLearningProfile, on_delete=models.PROTECT, related_name="profile_versions")
    version_number = models.PositiveIntegerField()
    status = models.CharField(
        max_length=24,
        choices=ProfileVersionStatus.choices,
        default=ProfileVersionStatus.DRAFT,
    )
    summary = models.TextField(blank=True)
    source_revision = models.CharField(max_length=64, blank=True)
    supersedes_version = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="successor_versions",
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_learning_profile_versions")
    created_at = models.DateTimeField(auto_now_add=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="published_learning_profile_versions",
    )
    published_at = models.DateTimeField(null=True, blank=True)
    superseded_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["profile_id", "version_number"]
        indexes = [
            models.Index(fields=["profile", "status", "version_number"], name="li_version_profile_status_idx"),
            models.Index(fields=["published_at"], name="li_version_published_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["profile", "version_number"], name="li_unique_profile_version_no"),
            models.UniqueConstraint(
                fields=["profile"],
                condition=Q(status=ProfileVersionStatus.DRAFT),
                name="li_one_draft_version",
            ),
            models.CheckConstraint(
                condition=Q(status__in=ProfileVersionStatus.values),
                name="li_version_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(supersedes_version__isnull=True) | ~Q(id=models.F("supersedes_version")),
                name="li_version_not_self_supersede",
            ),
        ]

    def clean(self):
        super().clean()
        if self.version_number < 1:
            raise ValidationError("Version number must be positive.", code="VERSION_NUMBER_INVALID")
        if self.supersedes_version_id:
            if self.supersedes_version_id == self.id:
                raise ValidationError("A version cannot supersede itself.", code="VERSION_SELF_SUPERSEDE")
            if self.supersedes_version.profile_id != self.profile_id:
                raise ValidationError("Superseded version must belong to the same profile.", code="VERSION_SUPERSEDE_PROFILE_MISMATCH")
            if self.supersedes_version.status != ProfileVersionStatus.PUBLISHED:
                raise ValidationError("Only published versions can be superseded.", code="VERSION_SUPERSEDE_NOT_PUBLISHED")
        if self.status == ProfileVersionStatus.PUBLISHED and not self.published_at:
            raise ValidationError("Published versions must record published_at.", code="VERSION_PUBLISHED_AT_REQUIRED")

    @property
    def is_mutable_draft(self) -> bool:
        return self.status == ProfileVersionStatus.DRAFT

    def ensure_draft(self):
        if not self.is_mutable_draft:
            raise ValidationError("Only draft profile versions may be modified.", code="VERSION_NOT_DRAFT")

    def publish(self, *, actor, supersedes=None):
        self.ensure_draft()
        self.status = ProfileVersionStatus.PUBLISHED
        self.published_by = actor
        self.published_at = timezone.now()
        self.supersedes_version = supersedes

    def mark_superseded(self):
        if self.status != ProfileVersionStatus.PUBLISHED:
            raise ValidationError("Only published profile versions may be superseded.", code="VERSION_NOT_PUBLISHED")
        self.status = ProfileVersionStatus.SUPERSEDED
        self.superseded_at = timezone.now()

    def revoke(self):
        if self.status == ProfileVersionStatus.REVOKED:
            return
        if self.status not in {ProfileVersionStatus.DRAFT, ProfileVersionStatus.PUBLISHED}:
            raise ValidationError("Only draft or published versions may be revoked.", code="VERSION_REVOKE_NOT_ALLOWED")
        self.status = ProfileVersionStatus.REVOKED
        self.revoked_at = timezone.now()


class LearningIdentityAttribute(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile_version = models.ForeignKey(LearningProfileVersion, on_delete=models.PROTECT, related_name="attributes")
    attribute_type = models.CharField(max_length=64, choices=LearningAttributeType.choices)
    classification = models.CharField(max_length=16, choices=AttributeClassification.choices)
    value = models.JSONField()
    value_schema_version = models.PositiveSmallIntegerField(default=1)
    confidence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    source_type = models.CharField(max_length=32, choices=AttributeSourceType.choices)
    source_reference = models.JSONField(default=dict, blank=True)
    declared_at = models.DateTimeField(null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    visibility = models.CharField(
        max_length=24,
        choices=AttributeVisibility.choices,
        default=AttributeVisibility.LEARNER_VISIBLE,
    )
    review_required = models.BooleanField(default=False)
    restricted = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_learning_identity_attributes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["profile_version__version_number", "attribute_type", "created_at"]
        indexes = [
            models.Index(fields=["profile_version", "attribute_type"], name="li_attr_version_type_idx"),
            models.Index(fields=["classification", "visibility"], name="li_attr_class_visibility_idx"),
            models.Index(fields=["restricted"], name="li_attr_restricted_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["profile_version", "attribute_type", "classification"], name="li_unique_attr_type_class"),
            models.CheckConstraint(condition=Q(attribute_type__in=LearningAttributeType.values), name="li_attr_type_valid"),
            models.CheckConstraint(condition=Q(classification__in=AttributeClassification.values), name="li_attr_class_valid"),
            models.CheckConstraint(condition=Q(visibility__in=AttributeVisibility.values), name="li_attr_visibility_valid"),
            models.CheckConstraint(condition=Q(source_type__in=AttributeSourceType.values), name="li_attr_source_valid"),
            models.CheckConstraint(
                condition=Q(confidence__isnull=True) | (Q(confidence__gte=0) & Q(confidence__lte=1)),
                name="li_attr_confidence_bounds",
            ),
            models.CheckConstraint(
                condition=Q(valid_from__isnull=True) | Q(valid_until__isnull=True) | Q(valid_until__gte=models.F("valid_from")),
                name="li_attr_validity_order",
            ),
            models.CheckConstraint(
                condition=Q(restricted=False) | Q(visibility__in=[AttributeVisibility.RESTRICTED, AttributeVisibility.SYSTEM_ONLY]),
                name="li_attr_restricted_visibility",
            ),
        ]

    def clean(self):
        super().clean()
        self.profile_version.ensure_draft()
        if self.value_schema_version < 1:
            raise ValidationError("Attribute value schema version is required.", code="ATTRIBUTE_SCHEMA_VERSION_REQUIRED")
        if self.classification == AttributeClassification.DECLARED:
            if self.source_type not in {
                AttributeSourceType.LEARNER,
                AttributeSourceType.AUTHORIZED_ACTOR,
                AttributeSourceType.ONBOARDING,
            }:
                raise ValidationError("Declared attributes require a declaration source.", code="DECLARED_SOURCE_INVALID")
        else:
            if not self.source_reference:
                raise ValidationError("Non-declared attributes require provenance metadata.", code="ATTRIBUTE_PROVENANCE_REQUIRED")
        if self.classification in {AttributeClassification.OBSERVED, AttributeClassification.DERIVED} and self.confidence is None:
            raise ValidationError("Observed and derived attributes require confidence.", code="ATTRIBUTE_CONFIDENCE_REQUIRED")
        if self.confidence is not None and not (0 <= self.confidence <= 1):
            raise ValidationError("Attribute confidence must be between 0 and 1.", code="ATTRIBUTE_CONFIDENCE_INVALID")
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValidationError("Attribute valid_until cannot precede valid_from.", code="ATTRIBUTE_VALIDITY_INVALID")
        if self.restricted and self.visibility not in {AttributeVisibility.RESTRICTED, AttributeVisibility.SYSTEM_ONLY}:
            raise ValidationError("Restricted attributes cannot be learner-visible.", code="ATTRIBUTE_RESTRICTED_VISIBILITY")
        self.value = validate_attribute_value(self.attribute_type, self.value)


class LearningIdentityCommandRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    scope = models.CharField(max_length=80)
    idempotency_key = models.CharField(max_length=128)
    payload_fingerprint = models.CharField(max_length=64)
    result_model = models.CharField(max_length=80)
    result_id = models.UUIDField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["scope", "idempotency_key"], name="li_command_key_once"),
        ]
        indexes = [
            models.Index(fields=["result_model", "result_id"], name="li_command_result_idx"),
        ]


class LearningIdentityDeclarationSynchronization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        LearnerLearningProfile,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="declaration_synchronizations",
    )
    profile_version = models.ForeignKey(
        LearningProfileVersion,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="declaration_synchronizations",
    )
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="learning_identity_declaration_synchronizations")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="learning_identity_declaration_synchronizations")
    onboarding_session_id = models.UUIDField()
    onboarding_revision = models.PositiveIntegerField()
    source_event_id = models.CharField(max_length=128, blank=True)
    payload_fingerprint = models.CharField(max_length=64)
    source_schema_version = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, choices=DeclarationSynchronizationStatus.choices)
    result_code = models.CharField(max_length=64, choices=DeclarationSynchronizationResultCode.choices)
    readiness_status = models.CharField(max_length=24, blank=True)
    change_counts = models.JSONField(default=dict, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "onboarding_session_id", "onboarding_revision"]
        indexes = [
            models.Index(fields=["tenant", "learner"], name="li_declsync_tenant_learner_idx"),
            models.Index(fields=["profile"], name="li_declsync_profile_idx"),
            models.Index(fields=["onboarding_session_id", "onboarding_revision"], name="li_declsync_source_rev_idx"),
            models.Index(fields=["source_event_id"], name="li_declsync_event_idx"),
            models.Index(fields=["status"], name="li_declsync_status_idx"),
            models.Index(fields=["applied_at"], name="li_declsync_applied_idx"),
            models.Index(fields=["profile", "onboarding_session_id"], name="li_declsync_profile_source_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["onboarding_session_id", "onboarding_revision"],
                name="li_declsync_unique_source_rev",
            ),
            models.UniqueConstraint(
                fields=["source_event_id"],
                condition=~Q(source_event_id=""),
                name="li_declsync_unique_event",
            ),
            models.UniqueConstraint(
                fields=["idempotency_key"],
                condition=~Q(idempotency_key=""),
                name="li_declsync_unique_idem",
            ),
            models.CheckConstraint(
                condition=Q(onboarding_revision__gt=0),
                name="li_declsync_revision_positive",
            ),
            models.CheckConstraint(
                condition=Q(status__in=DeclarationSynchronizationStatus.values),
                name="li_declsync_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(result_code__in=DeclarationSynchronizationResultCode.values),
                name="li_declsync_result_valid",
            ),
            models.CheckConstraint(
                condition=Q(payload_fingerprint__regex=r"^[0-9a-f]{64}$"),
                name="li_declsync_fp_valid",
            ),
            models.CheckConstraint(
                condition=Q(status=DeclarationSynchronizationStatus.APPLIED, applied_at__isnull=False)
                | ~Q(status=DeclarationSynchronizationStatus.APPLIED),
                name="li_declsync_applied_at",
            ),
            models.CheckConstraint(
                condition=Q(status=DeclarationSynchronizationStatus.BLOCKED, blocked_at__isnull=False)
                | ~Q(status=DeclarationSynchronizationStatus.BLOCKED),
                name="li_declsync_blocked_at",
            ),
            models.CheckConstraint(
                condition=Q(status=DeclarationSynchronizationStatus.FAILED, failed_at__isnull=False)
                | ~Q(status=DeclarationSynchronizationStatus.FAILED),
                name="li_declsync_failed_at",
            ),
        ]

    def clean(self):
        super().clean()
        if self.onboarding_revision < 1:
            raise ValidationError("Onboarding revision must be positive.", code="ONBOARDING_REVISION_INVALID")
        if len(self.payload_fingerprint or "") != 64:
            raise ValidationError("Synchronization fingerprint is required.", code="SYNCHRONIZATION_FINGERPRINT_REQUIRED")
        if self.profile and (str(self.profile.tenant_id) != str(self.tenant_id) or str(self.profile.learner_id) != str(self.learner_id)):
            raise ValidationError("Synchronization profile ownership mismatch.", code="SYNCHRONIZATION_PROFILE_MISMATCH")
        if self.profile_version and self.profile and str(self.profile_version.profile_id) != str(self.profile_id):
            raise ValidationError("Synchronization version must belong to the synchronized profile.", code="SYNCHRONIZATION_VERSION_MISMATCH")


class LearningIdentityEvidenceLink(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attribute = models.ForeignKey(LearningIdentityAttribute, on_delete=models.PROTECT, related_name="evidence_links")
    source_domain = models.CharField(max_length=32, choices=EvidenceSourceDomain.choices)
    source_type = models.CharField(max_length=48, choices=EvidenceSourceType.choices)
    source_identifier = models.CharField(max_length=128)
    source_revision = models.CharField(max_length=80, blank=True)
    relationship = models.CharField(max_length=24, choices=EvidenceRelationship.choices)
    authority_class = models.CharField(max_length=24, choices=EvidenceAuthorityClass.choices)
    status = models.CharField(max_length=16, choices=EvidenceLinkStatus.choices, default=EvidenceLinkStatus.ACTIVE)
    source_observed_at = models.DateTimeField(null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    freshness_expires_at = models.DateTimeField(null=True, blank=True)
    weight = models.DecimalField(max_digits=4, decimal_places=3, default=1)
    confidence_contribution = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True)
    safe_summary = models.CharField(max_length=240, blank=True)
    summary_visibility = models.CharField(
        max_length=24,
        choices=AttributeVisibility.choices,
        default=AttributeVisibility.AUTHORIZED_STAFF,
    )
    metadata_schema_version = models.PositiveSmallIntegerField(default=1)
    linked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="linked_learning_identity_evidence")
    linked_at = models.DateTimeField(auto_now_add=True)
    withdrawn_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="withdrawn_learning_identity_evidence",
    )
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawal_reason_code = models.CharField(max_length=64, blank=True)
    invalidated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="invalidated_learning_identity_evidence",
    )
    invalidated_at = models.DateTimeField(null=True, blank=True)
    invalidation_reason_code = models.CharField(max_length=64, blank=True)
    superseded_by_link = models.OneToOneField(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="supersedes_link",
    )
    superseded_at = models.DateTimeField(null=True, blank=True)
    review_required = models.BooleanField(default=False)
    reason_codes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["attribute_id", "relationship", "source_domain", "source_type", "source_identifier", "source_revision", "created_at"]
        indexes = [
            models.Index(fields=["attribute"], name="li_ev_attr_idx"),
            models.Index(fields=["attribute", "status"], name="li_ev_attr_status_idx"),
            models.Index(fields=["source_domain", "source_type", "source_identifier"], name="li_ev_source_idx"),
            models.Index(fields=["status"], name="li_ev_status_idx"),
            models.Index(fields=["freshness_expires_at"], name="li_ev_freshness_idx"),
            models.Index(fields=["relationship"], name="li_ev_relationship_idx"),
            models.Index(fields=["authority_class"], name="li_ev_authority_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "source_domain", "source_type", "source_identifier", "relationship", "source_revision"],
                condition=Q(status=EvidenceLinkStatus.ACTIVE),
                name="li_ev_unique_active_source",
            ),
            models.CheckConstraint(condition=Q(source_domain__in=EvidenceSourceDomain.values), name="li_ev_domain_valid"),
            models.CheckConstraint(condition=Q(source_type__in=EvidenceSourceType.values), name="li_ev_type_valid"),
            models.CheckConstraint(condition=Q(relationship__in=EvidenceRelationship.values), name="li_ev_relationship_valid"),
            models.CheckConstraint(condition=Q(authority_class__in=EvidenceAuthorityClass.values), name="li_ev_authority_valid"),
            models.CheckConstraint(condition=Q(status__in=EvidenceLinkStatus.values), name="li_ev_status_valid"),
            models.CheckConstraint(condition=Q(weight__gte=0) & Q(weight__lte=1), name="li_ev_weight_bounds"),
            models.CheckConstraint(
                condition=Q(confidence_contribution__isnull=True) | (Q(confidence_contribution__gte=0) & Q(confidence_contribution__lte=1)),
                name="li_ev_confidence_bounds",
            ),
            models.CheckConstraint(
                condition=Q(valid_from__isnull=True) | Q(valid_until__isnull=True) | Q(valid_until__gte=models.F("valid_from")),
                name="li_ev_validity_order",
            ),
            models.CheckConstraint(
                condition=Q(source_observed_at__isnull=True) | Q(freshness_expires_at__isnull=True) | Q(freshness_expires_at__gte=models.F("source_observed_at")),
                name="li_ev_freshness_order",
            ),
            models.CheckConstraint(
                condition=Q(superseded_by_link__isnull=True) | ~Q(id=models.F("superseded_by_link")),
                name="li_ev_no_self_supersede",
            ),
            models.CheckConstraint(
                condition=Q(summary_visibility__in=AttributeVisibility.values),
                name="li_ev_summary_visibility_valid",
            ),
        ]

    def clean(self):
        super().clean()
        if not self.attribute.profile_version.is_mutable_draft and self.status == EvidenceLinkStatus.ACTIVE and not self.pk:
            raise ValidationError("Evidence cannot be linked directly to a published profile version.", code="EVIDENCE_VERSION_NOT_DRAFT")
        if self.valid_from and self.valid_until and self.valid_until < self.valid_from:
            raise ValidationError("Evidence valid_until cannot precede valid_from.", code="EVIDENCE_VALIDITY_INVALID")
        if self.source_observed_at and self.freshness_expires_at and self.freshness_expires_at < self.source_observed_at:
            raise ValidationError("Evidence freshness cannot expire before observation.", code="EVIDENCE_FRESHNESS_INVALID")
        if self.weight is not None and not (0 <= self.weight <= 1):
            raise ValidationError("Evidence weight must be between 0 and 1.", code="EVIDENCE_WEIGHT_INVALID")
        if self.confidence_contribution is not None and not (0 <= self.confidence_contribution <= 1):
            raise ValidationError("Evidence confidence contribution must be between 0 and 1.", code="EVIDENCE_CONFIDENCE_INVALID")
        if self.superseded_by_link_id and self.superseded_by_link_id == self.id:
            raise ValidationError("Evidence cannot supersede itself.", code="EVIDENCE_SELF_SUPERSEDE")

    @property
    def is_terminal(self) -> bool:
        return self.status in {EvidenceLinkStatus.WITHDRAWN, EvidenceLinkStatus.INVALIDATED, EvidenceLinkStatus.SUPERSEDED}

    def withdraw(self, *, actor, reason_code: str):
        if self.status == EvidenceLinkStatus.WITHDRAWN:
            return
        if self.is_terminal:
            raise ValidationError("Terminal evidence cannot be withdrawn again.", code="EVIDENCE_TERMINAL")
        self.status = EvidenceLinkStatus.WITHDRAWN
        self.withdrawn_by = actor
        self.withdrawn_at = timezone.now()
        self.withdrawal_reason_code = reason_code[:64]

    def invalidate(self, *, actor, reason_code: str):
        if self.status == EvidenceLinkStatus.INVALIDATED:
            return
        if self.is_terminal:
            raise ValidationError("Terminal evidence cannot be invalidated again.", code="EVIDENCE_TERMINAL")
        self.status = EvidenceLinkStatus.INVALIDATED
        self.invalidated_by = actor
        self.invalidated_at = timezone.now()
        self.invalidation_reason_code = reason_code[:64]

    def mark_stale(self, *, reason_code: str):
        if self.status == EvidenceLinkStatus.STALE:
            return
        if self.is_terminal:
            raise ValidationError("Terminal evidence cannot be marked stale.", code="EVIDENCE_TERMINAL")
        self.status = EvidenceLinkStatus.STALE
        self.reason_codes = sorted(set([*(self.reason_codes or []), reason_code]))

    def mark_superseded(self, *, successor):
        if self.status == EvidenceLinkStatus.SUPERSEDED and self.superseded_by_link_id == successor.id:
            return
        if self.is_terminal:
            raise ValidationError("Terminal evidence cannot be superseded again.", code="EVIDENCE_TERMINAL")
        if successor.id == self.id:
            raise ValidationError("Evidence cannot supersede itself.", code="EVIDENCE_SELF_SUPERSEDE")
        self.status = EvidenceLinkStatus.SUPERSEDED
        self.superseded_by_link = successor
        self.superseded_at = timezone.now()


class LearningIdentityObservation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(LearnerLearningProfile, on_delete=models.PROTECT, related_name="observations")
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="learning_identity_observations")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="learning_identity_observations")
    observation_type = models.CharField(max_length=48, choices=LearningObservationType.choices)
    status = models.CharField(max_length=16, choices=LearningObservationStatus.choices, default=LearningObservationStatus.ACTIVE)
    source_domain = models.CharField(max_length=32, choices=EvidenceSourceDomain.choices)
    source_type = models.CharField(max_length=48, choices=EvidenceSourceType.choices)
    source_identifier = models.CharField(max_length=128)
    source_revision = models.CharField(max_length=80)
    semantic_key = models.CharField(max_length=160)
    authority_class = models.CharField(max_length=24, choices=EvidenceAuthorityClass.choices)
    occurred_at = models.DateTimeField()
    learner_visible = models.BooleanField(default=True)
    mentor_context_eligible = models.BooleanField(default=False)
    safe_title = models.CharField(max_length=160)
    safe_summary = models.CharField(max_length=280, blank=True)
    controlled_payload = models.JSONField(default=dict, blank=True)
    reason_codes = models.JSONField(default=list, blank=True)
    contested_at = models.DateTimeField(null=True, blank=True)
    hidden_at = models.DateTimeField(null=True, blank=True)
    stale_at = models.DateTimeField(null=True, blank=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    invalidated_at = models.DateTimeField(null=True, blank=True)
    superseded_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_observations")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at", "-created_at", "id"]
        indexes = [
            models.Index(fields=["tenant", "learner", "status"], name="li_obs_tenant_learner_idx"),
            models.Index(fields=["profile", "status"], name="li_obs_profile_status_idx"),
            models.Index(fields=["source_domain", "source_type", "source_identifier"], name="li_obs_source_idx"),
            models.Index(fields=["semantic_key"], name="li_obs_semantic_idx"),
            models.Index(fields=["mentor_context_eligible", "status"], name="li_obs_mentor_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_domain", "source_type", "source_identifier", "source_revision"],
                name="li_obs_unique_source_rev",
            ),
            models.CheckConstraint(condition=Q(observation_type__in=LearningObservationType.values), name="li_obs_type_valid"),
            models.CheckConstraint(condition=Q(status__in=LearningObservationStatus.values), name="li_obs_status_valid"),
            models.CheckConstraint(condition=Q(source_domain__in=EvidenceSourceDomain.values), name="li_obs_domain_valid"),
            models.CheckConstraint(condition=Q(source_type__in=EvidenceSourceType.values), name="li_obs_source_type_valid"),
            models.CheckConstraint(condition=Q(authority_class__in=EvidenceAuthorityClass.values), name="li_obs_authority_valid"),
        ]

    def clean(self):
        super().clean()
        if str(self.profile.tenant_id) != str(self.tenant_id) or str(self.profile.learner_id) != str(self.learner_id):
            raise ValidationError("Observation ownership mismatch.", code="OBSERVATION_PROFILE_MISMATCH")
        if self.status == LearningObservationStatus.CONTESTED and not self.contested_at:
            raise ValidationError("Contested observations must record contested_at.", code="OBSERVATION_CONTESTED_AT_REQUIRED")

    @property
    def is_current_for_summary(self) -> bool:
        return self.status == LearningObservationStatus.ACTIVE and self.learner_visible

    def contest(self):
        if self.status in {
            LearningObservationStatus.WITHDRAWN,
            LearningObservationStatus.INVALIDATED,
            LearningObservationStatus.SUPERSEDED,
        }:
            raise ValidationError("Terminal observations cannot be contested.", code="OBSERVATION_TERMINAL")
        self.status = LearningObservationStatus.CONTESTED
        self.contested_at = timezone.now()

    def hide(self):
        if self.status == LearningObservationStatus.ACTIVE:
            self.status = LearningObservationStatus.HIDDEN
            self.hidden_at = timezone.now()
            self.mentor_context_eligible = False


class LearningIdentityObservationSynchronization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    observation = models.ForeignKey(LearningIdentityObservation, null=True, blank=True, on_delete=models.PROTECT, related_name="synchronizations")
    profile = models.ForeignKey(LearnerLearningProfile, null=True, blank=True, on_delete=models.PROTECT, related_name="observation_synchronizations")
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="learning_identity_observation_synchronizations")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="learning_identity_observation_synchronizations")
    source_domain = models.CharField(max_length=32, choices=EvidenceSourceDomain.choices)
    source_type = models.CharField(max_length=48, choices=EvidenceSourceType.choices)
    source_identifier = models.CharField(max_length=128)
    source_revision = models.CharField(max_length=80)
    payload_fingerprint = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=ObservationSynchronizationStatus.choices)
    result_code = models.CharField(max_length=64, choices=ObservationSynchronizationResultCode.choices)
    reason_codes = models.JSONField(default=list, blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True)
    applied_at = models.DateTimeField(null=True, blank=True)
    blocked_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "source_domain", "source_type", "source_identifier"]
        indexes = [
            models.Index(fields=["tenant", "learner"], name="li_obssync_tenant_idx"),
            models.Index(fields=["source_domain", "source_type", "source_identifier"], name="li_obssync_source_idx"),
            models.Index(fields=["profile", "status"], name="li_obssync_profile_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["source_domain", "source_type", "source_identifier", "source_revision"], name="li_obssync_src_once"),
            models.UniqueConstraint(fields=["idempotency_key"], condition=~Q(idempotency_key=""), name="li_obssync_idem_once"),
            models.CheckConstraint(condition=Q(status__in=ObservationSynchronizationStatus.values), name="li_obssync_status_valid"),
            models.CheckConstraint(condition=Q(result_code__in=ObservationSynchronizationResultCode.values), name="li_obssync_result_valid"),
            models.CheckConstraint(condition=Q(payload_fingerprint__regex=r"^[0-9a-f]{64}$"), name="li_obssync_fp_valid"),
        ]


class LearningIdentityCorrectionRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(LearnerLearningProfile, on_delete=models.PROTECT, related_name="correction_requests")
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="learning_identity_correction_requests")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="learning_identity_correction_requests")
    target_attribute = models.ForeignKey(LearningIdentityAttribute, null=True, blank=True, on_delete=models.PROTECT, related_name="correction_requests")
    target_observation = models.ForeignKey(LearningIdentityObservation, null=True, blank=True, on_delete=models.PROTECT, related_name="correction_requests")
    action = models.CharField(max_length=32, choices=LearningIdentityReviewAction.choices)
    reason_code = models.CharField(max_length=64)
    learner_note = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=16, choices=LearningIdentityReviewStatus.choices, default=LearningIdentityReviewStatus.OPEN)
    resulting_profile_version = models.ForeignKey(LearningProfileVersion, null=True, blank=True, on_delete=models.PROTECT, related_name="correction_requests")
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="resolved_learning_identity_corrections")
    resolution_code = models.CharField(max_length=64, blank=True)
    idempotency_key = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["-requested_at", "id"]
        indexes = [
            models.Index(fields=["tenant", "learner", "status"], name="li_corr_tenant_status_idx"),
            models.Index(fields=["profile", "status"], name="li_corr_profile_status_idx"),
            models.Index(fields=["action", "status"], name="li_corr_action_status_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["idempotency_key"], condition=~Q(idempotency_key=""), name="li_corr_idem_once"),
            models.CheckConstraint(condition=Q(action__in=LearningIdentityReviewAction.values), name="li_corr_action_valid"),
            models.CheckConstraint(condition=Q(status__in=LearningIdentityReviewStatus.values), name="li_corr_status_valid"),
            models.CheckConstraint(
                condition=(Q(target_attribute__isnull=False) & Q(target_observation__isnull=True))
                | (Q(target_attribute__isnull=True) & Q(target_observation__isnull=False)),
                name="li_corr_one_target",
            ),
        ]

    def clean(self):
        super().clean()
        if str(self.profile.tenant_id) != str(self.tenant_id) or str(self.profile.learner_id) != str(self.learner_id):
            raise ValidationError("Correction ownership mismatch.", code="CORRECTION_PROFILE_MISMATCH")


class LearnerPreferenceSelection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(LearnerLearningProfile, on_delete=models.PROTECT, related_name="preferences")
    tenant = models.ForeignKey("users.Institution", on_delete=models.PROTECT, related_name="learning_identity_preferences")
    learner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="learning_identity_preferences")
    preference_key = models.CharField(max_length=40, choices=LearnerPreferenceKey.choices)
    value = models.JSONField()
    value_schema_version = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=16, choices=LearnerPreferenceStatus.choices, default=LearnerPreferenceStatus.ACTIVE)
    explicit = models.BooleanField(default=True)
    mentor_context_eligible = models.BooleanField(default=False)
    teaching_context_eligible = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="successor_preferences")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_learning_identity_preferences")
    created_at = models.DateTimeField(auto_now_add=True)
    withdrawn_at = models.DateTimeField(null=True, blank=True)
    withdrawal_reason_code = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ["preference_key", "-created_at", "id"]
        indexes = [
            models.Index(fields=["tenant", "learner", "status"], name="li_pref_tenant_status_idx"),
            models.Index(fields=["profile", "preference_key", "status"], name="li_pref_profile_key_idx"),
            models.Index(fields=["mentor_context_eligible", "status"], name="li_pref_mentor_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "preference_key"],
                condition=Q(status=LearnerPreferenceStatus.ACTIVE),
                name="li_pref_one_active_key",
            ),
            models.CheckConstraint(condition=Q(preference_key__in=LearnerPreferenceKey.values), name="li_pref_key_valid"),
            models.CheckConstraint(condition=Q(status__in=LearnerPreferenceStatus.values), name="li_pref_status_valid"),
            models.CheckConstraint(condition=Q(value_schema_version__gt=0), name="li_pref_schema_positive"),
        ]

    def clean(self):
        super().clean()
        if str(self.profile.tenant_id) != str(self.tenant_id) or str(self.profile.learner_id) != str(self.learner_id):
            raise ValidationError("Preference ownership mismatch.", code="PREFERENCE_PROFILE_MISMATCH")
        if self.status == LearnerPreferenceStatus.WITHDRAWN and not self.withdrawn_at:
            raise ValidationError("Withdrawn preferences must record withdrawn_at.", code="PREFERENCE_WITHDRAWN_AT_REQUIRED")

    def withdraw(self, *, reason_code: str = "LEARNER_WITHDREW"):
        if self.status == LearnerPreferenceStatus.WITHDRAWN:
            return
        self.status = LearnerPreferenceStatus.WITHDRAWN
        self.withdrawn_at = timezone.now()
        self.withdrawal_reason_code = reason_code[:64]
        self.mentor_context_eligible = False
        self.teaching_context_eligible = False
