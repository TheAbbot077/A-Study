from django.db import models


class LearningProfileStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ACTIVE = "ACTIVE", "Active"
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
    RESTRICTED = "RESTRICTED", "Restricted"
    ARCHIVED = "ARCHIVED", "Archived"


class ProfileVersionStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    SUPERSEDED = "SUPERSEDED", "Superseded"
    REVOKED = "REVOKED", "Revoked"


class AttributeClassification(models.TextChoices):
    DECLARED = "DECLARED", "Declared"
    VERIFIED = "VERIFIED", "Verified"
    OBSERVED = "OBSERVED", "Observed"
    DERIVED = "DERIVED", "Derived"


class LearningAttributeType(models.TextChoices):
    PREFERRED_LEARNING_LANGUAGE = "PREFERRED_LEARNING_LANGUAGE", "Preferred learning language"
    TARGET_QUALIFICATION = "TARGET_QUALIFICATION", "Target qualification"
    TARGET_EXAM_DATE = "TARGET_EXAM_DATE", "Target exam date"
    WEEKLY_STUDY_CAPACITY = "WEEKLY_STUDY_CAPACITY", "Weekly study capacity"
    PRIOR_STUDY_EXPERIENCE = "PRIOR_STUDY_EXPERIENCE", "Prior study experience"
    ACCESSIBILITY_PREFERENCE = "ACCESSIBILITY_PREFERENCE", "Accessibility preference"
    STUDY_GOAL = "STUDY_GOAL", "Study goal"
    PREFERRED_EXPLANATION_FORMAT = "PREFERRED_EXPLANATION_FORMAT", "Preferred explanation format"
    PACING_SUPPORT_PREFERENCE = "PACING_SUPPORT_PREFERENCE", "Pacing support preference"


class AttributeVisibility(models.TextChoices):
    LEARNER_VISIBLE = "LEARNER_VISIBLE", "Learner visible"
    AUTHORIZED_STAFF = "AUTHORIZED_STAFF", "Authorized staff"
    RESTRICTED = "RESTRICTED", "Restricted"
    SYSTEM_ONLY = "SYSTEM_ONLY", "System only"


class AttributeSourceType(models.TextChoices):
    LEARNER = "LEARNER", "Learner"
    AUTHORIZED_ACTOR = "AUTHORIZED_ACTOR", "Authorized actor"
    INSTITUTION = "INSTITUTION", "Institution"
    ONBOARDING = "ONBOARDING", "Onboarding"
    DIAGNOSTIC = "DIAGNOSTIC", "Diagnostic"
    ASSESSMENT = "ASSESSMENT", "Assessment"
    LEARNING_SESSION = "LEARNING_SESSION", "Learning session"
    SYSTEM_DERIVATION = "SYSTEM_DERIVATION", "System derivation"


class EvidenceSourceDomain(models.TextChoices):
    IDENTITY = "IDENTITY", "Identity"
    SELF_STUDY = "SELF_STUDY", "Self-study"
    ACADEMIC = "ACADEMIC", "Academic"
    LEARNING = "LEARNING", "Learning"
    ASSESSMENT = "ASSESSMENT", "Assessment"
    DIAGNOSTIC = "DIAGNOSTIC", "Diagnostic"
    INSTITUTION = "INSTITUTION", "Institution"
    LEARNING_IDENTITY = "LEARNING_IDENTITY", "Learning identity"


class EvidenceSourceType(models.TextChoices):
    LEARNER_DECLARATION = "LEARNER_DECLARATION", "Learner declaration"
    ONBOARDING_CONTEXT = "ONBOARDING_CONTEXT", "Onboarding context"
    INSTITUTIONAL_MEMBERSHIP = "INSTITUTIONAL_MEMBERSHIP", "Institutional membership"
    DIAGNOSTIC_ATTEMPT = "DIAGNOSTIC_ATTEMPT", "Diagnostic attempt"
    DIAGNOSTIC_EVIDENCE = "DIAGNOSTIC_EVIDENCE", "Diagnostic evidence"
    ASSESSMENT_ATTEMPT = "ASSESSMENT_ATTEMPT", "Assessment attempt"
    ASSESSMENT_EVIDENCE = "ASSESSMENT_EVIDENCE", "Assessment evidence"
    MASTERY_EVIDENCE = "MASTERY_EVIDENCE", "Mastery evidence"
    LEARNING_SESSION = "LEARNING_SESSION", "Learning session"
    LEARNING_TURN = "LEARNING_TURN", "Learning turn"
    PROFILE_CORRECTION = "PROFILE_CORRECTION", "Profile correction"


class EvidenceRelationship(models.TextChoices):
    SUPPORTS = "SUPPORTS", "Supports"
    CONTRADICTS = "CONTRADICTS", "Contradicts"
    CONFIRMS = "CONFIRMS", "Confirms"
    SUPERSEDES = "SUPERSEDES", "Supersedes"
    CONTEXTUALIZES = "CONTEXTUALIZES", "Contextualizes"


class EvidenceAuthorityClass(models.TextChoices):
    DECLARATIVE = "DECLARATIVE", "Declarative"
    INSTITUTIONAL = "INSTITUTIONAL", "Institutional"
    ASSESSMENT = "ASSESSMENT", "Assessment"
    DIAGNOSTIC = "DIAGNOSTIC", "Diagnostic"
    OBSERVATIONAL = "OBSERVATIONAL", "Observational"
    DERIVED = "DERIVED", "Derived"
    SYSTEM = "SYSTEM", "System"


class EvidenceLinkStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    STALE = "STALE", "Stale"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    INVALIDATED = "INVALIDATED", "Invalidated"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class ProvenanceReadinessStatus(models.TextChoices):
    READY = "READY", "Ready"
    NEEDS_REVIEW = "NEEDS_REVIEW", "Needs review"
    BLOCKED = "BLOCKED", "Blocked"


class ProvenanceReasonCode(models.TextChoices):
    DECLARATION_SOURCE_REQUIRED = "DECLARATION_SOURCE_REQUIRED", "Declaration source required"
    AUTHORITATIVE_EVIDENCE_REQUIRED = "AUTHORITATIVE_EVIDENCE_REQUIRED", "Authoritative evidence required"
    GOVERNED_EVIDENCE_REQUIRED = "GOVERNED_EVIDENCE_REQUIRED", "Governed evidence required"
    DERIVATION_POLICY_REQUIRED = "DERIVATION_POLICY_REQUIRED", "Derivation policy required"
    CONFIDENCE_REQUIRED = "CONFIDENCE_REQUIRED", "Confidence required"
    SOURCE_TYPE_UNSUPPORTED = "SOURCE_TYPE_UNSUPPORTED", "Source type unsupported"
    SOURCE_NOT_FOUND = "SOURCE_NOT_FOUND", "Source not found"
    SOURCE_INACTIVE = "SOURCE_INACTIVE", "Source inactive"
    SOURCE_REVOKED = "SOURCE_REVOKED", "Source revoked"
    SOURCE_INVALIDATED = "SOURCE_INVALIDATED", "Source invalidated"
    SOURCE_WITHDRAWN = "SOURCE_WITHDRAWN", "Source withdrawn"
    SOURCE_STALE = "SOURCE_STALE", "Source stale"
    SOURCE_TENANT_MISMATCH = "SOURCE_TENANT_MISMATCH", "Source tenant mismatch"
    SOURCE_LEARNER_MISMATCH = "SOURCE_LEARNER_MISMATCH", "Source learner mismatch"
    SOURCE_AUTHORITY_INSUFFICIENT = "SOURCE_AUTHORITY_INSUFFICIENT", "Source authority insufficient"
    SOURCE_RELATIONSHIP_INVALID = "SOURCE_RELATIONSHIP_INVALID", "Source relationship invalid"
    CONTRADICTORY_EVIDENCE = "CONTRADICTORY_EVIDENCE", "Contradictory evidence"
    UNRESOLVED_SUPERSESSION = "UNRESOLVED_SUPERSESSION", "Unresolved supersession"
    RESTRICTED_SOURCE_VISIBILITY = "RESTRICTED_SOURCE_VISIBILITY", "Restricted source visibility"
    SOURCE_VALIDITY_EXPIRED = "SOURCE_VALIDITY_EXPIRED", "Source validity expired"


class OnboardingDeclarationDisposition(models.TextChoices):
    EXPLICITLY_DECLARED = "EXPLICITLY_DECLARED", "Explicitly declared"
    EXPLICITLY_CONFIRMED = "EXPLICITLY_CONFIRMED", "Explicitly confirmed"
    SYSTEM_NORMALIZED = "SYSTEM_NORMALIZED", "System normalized"
    INFERRED = "INFERRED", "Inferred"
    UNRESOLVED = "UNRESOLVED", "Unresolved"
    REJECTED = "REJECTED", "Rejected"


class DeclarationChangeType(models.TextChoices):
    ADDED = "ADDED", "Added"
    UPDATED = "UPDATED", "Updated"
    UNCHANGED = "UNCHANGED", "Unchanged"
    CLEARED = "CLEARED", "Cleared"
    REJECTED = "REJECTED", "Rejected"
    BLOCKED = "BLOCKED", "Blocked"
    REQUIRES_REVIEW = "REQUIRES_REVIEW", "Requires review"


class DeclarationFieldStatus(models.TextChoices):
    ELIGIBLE = "ELIGIBLE", "Eligible"
    UNCHANGED = "UNCHANGED", "Unchanged"
    REJECTED = "REJECTED", "Rejected"
    BLOCKED = "BLOCKED", "Blocked"
    REQUIRES_REVIEW = "REQUIRES_REVIEW", "Requires review"
    EXPLICITLY_CLEARED = "EXPLICITLY_CLEARED", "Explicitly cleared"
    NOT_PROVIDED = "NOT_PROVIDED", "Not provided"


class DeclarationSynchronizationStatus(models.TextChoices):
    APPLIED = "APPLIED", "Applied"
    NO_CHANGE = "NO_CHANGE", "No change"
    BLOCKED = "BLOCKED", "Blocked"
    FAILED = "FAILED", "Failed"


class DeclarationSynchronizationResultCode(models.TextChoices):
    APPLIED = "APPLIED", "Applied"
    NO_CHANGE = "NO_CHANGE", "No change"
    BLOCKED = "BLOCKED", "Blocked"
    FAILED = "FAILED", "Failed"
    ONBOARDING_REVISION_STALE = "ONBOARDING_REVISION_STALE", "Onboarding revision stale"
    ONBOARDING_REVISION_ALREADY_APPLIED = "ONBOARDING_REVISION_ALREADY_APPLIED", "Onboarding revision already applied"
    ONBOARDING_REVISION_PAYLOAD_CONFLICT = "ONBOARDING_REVISION_PAYLOAD_CONFLICT", "Onboarding revision payload conflict"
    ONBOARDING_REVISION_UNAVAILABLE = "ONBOARDING_REVISION_UNAVAILABLE", "Onboarding revision unavailable"
    ONBOARDING_SOURCE_NOT_FOUND = "ONBOARDING_SOURCE_NOT_FOUND", "Onboarding source not found"
    ONBOARDING_NOT_COMPLETED = "ONBOARDING_NOT_COMPLETED", "Onboarding not completed"
    TENANT_MISMATCH = "TENANT_MISMATCH", "Tenant mismatch"
    LEARNER_MISMATCH = "LEARNER_MISMATCH", "Learner mismatch"
    UNRELATED_DRAFT_EXISTS = "UNRELATED_DRAFT_EXISTS", "Unrelated draft exists"
    PROFILE_VERSION_CONFLICT = "PROFILE_VERSION_CONFLICT", "Profile version conflict"
    PROVENANCE_BLOCKED = "PROVENANCE_BLOCKED", "Provenance blocked"
    PROVENANCE_REVIEW_REQUIRED = "PROVENANCE_REVIEW_REQUIRED", "Provenance review required"


class LearningObservationType(models.TextChoices):
    DIAGNOSTIC_COMPLETED = "DIAGNOSTIC_COMPLETED", "Diagnostic completed"
    LEARNING_SESSION_COMPLETED = "LEARNING_SESSION_COMPLETED", "Learning session completed"
    LEARNING_SESSION_RESUMED = "LEARNING_SESSION_RESUMED", "Learning session resumed"
    EXPLANATION_REVISITED = "EXPLANATION_REVISITED", "Explanation revisited"
    STUDY_ACTIVITY_RECORDED = "STUDY_ACTIVITY_RECORDED", "Study activity recorded"


class LearningObservationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    CONTESTED = "CONTESTED", "Contested"
    HIDDEN = "HIDDEN", "Hidden"
    STALE = "STALE", "Stale"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    INVALIDATED = "INVALIDATED", "Invalidated"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class ObservationSynchronizationStatus(models.TextChoices):
    APPLIED = "APPLIED", "Applied"
    UNCHANGED = "UNCHANGED", "Unchanged"
    BLOCKED = "BLOCKED", "Blocked"
    FAILED = "FAILED", "Failed"


class ObservationSynchronizationResultCode(models.TextChoices):
    CREATED = "CREATED", "Created"
    UPDATED = "UPDATED", "Updated"
    UNCHANGED = "UNCHANGED", "Unchanged"
    DUPLICATE = "DUPLICATE", "Duplicate"
    STALE_SOURCE_REVISION = "STALE_SOURCE_REVISION", "Stale source revision"
    UNSUPPORTED_SOURCE_TYPE = "UNSUPPORTED_SOURCE_TYPE", "Unsupported source type"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE", "Source unavailable"
    SOURCE_WITHDRAWN = "SOURCE_WITHDRAWN", "Source withdrawn"
    INVALID_PROVENANCE = "INVALID_PROVENANCE", "Invalid provenance"
    BLOCKED_BY_POLICY = "BLOCKED_BY_POLICY", "Blocked by policy"
    REJECTED_UNSAFE_PAYLOAD = "REJECTED_UNSAFE_PAYLOAD", "Rejected unsafe payload"
    PUBLICATION_DEFERRED = "PUBLICATION_DEFERRED", "Publication deferred"


class LearningIdentityReviewAction(models.TextChoices):
    REPLACE_DECLARATION = "REPLACE_DECLARATION", "Replace declaration"
    WITHDRAW_DECLARATION = "WITHDRAW_DECLARATION", "Withdraw declaration"
    CONTEST_OBSERVATION = "CONTEST_OBSERVATION", "Contest observation"
    REQUEST_CORRECTION = "REQUEST_CORRECTION", "Request correction"
    HIDE_OBSERVATION = "HIDE_OBSERVATION", "Hide observation"


class LearningIdentityReviewStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    RESOLVED = "RESOLVED", "Resolved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled"


class LearnerPreferenceKey(models.TextChoices):
    EXPLANATION_MODE = "EXPLANATION_MODE", "Explanation mode"
    TEACHING_PACE = "TEACHING_PACE", "Teaching pace"
    INTERFACE_LANGUAGE = "INTERFACE_LANGUAGE", "Interface language"
    SESSION_LENGTH = "SESSION_LENGTH", "Session length"
    REDUCED_MOTION = "REDUCED_MOTION", "Reduced motion"
    HIGH_CONTRAST = "HIGH_CONTRAST", "High contrast"
    LARGER_TEXT = "LARGER_TEXT", "Larger text"
    CAPTIONS = "CAPTIONS", "Captions"


class LearnerPreferenceStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class MentorContextPurpose(models.TextChoices):
    SESSION_OPENING = "SESSION_OPENING", "Session opening"
    TEACHING_PERSONALIZATION = "TEACHING_PERSONALIZATION", "Teaching personalization"
    LEARNER_PROFILE_DISPLAY = "LEARNER_PROFILE_DISPLAY", "Learner profile display"
    STUDY_PLANNING = "STUDY_PLANNING", "Study planning"
    NOTIFICATION_PERSONALIZATION = "NOTIFICATION_PERSONALIZATION", "Notification personalization"


class LearningIdentityTimelineEventType(models.TextChoices):
    DECLARATION_ADDED = "DECLARATION_ADDED", "Declaration added"
    DECLARATION_UPDATED = "DECLARATION_UPDATED", "Declaration updated"
    DECLARATION_WITHDRAWN = "DECLARATION_WITHDRAWN", "Declaration withdrawn"
    OBSERVATION_RECORDED = "OBSERVATION_RECORDED", "Observation recorded"
    OBSERVATION_CONTESTED = "OBSERVATION_CONTESTED", "Observation contested"
    CORRECTION_RESOLVED = "CORRECTION_RESOLVED", "Correction resolved"
    PREFERENCE_SELECTED = "PREFERENCE_SELECTED", "Preference selected"
    PREFERENCE_UPDATED = "PREFERENCE_UPDATED", "Preference updated"
    PREFERENCE_WITHDRAWN = "PREFERENCE_WITHDRAWN", "Preference withdrawn"
    PROFILE_PUBLISHED = "PROFILE_PUBLISHED", "Profile published"
