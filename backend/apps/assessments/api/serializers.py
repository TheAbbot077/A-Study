from rest_framework import serializers

from apps.assessments.domain.models import (
    Assessment,
    AssessmentDeliverySession,
    AssessmentResult,
    LearningEvidence,
    MasteryProfile,
)
from apps.remediation.domain.models import RemediationPlan


class AssessmentSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = ["id", "content_concept", "title", "description", "state", "metadata", "created_at", "updated_at"]
        read_only_fields = fields


class AssessmentDeliverySessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentDeliverySession
        fields = [
            "id",
            "assessment",
            "learner",
            "assessment_attempt",
            "status",
            "current_sequence_number",
            "started_at",
            "submitted_at",
            "completed_at",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AssessmentOptionSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    content = serializers.CharField()


class AssessmentQuestionSerializer(serializers.Serializer):
    id = serializers.CharField()
    sequence_number = serializers.IntegerField()
    item_type = serializers.CharField()
    prompt = serializers.CharField()
    options = AssessmentOptionSerializer(many=True, required=False)
    response_data = serializers.JSONField(required=False)
    submitted = serializers.BooleanField()
    source_type = serializers.CharField()


class AssessmentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentResult
        fields = ["id", "attempt", "total_score", "max_score", "percentage", "passed", "result_data", "created_at", "updated_at"]
        read_only_fields = fields


class MasteryProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = MasteryProfile
        fields = ["id", "learner", "content_concept", "current_decision", "confidence", "evidence_count", "last_evidence_at", "created_at", "updated_at"]
        read_only_fields = fields


class LearningEvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningEvidence
        fields = ["id", "source_type", "source_id", "evidence_type", "score", "confidence", "metadata", "created_at"]
        read_only_fields = fields


class RemediationPlanSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = RemediationPlan
        fields = [
            "id",
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
        ]
        read_only_fields = fields


class MasteryCheckSnapshotSerializer(serializers.Serializer):
    content_concept_id = serializers.CharField()
    assessment = AssessmentSummarySerializer(allow_null=True)
    delivery_session = AssessmentDeliverySessionSerializer(allow_null=True)
    questions = AssessmentQuestionSerializer(many=True)
    current_question_id = serializers.CharField(allow_null=True)
    result = AssessmentResultSerializer(allow_null=True)
    mastery_profile = MasteryProfileSerializer(allow_null=True)
    evidence = LearningEvidenceSerializer(many=True)
    remediation_plan = serializers.JSONField(allow_null=True)
    next_available_concept_id = serializers.CharField(allow_null=True)
    next_available_concept_title = serializers.CharField(allow_null=True)
    can_start = serializers.BooleanField()
    can_submit = serializers.BooleanField()
    is_complete = serializers.BooleanField()


class StartMasteryCheckSerializer(serializers.Serializer):
    content_concept = serializers.UUIDField()


class SubmitAssessmentAnswerSerializer(serializers.Serializer):
    item_id = serializers.UUIDField()
    response_data = serializers.JSONField()
