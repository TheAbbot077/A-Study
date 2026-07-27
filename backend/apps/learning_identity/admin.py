from django.contrib import admin

from apps.learning_identity.domain.models import (
    LearnerLearningProfile,
    LearnerPreferenceSelection,
    LearningIdentityAttribute,
    LearningIdentityCommandRecord,
    LearningIdentityCorrectionRequest,
    LearningIdentityDeclarationSynchronization,
    LearningIdentityEvidenceLink,
    LearningIdentityObservation,
    LearningIdentityObservationSynchronization,
    LearningProfileVersion,
)


@admin.register(LearnerLearningProfile)
class LearnerLearningProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "tenant", "learner", "status", "current_version", "version", "updated_at")
    list_filter = ("status", "tenant", "created_at", "updated_at")
    search_fields = ("learner__email", "tenant__name")
    readonly_fields = (
        "id",
        "tenant",
        "learner",
        "status",
        "current_version",
        "version",
        "created_at",
        "updated_at",
        "last_reviewed_at",
        "archived_at",
        "restricted_at",
        "restriction_reason",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LearningProfileVersion)
class LearningProfileVersionAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "version_number", "status", "created_by", "published_by", "published_at")
    list_filter = ("status", "created_at", "published_at")
    search_fields = ("profile__learner__email", "profile__tenant__name")
    readonly_fields = (
        "id",
        "profile",
        "version_number",
        "status",
        "summary",
        "source_revision",
        "supersedes_version",
        "created_by",
        "created_at",
        "published_by",
        "published_at",
        "superseded_at",
        "revoked_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LearningIdentityAttribute)
class LearningIdentityAttributeAdmin(admin.ModelAdmin):
    list_display = ("id", "profile_version", "attribute_type", "classification", "visibility", "restricted", "created_at")
    list_filter = ("attribute_type", "classification", "visibility", "restricted", "created_at")
    search_fields = ("profile_version__profile__learner__email", "profile_version__profile__tenant__name")
    readonly_fields = (
        "id",
        "profile_version",
        "attribute_type",
        "classification",
        "value",
        "value_schema_version",
        "confidence",
        "source_type",
        "source_reference",
        "declared_at",
        "valid_from",
        "valid_until",
        "visibility",
        "review_required",
        "restricted",
        "created_by",
        "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LearningIdentityCommandRecord)
class LearningIdentityCommandRecordAdmin(admin.ModelAdmin):
    list_display = ("scope", "idempotency_key", "result_model", "result_id", "created_at")
    list_filter = ("scope", "result_model", "created_at")
    search_fields = ("idempotency_key", "result_id")
    readonly_fields = ("id", "scope", "idempotency_key", "payload_fingerprint", "result_model", "result_id", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LearningIdentityDeclarationSynchronization)
class LearningIdentityDeclarationSynchronizationAdmin(admin.ModelAdmin):
    exclude = ("payload_fingerprint",)
    list_display = (
        "id",
        "profile",
        "profile_version",
        "tenant",
        "learner",
        "onboarding_session_id",
        "onboarding_revision",
        "status",
        "result_code",
        "readiness_status",
        "applied_at",
        "created_at",
    )
    list_filter = ("status", "result_code", "readiness_status", "created_at", "applied_at")
    search_fields = ("onboarding_session_id", "source_event_id", "learner__email", "tenant__name")
    readonly_fields = (
        "id",
        "profile",
        "profile_version",
        "tenant",
        "learner",
        "onboarding_session_id",
        "onboarding_revision",
        "source_event_id",
        "source_schema_version",
        "status",
        "result_code",
        "readiness_status",
        "change_counts",
        "reason_codes",
        "idempotency_key",
        "applied_at",
        "blocked_at",
        "failed_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LearningIdentityEvidenceLink)
class LearningIdentityEvidenceLinkAdmin(admin.ModelAdmin):
    list_display = ("id", "attribute", "source_domain", "source_type", "relationship", "authority_class", "status", "linked_at")
    list_filter = ("source_domain", "source_type", "relationship", "authority_class", "status", "summary_visibility", "created_at")
    search_fields = ("source_identifier", "safe_summary", "attribute__profile_version__profile__learner__email")
    readonly_fields = (
        "id",
        "attribute",
        "source_domain",
        "source_type",
        "source_identifier",
        "source_revision",
        "relationship",
        "authority_class",
        "status",
        "source_observed_at",
        "valid_from",
        "valid_until",
        "freshness_expires_at",
        "weight",
        "confidence_contribution",
        "safe_summary",
        "summary_visibility",
        "metadata_schema_version",
        "linked_by",
        "linked_at",
        "withdrawn_by",
        "withdrawn_at",
        "withdrawal_reason_code",
        "invalidated_by",
        "invalidated_at",
        "invalidation_reason_code",
        "superseded_by_link",
        "superseded_at",
        "review_required",
        "reason_codes",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LearningIdentityObservation)
class LearningIdentityObservationAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "observation_type", "status", "source_type", "occurred_at")
    list_filter = ("observation_type", "status", "source_domain", "source_type", "mentor_context_eligible")
    search_fields = ("safe_title", "safe_summary", "source_identifier", "learner__email")
    readonly_fields = [field.name for field in LearningIdentityObservation._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LearningIdentityObservationSynchronization)
class LearningIdentityObservationSynchronizationAdmin(admin.ModelAdmin):
    exclude = ("payload_fingerprint",)
    list_display = ("id", "source_domain", "source_type", "status", "result_code", "created_at")
    list_filter = ("status", "result_code", "source_domain", "source_type")
    search_fields = ("source_identifier", "learner__email")
    readonly_fields = [field.name for field in LearningIdentityObservationSynchronization._meta.fields if field.name != "payload_fingerprint"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LearningIdentityCorrectionRequest)
class LearningIdentityCorrectionRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "action", "status", "reason_code", "requested_at")
    list_filter = ("action", "status", "reason_code")
    search_fields = ("learner__email", "reason_code", "learner_note")
    readonly_fields = [field.name for field in LearningIdentityCorrectionRequest._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(LearnerPreferenceSelection)
class LearnerPreferenceSelectionAdmin(admin.ModelAdmin):
    list_display = ("id", "profile", "preference_key", "status", "explicit", "created_at")
    list_filter = ("preference_key", "status", "mentor_context_eligible", "teaching_context_eligible")
    search_fields = ("learner__email", "preference_key")
    readonly_fields = [field.name for field in LearnerPreferenceSelection._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
