from rest_framework import serializers

from apps.assessments.domain.models import (
    Assessment,
    AssessmentDeliverySession,
    AssessmentExperience,
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


class AssessmentExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssessmentExperience
        fields = [
            "id",
            "learner",
            "learning_journey_id",
            "institution_id",
            "content_concept",
            "purpose",
            "state",
            "assessment",
            "assessment_strategy_type",
            "assessment_attempt",
            "delivery_session",
            "evaluation",
            "policy_version",
            "attempt_number",
            "previous_experience",
            "blockers",
            "current_step",
            "feedback_available",
            "failure_code",
            "ready_at",
            "started_at",
            "submitted_at",
            "evaluated_at",
            "completed_at",
            "cancelled_at",
            "expired_at",
            "failed_at",
            "created_at",
            "updated_at",
            "version",
        ]
        read_only_fields = fields


class AssessmentExperienceProductStateSerializer(serializers.Serializer):
    experience_id = serializers.CharField()
    purpose = serializers.CharField()
    status = serializers.CharField()
    current_step = serializers.JSONField()
    available_actions = serializers.ListField(child=serializers.CharField())
    blockers = serializers.ListField(child=serializers.CharField())
    attempt = serializers.JSONField()
    feedback_available = serializers.BooleanField()
    tool_policy = serializers.JSONField()
    environment = serializers.JSONField(required=False)


class AssessmentEnvironmentSerializer(serializers.Serializer):
    policy = serializers.JSONField()
    state = serializers.CharField()
    capabilities = serializers.JSONField()
    blockers = serializers.JSONField()
    resolved_at = serializers.JSONField(allow_null=True)
    source_checksum = serializers.CharField()


class AssessmentEvaluationProjectionSerializer(serializers.Serializer):
    experience_id = serializers.CharField()
    evaluation_count = serializers.IntegerField()
    latest_evaluation = serializers.JSONField(allow_null=True)
    latest_result = serializers.JSONField(allow_null=True)
    policy = serializers.JSONField(allow_null=True)
    strategy = serializers.JSONField(allow_null=True)
    projected_at = serializers.JSONField(allow_null=True)


class AssessmentEvidenceProjectionSerializer(serializers.Serializer):
    experience_id = serializers.CharField()
    evidence_count = serializers.IntegerField()
    latest_evidence = serializers.JSONField(allow_null=True)
    policy = serializers.JSONField(allow_null=True)
    target = serializers.JSONField(allow_null=True)
    projected_at = serializers.JSONField(allow_null=True)


class MasteryInterpretationSerializer(serializers.Serializer):
    learner_id = serializers.CharField()
    content_concept_id = serializers.CharField()
    policy = serializers.JSONField()
    evidence_count = serializers.IntegerField()
    authoritative_evidence_ids = serializers.ListField(child=serializers.CharField())
    current_decision = serializers.CharField()
    current_confidence = serializers.FloatField()
    state = serializers.CharField()
    explanation = serializers.CharField()
    previous_decision_id = serializers.CharField(allow_null=True, required=False)
    updated_at = serializers.CharField(allow_null=True, required=False)


class RecoveryObservationRequestSerializer(serializers.Serializer):
    learner_id = serializers.CharField()
    target_id = serializers.CharField()
    origin_target_id = serializers.CharField()
    pedagogical_decision_id = serializers.CharField(allow_null=True, required=False)
    recovery_reason = serializers.CharField()
    policy = serializers.JSONField()
    cycle_number = serializers.IntegerField()
    status = serializers.CharField()
    mastery_state = serializers.CharField()
    remediation_plan_id = serializers.CharField(allow_null=True, required=False)
    learning_journey_id = serializers.CharField(allow_null=True, required=False)
    recovery_obsolete = serializers.BooleanField()
    next_action = serializers.CharField()


class ReassessmentBlueprintSerializer(serializers.Serializer):
    target_id = serializers.CharField()
    assessment_purpose = serializers.CharField()
    recovery_reason = serializers.CharField()
    required_evidence_role = serializers.CharField()
    item_reuse_policy = serializers.CharField()
    prior_item_ids = serializers.ListField(child=serializers.CharField())
    prior_exposure_count = serializers.IntegerField()
    assessment_environment_reference = serializers.JSONField()
    policy = serializers.JSONField()


class RecoveryProjectionSerializer(serializers.Serializer):
    request = RecoveryObservationRequestSerializer()
    blueprint = ReassessmentBlueprintSerializer()


class ReconciledRecoverySerializer(serializers.Serializer):
    learner_id = serializers.CharField()
    target_id = serializers.CharField()
    recovery_status = serializers.CharField()
    reconciliation_state = serializers.CharField()
    current_mastery_state = serializers.CharField()
    current_pedagogical_decision = serializers.CharField()
    reason_code = serializers.CharField()
    recovery = serializers.JSONField()
    reconciled_at = serializers.CharField(allow_null=True, required=False)
