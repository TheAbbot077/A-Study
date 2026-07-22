from decimal import Decimal

from rest_framework import serializers

from apps.academic.models import Subject
from apps.users.models import Institution, User

from ..domain.policy import AcquisitionCandidate
from ..models import (
    EffectiveLearningPolicySnapshot,
    LearningMode,
    LearningPolicyRuleSet,
    RequestedDepth,
    SelfStudyIntent,
)


class SelfStudyIntentSerializer(serializers.ModelSerializer):
    effective_policy_snapshot_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = SelfStudyIntent
        fields = [
            "id",
            "learner_id",
            "tenant_id",
            "subject_id",
            "mode",
            "goal_statement",
            "target_title",
            "target_outcomes",
            "target_credential",
            "preferred_curriculum_authority",
            "jurisdiction",
            "preferred_language",
            "learner_age_band",
            "accessibility_requirements",
            "desired_depth",
            "pace_preference",
            "time_budget_minutes_per_week",
            "target_completion_date",
            "policy_acknowledged_at",
            "status",
            "effective_policy_snapshot_id",
            "created_at",
            "updated_at",
            "version",
        ]
        read_only_fields = [
            "id",
            "status",
            "effective_policy_snapshot_id",
            "created_at",
            "updated_at",
            "version",
        ]


class CreateIntentSerializer(serializers.Serializer):
    learner_id = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), source="learner", required=False)
    tenant_id = serializers.PrimaryKeyRelatedField(queryset=Institution.objects.all(), source="tenant")
    subject_id = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.all(), source="subject")
    mode = serializers.ChoiceField(choices=LearningMode.choices)
    goal_statement = serializers.CharField(allow_blank=True)
    target_title = serializers.CharField(required=False, allow_blank=True, default="")
    target_outcomes = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    target_credential = serializers.CharField(required=False, allow_blank=True, default="")
    preferred_curriculum_authority = serializers.CharField(required=False, allow_blank=True, default="")
    jurisdiction = serializers.CharField(required=False, allow_blank=True, default="")
    preferred_language = serializers.CharField(allow_blank=True)
    learner_age_band = serializers.CharField(required=False, allow_blank=True, default="")
    accessibility_requirements = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    desired_depth = serializers.ChoiceField(choices=RequestedDepth.choices, required=False, default=RequestedDepth.GENERAL)
    pace_preference = serializers.CharField(required=False, allow_blank=True, default="")
    time_budget_minutes_per_week = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    target_completion_date = serializers.DateField(required=False, allow_null=True)
    policy_acknowledged = serializers.BooleanField(write_only=True, required=False, default=False)


class UpdateIntentSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    goal_statement = serializers.CharField(required=False, allow_blank=True)
    target_title = serializers.CharField(required=False, allow_blank=True)
    target_outcomes = serializers.ListField(child=serializers.CharField(), required=False)
    target_credential = serializers.CharField(required=False, allow_blank=True)
    preferred_curriculum_authority = serializers.CharField(required=False, allow_blank=True)
    jurisdiction = serializers.CharField(required=False, allow_blank=True)
    preferred_language = serializers.CharField(required=False, allow_blank=True)
    learner_age_band = serializers.CharField(required=False, allow_blank=True)
    accessibility_requirements = serializers.ListField(child=serializers.CharField(), required=False)
    desired_depth = serializers.ChoiceField(choices=RequestedDepth.choices, required=False)
    pace_preference = serializers.CharField(required=False, allow_blank=True)
    time_budget_minutes_per_week = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    target_completion_date = serializers.DateField(required=False, allow_null=True)
    policy_acknowledged = serializers.BooleanField(write_only=True, required=False)


class VersionCommandSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)


class PublicPolicySerializer(serializers.ModelSerializer):
    diagnostic_disclosure = serializers.SerializerMethodField()
    acquisition = serializers.SerializerMethodField()

    class Meta:
        model = EffectiveLearningPolicySnapshot
        fields = ["id", "policy_version", "diagnostic_disclosure", "acquisition", "created_at"]

    def get_diagnostic_disclosure(self, obj):
        return {
            "purpose_disclosure_required": obj.purpose_disclosure_required,
            "learner_can_retake": obj.learner_can_retake,
            "learner_can_challenge": obj.learner_can_challenge,
            "learner_can_attempt_checkpoint": obj.learner_can_attempt_checkpoint,
            "formal_grade_effect": False,
            "transcript_effect": False,
        }

    def get_acquisition(self, obj):
        return {
            "automatic_acquisition_enabled": obj.automatic_acquisition_enabled,
            "allowed_provider_ids": obj.allowed_provider_ids,
            "allowed_source_categories": obj.allowed_source_categories,
            "allowed_licence_categories": obj.allowed_licence_categories,
            "allowed_mime_types": obj.allowed_mime_types,
            "allowed_languages": obj.allowed_languages,
            "maximum_resource_count": obj.maximum_resource_count,
            "maximum_single_file_bytes": obj.maximum_single_file_bytes,
            "maximum_total_bytes": obj.maximum_total_bytes,
            "maximum_cost": obj.maximum_cost,
            "cost_currency": obj.cost_currency,
            "paid_content_allowed": obj.paid_content_allowed,
            "unknown_licence_allowed": obj.unknown_licence_allowed,
            "link_only_when_restricted": obj.link_only_when_restricted,
            "user_approval_threshold": obj.user_approval_threshold,
            "retention_policy": obj.retention_policy,
            "external_network_access_enabled": obj.external_network_access_enabled,
            "autonomous_curriculum_fallback_allowed": obj.autonomous_curriculum_fallback_allowed,
            "curriculum_source_precedence": obj.curriculum_source_precedence,
        }


class PolicyPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPolicyRuleSet
        fields = [
            "automatic_acquisition_enabled",
            "allowed_provider_ids",
            "allowed_source_categories",
            "allowed_licence_categories",
            "allowed_mime_types",
            "allowed_languages",
            "maximum_resource_count",
            "maximum_single_file_bytes",
            "maximum_total_bytes",
            "maximum_cost",
            "cost_currency",
            "paid_content_allowed",
            "unknown_licence_allowed",
            "link_only_when_restricted",
            "user_approval_threshold",
            "retention_policy",
            "external_network_access_enabled",
            "autonomous_curriculum_fallback_allowed",
        ]

    def validate(self, attrs):
        instance = LearningPolicyRuleSet(**attrs)
        instance.authority = LearningPolicyRuleSet.Authority.LEARNER
        # Scope is validated after it is attached by the application boundary.
        for field in ("allowed_provider_ids", "allowed_source_categories", "allowed_licence_categories", "allowed_mime_types", "allowed_languages"):
            attrs.setdefault(field, [])
        return attrs


class AcquisitionCandidateSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=128)
    provider_id = serializers.CharField(max_length=255)
    source_category = serializers.CharField(max_length=64)
    licence_category = serializers.CharField(max_length=64)
    mime_type = serializers.CharField(max_length=255)
    language = serializers.CharField(max_length=16)
    file_size = serializers.IntegerField(min_value=0)
    projected_total_size = serializers.IntegerField(min_value=0)
    projected_resource_count = serializers.IntegerField(min_value=1)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0"))
    currency = serializers.CharField(min_length=3, max_length=3)
    trust_classification = serializers.CharField(max_length=64)
    network_acquisition_required = serializers.BooleanField()
    restricted = serializers.BooleanField(required=False, default=False)
    canonical_uri = serializers.URLField(required=False, allow_blank=True, max_length=2048)

    def candidate(self):
        data = dict(self.validated_data)
        data.pop("idempotency_key")
        data.pop("canonical_uri", None)
        return AcquisitionCandidate(**data)


class FallbackAuthorizationSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=128)
    resolution_failure_id = serializers.UUIDField(required=False, allow_null=True)
