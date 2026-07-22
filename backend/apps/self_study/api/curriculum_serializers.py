from rest_framework import serializers

from apps.users.models import Institution

from ..curriculum_models import (
    CurriculumAuthority,
    CurriculumReference,
    CurriculumResolutionAttempt,
    CurriculumVersion,
)


class CurriculumAuthoritySerializer(serializers.ModelSerializer):
    tenant_id = serializers.PrimaryKeyRelatedField(
        source="tenant", queryset=Institution.objects.all(), required=False, allow_null=True
    )

    class Meta:
        model = CurriculumAuthority
        fields = [
            "id", "canonical_key", "name", "authority_type", "jurisdictions",
            "canonical_domain", "verification_status", "tenant_id", "status",
            "verified_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "verification_status", "status", "verified_at", "created_at", "updated_at"]


class CurriculumReferenceSerializer(serializers.ModelSerializer):
    authority_id = serializers.PrimaryKeyRelatedField(
        source="authority", queryset=CurriculumAuthority.objects.all()
    )
    tenant_id = serializers.PrimaryKeyRelatedField(
        source="tenant", queryset=Institution.objects.all(), required=False, allow_null=True
    )
    authority_name = serializers.CharField(source="authority.name", read_only=True)
    current_version_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = CurriculumReference
        fields = [
            "id", "canonical_key", "title", "description", "subject_area",
            "authority_id", "authority_name", "source_classification",
            "jurisdiction", "education_stage", "qualification_type",
            "credential_identifier", "language", "delivery_context", "tenant_id",
            "status", "current_version_id", "version", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "status", "current_version_id", "version", "created_at", "updated_at"]


class CurriculumVersionSerializer(serializers.ModelSerializer):
    authority_name = serializers.CharField(source="curriculum_reference.authority.name", read_only=True)
    curriculum_title = serializers.CharField(source="curriculum_reference.title", read_only=True)
    source_classification = serializers.CharField(source="curriculum_reference.source_classification", read_only=True)

    class Meta:
        model = CurriculumVersion
        fields = [
            "id", "curriculum_reference_id", "curriculum_title", "authority_name",
            "source_classification", "version_label", "effective_from", "effective_until",
            "publication_date", "status", "supersedes_id", "canonical_source_uri",
            "source_document_id", "content_hash", "licence_identifier", "licence_uri",
            "provenance_status", "language", "official_translation_languages",
            "generated_translation_permitted", "jurisdiction", "education_stage",
            "qualification_type", "credential_identifier", "subject_taxonomy",
            "target_outcomes_summary", "entry_expectations_summary",
            "estimated_duration_hours", "created_at",
        ]
        read_only_fields = ["id", "curriculum_reference_id", "status", "created_at"]


class CreateCurriculumVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurriculumVersion
        exclude = ["id", "curriculum_reference", "created_by", "created_at", "status", "supersedes"]


class StartResolutionSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=128)
    requested_version_id = serializers.UUIDField(required=False, allow_null=True)

    def validate(self, attrs):
        unexpected = set(self.initial_data) - {"idempotency_key", "requested_version_id"}
        if unexpected:
            raise serializers.ValidationError(
                {"code": "CURRICULUM_RESOLUTION_ACCESS_DENIED", "detail": "Resolver outcomes are server-controlled."}
            )
        return attrs


class SupersedeCurriculumVersionSerializer(serializers.Serializer):
    replacement_version_id = serializers.UUIDField()


class ConfirmCurriculumSelectionSerializer(serializers.Serializer):
    curriculum_version_id = serializers.UUIDField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class CandidatePublicSerializer(serializers.Serializer):
    curriculum_version_id = serializers.UUIDField()
    curriculum_title = serializers.CharField()
    authority = serializers.CharField()
    version_label = serializers.CharField()
    source_classification = serializers.CharField()
    hierarchy_rank = serializers.IntegerField()
    eligibility = serializers.CharField()
    match_classification = serializers.CharField()
    language_disposition = serializers.CharField()
    requires_approval = serializers.BooleanField()
    rejection_reasons = serializers.ListField(child=serializers.CharField())


def resolution_payload(attempt: CurriculumResolutionAttempt):
    candidates = [
        {
            "curriculum_version_id": item.curriculum_version_id,
            "curriculum_title": item.curriculum_version.curriculum_reference.title,
            "authority": item.curriculum_version.curriculum_reference.authority.name,
            "version_label": item.curriculum_version.version_label,
            "source_classification": item.curriculum_version.curriculum_reference.source_classification,
            "hierarchy_rank": item.hierarchy_rank,
            "eligibility": item.eligibility,
            "match_classification": item.match_classification,
            "language_disposition": item.language_disposition,
            "requires_approval": item.requires_approval,
            "rejection_reasons": item.rejection_reasons,
        }
        for item in attempt.candidates.select_related(
            "curriculum_version__curriculum_reference__authority"
        ).order_by("hierarchy_rank", "-total_score", "id")
    ]
    payload = {
        "id": attempt.id,
        "intent_id": attempt.intent_id,
        "intent_version": attempt.intent_version,
        "policy_snapshot_id": attempt.policy_snapshot_id,
        "status": attempt.status,
        "algorithm_version": attempt.algorithm_version,
        "registry_snapshot_identifier": attempt.registry_snapshot_identifier,
        "requested_version_id": attempt.requested_version_id,
        "candidates": CandidatePublicSerializer(candidates, many=True).data,
        "started_at": attempt.started_at,
        "completed_at": attempt.completed_at,
    }
    if hasattr(attempt, "selection"):
        payload["selection"] = {
            "id": attempt.selection.id,
            "curriculum_version_id": attempt.selection.curriculum_version_id,
            "decision_type": attempt.selection.decision_type,
            "match_classification": attempt.selection.match_classification,
            "language_disposition": attempt.selection.language_disposition,
            "requires_approval": attempt.selection.requires_approval,
            "reason_codes": attempt.selection.reason_codes,
        }
    if hasattr(attempt, "composite_proposal"):
        payload["composite"] = {
            "id": attempt.composite_proposal.id,
            "status": attempt.composite_proposal.status,
            "requires_approval": attempt.composite_proposal.requires_approval,
            "rationale_codes": attempt.composite_proposal.rationale_codes,
        }
    if hasattr(attempt, "resolution_failure"):
        payload["failure"] = {
            "id": attempt.resolution_failure.id,
            "reason_codes": attempt.resolution_failure.reason_codes,
        }
    return payload
