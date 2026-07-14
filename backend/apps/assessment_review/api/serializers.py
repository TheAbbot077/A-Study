from rest_framework import serializers

from apps.assessment_review.domain.models import (
    AssessmentReview,
    DifficultyCalibration,
    QualityFinding,
    QuestionReview,
    ReviewDecision,
    ReviewerAssignment,
)


class QualityFindingSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        linked_count = int(bool(attrs.get("assessment_review"))) + int(bool(attrs.get("question_review")))
        if linked_count != 1:
            raise serializers.ValidationError("Provide exactly one of assessment_review or question_review.")
        return attrs

    class Meta:
        model = QualityFinding
        fields = [
            "id",
            "assessment_review",
            "question_review",
            "finding_type",
            "severity",
            "description",
            "resolved",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ReviewDecisionSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        linked_count = int(bool(attrs.get("assessment_review"))) + int(bool(attrs.get("question_review")))
        if linked_count != 1:
            raise serializers.ValidationError("Provide exactly one of assessment_review or question_review.")
        return attrs

    class Meta:
        model = ReviewDecision
        fields = [
            "id",
            "assessment_review",
            "question_review",
            "decision",
            "rationale",
            "decided_by",
            "metadata",
            "decided_at",
            "created_at",
        ]
        read_only_fields = ["id", "decided_at", "created_at"]


class AssessmentReviewSerializer(serializers.ModelSerializer):
    findings = QualityFindingSerializer(many=True, read_only=True)
    decisions = ReviewDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = AssessmentReview
        fields = [
            "id",
            "assessment",
            "status",
            "opened_by",
            "reviewer",
            "opened_at",
            "started_at",
            "completed_at",
            "metadata",
            "created_at",
            "updated_at",
            "findings",
            "decisions",
        ]
        read_only_fields = ["id", "status", "opened_at", "started_at", "completed_at", "created_at", "updated_at"]


class QuestionReviewSerializer(serializers.ModelSerializer):
    findings = QualityFindingSerializer(many=True, read_only=True)
    decisions = ReviewDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = QuestionReview
        fields = [
            "id",
            "item_bank_entry",
            "status",
            "opened_by",
            "reviewer",
            "opened_at",
            "started_at",
            "completed_at",
            "metadata",
            "created_at",
            "updated_at",
            "findings",
            "decisions",
        ]
        read_only_fields = ["id", "status", "opened_at", "started_at", "completed_at", "created_at", "updated_at"]


class DifficultyCalibrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DifficultyCalibration
        fields = [
            "id",
            "assessment",
            "item_bank_entry",
            "expected_difficulty",
            "observed_success_rate",
            "sample_size",
            "calibrated_difficulty",
            "direction",
            "calibration_reason",
            "metadata",
            "created_at",
        ]
        read_only_fields = ["id", "expected_difficulty", "calibrated_difficulty", "direction", "calibration_reason", "created_at"]


class ReviewerAssignmentSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        linked_count = int(bool(attrs.get("assessment_review"))) + int(bool(attrs.get("question_review")))
        if linked_count != 1:
            raise serializers.ValidationError("Provide exactly one of assessment_review or question_review.")
        return attrs

    class Meta:
        model = ReviewerAssignment
        fields = [
            "id",
            "reviewer",
            "assessment_review",
            "question_review",
            "status",
            "assigned_at",
            "completed_at",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "status", "assigned_at", "completed_at", "created_at", "updated_at"]


class ReviewDecisionActionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "needs_revision", "rejected"])
    rationale = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False)


class FindingActionSerializer(serializers.Serializer):
    finding_type = serializers.CharField(max_length=100)
    severity = serializers.ChoiceField(choices=["low", "medium", "high", "critical"], required=False)
    description = serializers.CharField()
    metadata = serializers.JSONField(required=False)


class CalibrationActionSerializer(serializers.Serializer):
    item_bank_entry = serializers.UUIDField()
    assessment = serializers.UUIDField(required=False)
    observed_success_rate = serializers.FloatField(required=False, allow_null=True, min_value=0.0, max_value=1.0)
    sample_size = serializers.IntegerField(min_value=0)
    metadata = serializers.JSONField(required=False)
