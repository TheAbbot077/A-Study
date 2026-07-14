from rest_framework import serializers

from apps.academic.domain.models import ContentConcept
from apps.assessments.domain.models import LearningEvidence
from apps.remediation.domain.models import (
    RemediationActivity,
    RemediationAttempt,
    RemediationOutcome,
    RemediationPlan,
    RemediationRecommendation,
)


class RemediationRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemediationRecommendation
        fields = ["id", "plan", "recommendation_type", "title", "rationale", "priority", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class RemediationActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RemediationActivity
        fields = [
            "id",
            "plan",
            "recommendation",
            "activity_type",
            "title",
            "instructions",
            "status",
            "evidence_producer_type",
            "evidence_reference_id",
            "resource",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class RemediationAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemediationAttempt
        fields = ["id", "activity", "learner", "status", "started_at", "completed_at", "metadata", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class RemediationOutcomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemediationOutcome
        fields = ["id", "plan", "activity", "outcome", "supporting_evidence", "notes", "metadata", "recorded_at", "created_at"]
        read_only_fields = ["id", "created_at"]


class RemediationPlanSerializer(serializers.ModelSerializer):
    recommendations = RemediationRecommendationSerializer(many=True, read_only=True)
    activities = RemediationActivitySerializer(many=True, read_only=True)
    outcomes = RemediationOutcomeSerializer(many=True, read_only=True)

    class Meta:
        model = RemediationPlan
        fields = [
            "id",
            "learner",
            "content_concept",
            "status",
            "trigger_evidence",
            "rationale",
            "metadata",
            "started_at",
            "completed_at",
            "escalated_at",
            "cancelled_at",
            "closed_at",
            "created_at",
            "updated_at",
            "recommendations",
            "activities",
            "outcomes",
        ]
        read_only_fields = [
            "id",
            "status",
            "started_at",
            "completed_at",
            "escalated_at",
            "cancelled_at",
            "closed_at",
            "created_at",
            "updated_at",
            "recommendations",
            "activities",
            "outcomes",
        ]


class CreateRemediationPlanSerializer(serializers.Serializer):
    evidence = serializers.PrimaryKeyRelatedField(queryset=LearningEvidence.objects.all(), required=False, allow_null=True)
    learner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    content_concept = serializers.PrimaryKeyRelatedField(queryset=ContentConcept.objects.all(), required=False)
    rationale = serializers.CharField(required=False, allow_blank=True, default="")
    metadata = serializers.JSONField(required=False, default=dict)


class PlanActionSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, default="")
