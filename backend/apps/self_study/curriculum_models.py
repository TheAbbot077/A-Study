from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class AuthorityType(models.TextChoices):
    GOVERNMENT = "GOVERNMENT", "Government"
    NATIONAL_CURRICULUM_BODY = "NATIONAL_CURRICULUM_BODY", "National curriculum body"
    ACCREDITATION_BODY = "ACCREDITATION_BODY", "Accreditation body"
    PROFESSIONAL_BODY = "PROFESSIONAL_BODY", "Professional body"
    QUALIFICATION_PROVIDER = "QUALIFICATION_PROVIDER", "Qualification provider"
    ACCREDITED_INSTITUTION = "ACCREDITED_INSTITUTION", "Accredited institution"
    APPROVED_PUBLISHER = "APPROVED_PUBLISHER", "Approved publisher"
    OPEN_EDUCATION_PROVIDER = "OPEN_EDUCATION_PROVIDER", "Open education provider"
    ABBOT_CURATED = "ABBOT_CURATED", "Abbot curated"
    LEARNER_SUPPLIED = "LEARNER_SUPPLIED", "Learner supplied"


class VerificationStatus(models.TextChoices):
    UNVERIFIED = "UNVERIFIED", "Unverified"
    PENDING = "PENDING", "Pending"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"
    SUSPENDED = "SUSPENDED", "Suspended"


class RegistryStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    SUSPENDED = "SUSPENDED", "Suspended"
    ARCHIVED = "ARCHIVED", "Archived"


class SourceClassification(models.TextChoices):
    LEARNER_SUPPLIED_OFFICIAL = "LEARNER_SUPPLIED_OFFICIAL", "Learner supplied official"
    INSTITUTION_OR_QUALIFICATION = "INSTITUTION_OR_QUALIFICATION", "Institution or qualification"
    NATIONAL_OR_REGIONAL = "NATIONAL_OR_REGIONAL", "National or regional"
    PROFESSIONAL_OR_ACCREDITATION = "PROFESSIONAL_OR_ACCREDITATION", "Professional or accreditation"
    CURATED_REFERENCE = "CURATED_REFERENCE", "Curated reference"
    COMPOSITE = "COMPOSITE", "Composite"


class CurriculumVersionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    UNDER_REVIEW = "UNDER_REVIEW", "Under review"
    ACTIVE = "ACTIVE", "Active"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    SUSPENDED = "SUSPENDED", "Suspended"


class ProvenanceStatus(models.TextChoices):
    COMPLETE = "COMPLETE", "Complete"
    INCOMPLETE = "INCOMPLETE", "Incomplete"
    CONFLICTING = "CONFLICTING", "Conflicting"
    UNVERIFIED = "UNVERIFIED", "Unverified"


class CurriculumAuthority(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_key = models.SlugField(max_length=255, unique=True)
    name = models.CharField(max_length=255)
    authority_type = models.CharField(max_length=48, choices=AuthorityType.choices)
    jurisdictions = models.JSONField(default=list, blank=True)
    canonical_domain = models.CharField(max_length=255, blank=True)
    verification_status = models.CharField(
        max_length=16, choices=VerificationStatus.choices, default=VerificationStatus.UNVERIFIED
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="verified_curriculum_authorities"
    )
    tenant = models.ForeignKey(
        "users.Institution", null=True, blank=True, on_delete=models.PROTECT, related_name="curriculum_authorities"
    )
    status = models.CharField(max_length=16, choices=RegistryStatus.choices, default=RegistryStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "self_study_curriculum_authority"

    def verify(self, actor):
        if self.status != RegistryStatus.ACTIVE:
            raise ValidationError("Suspended authority cannot be verified.", code="CURRICULUM_AUTHORITY_NOT_VERIFIED")
        self.verification_status = VerificationStatus.VERIFIED
        self.verified_at = timezone.now()
        self.verified_by = actor

    def suspend(self):
        self.status = RegistryStatus.SUSPENDED
        self.verification_status = VerificationStatus.SUSPENDED


class CurriculumReference(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    canonical_key = models.SlugField(max_length=255)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    subject_area = models.CharField(max_length=255)
    authority = models.ForeignKey(CurriculumAuthority, on_delete=models.PROTECT, related_name="curricula")
    source_classification = models.CharField(max_length=48, choices=SourceClassification.choices)
    jurisdiction = models.CharField(max_length=64, blank=True)
    education_stage = models.CharField(max_length=64, blank=True)
    qualification_type = models.CharField(max_length=64, blank=True)
    credential_identifier = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=16)
    delivery_context = models.CharField(max_length=64, blank=True)
    tenant = models.ForeignKey(
        "users.Institution", null=True, blank=True, on_delete=models.PROTECT, related_name="curriculum_references"
    )
    status = models.CharField(max_length=16, choices=RegistryStatus.choices, default=RegistryStatus.ACTIVE)
    current_version = models.OneToOneField(
        "CurriculumVersion", null=True, blank=True, on_delete=models.PROTECT, related_name="+"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "self_study_curriculum_reference"
        constraints = [
            models.UniqueConstraint(fields=["tenant", "canonical_key"], name="self_study_curriculum_key_tenant_unique"),
            models.UniqueConstraint(
                fields=["canonical_key"],
                condition=models.Q(tenant__isnull=True),
                name="self_study_global_curriculum_key_unique",
            ),
        ]


class CurriculumVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    curriculum_reference = models.ForeignKey(CurriculumReference, on_delete=models.PROTECT, related_name="versions")
    version_label = models.CharField(max_length=64)
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)
    publication_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=CurriculumVersionStatus.choices, default=CurriculumVersionStatus.DRAFT)
    supersedes = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="superseded_by")
    canonical_source_uri = models.URLField(max_length=2048)
    source_document_id = models.UUIDField(null=True, blank=True)
    content_hash = models.CharField(max_length=128)
    licence_identifier = models.CharField(max_length=128)
    licence_uri = models.URLField(max_length=2048, blank=True)
    provenance_status = models.CharField(max_length=16, choices=ProvenanceStatus.choices, default=ProvenanceStatus.INCOMPLETE)
    language = models.CharField(max_length=16)
    official_translation_languages = models.JSONField(default=list, blank=True)
    generated_translation_permitted = models.BooleanField(default=False)
    jurisdiction = models.CharField(max_length=64, blank=True)
    education_stage = models.CharField(max_length=64, blank=True)
    qualification_type = models.CharField(max_length=64, blank=True)
    credential_identifier = models.CharField(max_length=255, blank=True)
    subject_taxonomy = models.JSONField(default=list, blank=True)
    target_outcomes_summary = models.TextField(blank=True)
    entry_expectations_summary = models.TextField(blank=True)
    estimated_duration_hours = models.PositiveIntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="created_curriculum_versions")

    class Meta:
        db_table = "self_study_curriculum_version"
        constraints = [
            models.UniqueConstraint(
                fields=["curriculum_reference", "version_label"], name="self_study_curriculum_version_label_unique"
            )
        ]

    def clean(self):
        super().clean()
        if self.effective_from and self.effective_until and self.effective_from > self.effective_until:
            raise ValidationError("Effective dates are invalid.", code="CURRICULUM_VERSION_NOT_ACTIVE")

    def activate(self):
        if self.status not in {CurriculumVersionStatus.DRAFT, CurriculumVersionStatus.UNDER_REVIEW}:
            raise ValidationError("Curriculum version cannot be activated.", code="CURRICULUM_VERSION_NOT_ACTIVE")
        if self.provenance_status != ProvenanceStatus.COMPLETE:
            raise ValidationError("Complete provenance is required.", code="CURRICULUM_PROVENANCE_INCOMPLETE")
        if self.curriculum_reference.authority.verification_status != VerificationStatus.VERIFIED:
            raise ValidationError("Verified authority is required.", code="CURRICULUM_AUTHORITY_NOT_VERIFIED")
        required = [self.canonical_source_uri, self.content_hash, self.licence_identifier, self.language]
        if not all(value.strip() for value in required):
            raise ValidationError("Version provenance is incomplete.", code="CURRICULUM_PROVENANCE_INCOMPLETE")
        self.status = CurriculumVersionStatus.ACTIVE

    def save(self, *args, **kwargs):
        if self.pk:
            prior = type(self).objects.filter(pk=self.pk).first()
            if prior and prior.status in {
                CurriculumVersionStatus.ACTIVE,
                CurriculumVersionStatus.SUPERSEDED,
                CurriculumVersionStatus.WITHDRAWN,
                CurriculumVersionStatus.SUSPENDED,
            }:
                immutable = [
                    "curriculum_reference_id", "version_label", "effective_from", "effective_until",
                    "publication_date", "canonical_source_uri", "source_document_id", "content_hash",
                    "licence_identifier", "licence_uri", "provenance_status", "language",
                    "official_translation_languages", "generated_translation_permitted", "jurisdiction",
                    "education_stage", "qualification_type", "credential_identifier", "subject_taxonomy",
                    "target_outcomes_summary", "entry_expectations_summary", "estimated_duration_hours",
                ]
                if any(getattr(prior, field) != getattr(self, field) for field in immutable):
                    raise ValidationError("Active curriculum versions are immutable.", code="CURRICULUM_VERSION_NOT_ACTIVE")
        self.full_clean()
        return super().save(*args, **kwargs)


class ResolutionAttemptStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    EVALUATING = "EVALUATING", "Evaluating"
    SELECTED = "SELECTED", "Selected"
    AWAITING_APPROVAL = "AWAITING_APPROVAL", "Awaiting approval"
    FAILED = "FAILED", "Failed"
    CANCELLED = "CANCELLED", "Cancelled"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class CurriculumResolutionAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    intent = models.ForeignKey("self_study.SelfStudyIntent", on_delete=models.PROTECT, related_name="curriculum_resolution_attempts")
    intent_version = models.PositiveIntegerField()
    policy_snapshot = models.ForeignKey(
        "self_study.EffectiveLearningPolicySnapshot", on_delete=models.PROTECT, related_name="curriculum_resolution_attempts"
    )
    requested_by = models.ForeignKey("users.User", on_delete=models.PROTECT, related_name="curriculum_resolution_attempts")
    requested_version = models.ForeignKey(
        CurriculumVersion, null=True, blank=True, on_delete=models.PROTECT, related_name="requested_by_attempts"
    )
    status = models.CharField(max_length=24, choices=ResolutionAttemptStatus.choices, default=ResolutionAttemptStatus.PENDING)
    goal_snapshot = models.TextField()
    target_credential = models.CharField(max_length=255, blank=True)
    preferred_authority = models.CharField(max_length=255, blank=True)
    jurisdiction = models.CharField(max_length=64, blank=True)
    preferred_language = models.CharField(max_length=16)
    requested_depth = models.CharField(max_length=32)
    education_context = models.CharField(max_length=64, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    algorithm_version = models.CharField(max_length=32)
    registry_snapshot_identifier = models.CharField(max_length=128, blank=True)
    idempotency_key = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_curriculum_resolution_attempt"
        constraints = [
            models.UniqueConstraint(
                fields=["intent", "intent_version", "algorithm_version"],
                name="self_study_one_resolution_per_intent_version",
            ),
            models.UniqueConstraint(fields=["intent", "idempotency_key"], name="self_study_resolution_idempotency_unique"),
        ]


class CandidateEligibility(models.TextChoices):
    ELIGIBLE = "ELIGIBLE", "Eligible"
    INELIGIBLE = "INELIGIBLE", "Ineligible"
    REQUIRES_REVIEW = "REQUIRES_REVIEW", "Requires review"


class MatchClassification(models.TextChoices):
    EXACT = "EXACT", "Exact"
    STRONG = "STRONG", "Strong"
    PARTIAL = "PARTIAL", "Partial"
    WEAK = "WEAK", "Weak"
    INCOMPATIBLE = "INCOMPATIBLE", "Incompatible"


class LanguageDisposition(models.TextChoices):
    NATIVE_LANGUAGE = "NATIVE_LANGUAGE", "Native language"
    OFFICIAL_TRANSLATION = "OFFICIAL_TRANSLATION", "Official translation"
    GENERATED_TRANSLATION_REQUIRED = "GENERATED_TRANSLATION_REQUIRED", "Generated translation required"


class CurriculumResolutionCandidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.ForeignKey(CurriculumResolutionAttempt, on_delete=models.CASCADE, related_name="candidates")
    curriculum_version = models.ForeignKey(CurriculumVersion, on_delete=models.PROTECT, related_name="resolution_candidates")
    hierarchy_rank = models.PositiveSmallIntegerField()
    eligibility = models.CharField(max_length=24, choices=CandidateEligibility.choices)
    match_classification = models.CharField(max_length=16, choices=MatchClassification.choices)
    language_disposition = models.CharField(max_length=40, choices=LanguageDisposition.choices)
    score_components = models.JSONField(default=dict)
    total_score = models.DecimalField(max_digits=6, decimal_places=2)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    requires_approval = models.BooleanField(default=False)
    rejection_reasons = models.JSONField(default=list, blank=True)
    version_status_snapshot = models.CharField(max_length=16)
    authority_verification_snapshot = models.CharField(max_length=16)
    evaluated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "self_study_curriculum_resolution_candidate"
        constraints = [
            models.UniqueConstraint(fields=["attempt", "curriculum_version"], name="self_study_resolution_candidate_unique")
        ]


class SelectionDecisionType(models.TextChoices):
    AUTOMATIC_SELECTION = "AUTOMATIC_SELECTION", "Automatic selection"
    LEARNER_CONFIRMED_SELECTION = "LEARNER_CONFIRMED_SELECTION", "Learner confirmed selection"
    INSTITUTIONAL_SELECTION = "INSTITUTIONAL_SELECTION", "Institutional selection"
    INSTITUTIONAL_OVERRIDE = "INSTITUTIONAL_OVERRIDE", "Institutional override"
    COMPOSITE_PROPOSED = "COMPOSITE_PROPOSED", "Composite proposed"


class CurriculumSelectionDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.OneToOneField(CurriculumResolutionAttempt, on_delete=models.PROTECT, related_name="selection")
    intent = models.ForeignKey("self_study.SelfStudyIntent", on_delete=models.PROTECT, related_name="curriculum_selections")
    curriculum_version = models.ForeignKey(CurriculumVersion, on_delete=models.PROTECT, related_name="selection_decisions")
    decision_type = models.CharField(max_length=40, choices=SelectionDecisionType.choices)
    hierarchy_rank = models.PositiveSmallIntegerField()
    match_classification = models.CharField(max_length=16, choices=MatchClassification.choices)
    language_disposition = models.CharField(max_length=40, choices=LanguageDisposition.choices)
    confidence = models.DecimalField(max_digits=5, decimal_places=4)
    score_components = models.JSONField(default=dict)
    reason_codes = models.JSONField(default=list)
    override_reason = models.TextField(blank=True)
    requires_approval = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="approved_curriculum_selections"
    )
    algorithm_version = models.CharField(max_length=32)
    registry_snapshot_identifier = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "self_study_curriculum_selection_decision"

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Curriculum selection decisions are immutable.", code="CURRICULUM_RESOLUTION_ALREADY_COMPLETED")
        return super().save(*args, **kwargs)


class CompositeStatus(models.TextChoices):
    PROPOSED = "PROPOSED", "Proposed"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    INVALIDATED = "INVALIDATED", "Invalidated"


class CompositeCurriculumProposal(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    attempt = models.OneToOneField(CurriculumResolutionAttempt, on_delete=models.PROTECT, related_name="composite_proposal")
    status = models.CharField(max_length=16, choices=CompositeStatus.choices, default=CompositeStatus.PROPOSED)
    rationale_codes = models.JSONField(default=list)
    requires_approval = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "users.User", null=True, blank=True, on_delete=models.PROTECT, related_name="approved_composite_curricula"
    )

    class Meta:
        db_table = "self_study_composite_curriculum_proposal"


class CompositeComponentRole(models.TextChoices):
    PRIMARY = "PRIMARY", "Primary"
    PREREQUISITE = "PREREQUISITE", "Prerequisite"
    SUPPLEMENTARY = "SUPPLEMENTARY", "Supplementary"
    SPECIALIZATION = "SPECIALIZATION", "Specialization"
    ASSESSMENT_STANDARD = "ASSESSMENT_STANDARD", "Assessment standard"


class CompositeCurriculumComponent(models.Model):
    proposal = models.ForeignKey(CompositeCurriculumProposal, on_delete=models.CASCADE, related_name="components")
    curriculum_version = models.ForeignKey(CurriculumVersion, on_delete=models.PROTECT, related_name="composite_components")
    role = models.CharField(max_length=24, choices=CompositeComponentRole.choices)
    priority = models.PositiveSmallIntegerField()
    scope_description = models.TextField()

    class Meta:
        db_table = "self_study_composite_curriculum_component"
        constraints = [
            models.UniqueConstraint(fields=["proposal", "curriculum_version"], name="self_study_composite_component_unique"),
            models.UniqueConstraint(fields=["proposal", "priority"], name="self_study_composite_priority_unique"),
        ]
