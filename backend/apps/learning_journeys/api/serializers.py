from __future__ import annotations

from rest_framework import serializers


class CreateSelfStudyJourneySerializer(serializers.Serializer):
    workspace_id = serializers.UUIDField()


class CreateInstitutionalJourneySerializer(serializers.Serializer):
    learner_id = serializers.UUIDField()
    institution_id = serializers.UUIDField()
    subject_id = serializers.UUIDField(required=False)
    curriculum_reference_id = serializers.UUIDField(required=False)
    programme_label = serializers.CharField(max_length=255, allow_blank=True, required=False)
    course_label = serializers.CharField(max_length=255, allow_blank=True, required=False)
    required_competency_ids = serializers.ListField(child=serializers.UUIDField(), required=False)
    delivery_objectives = serializers.DictField(required=False)


class JourneyVersionCommandSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1, required=False)


class ExecuteLearningJourneyActionSerializer(serializers.Serializer):
    idempotency_key = serializers.CharField(max_length=128, allow_blank=True, required=False)
    payload = serializers.DictField(required=False)


class LearningJourneyActionReceiptSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    action_code = serializers.CharField()
    status = serializers.CharField()
    failure_code = serializers.CharField(required=False, allow_blank=True)
    failure_message = serializers.CharField(required=False, allow_blank=True)
    replayed = serializers.BooleanField(required=False)


class LearningJourneyReadSerializer(serializers.Serializer):
    journey_id = serializers.UUIDField()
    journey_type = serializers.CharField()
    state = serializers.CharField()
    status_reason = serializers.DictField()
    current_step = serializers.DictField()
    subject = serializers.DictField(required=False, allow_null=True)
    authority = serializers.DictField(required=False, allow_null=True)
    available_actions = serializers.ListField()
    blockers = serializers.ListField()
    capability_references = serializers.DictField()
    active_capabilities = serializers.DictField(required=False)
    progress = serializers.DictField(required=False)
    competency_context = serializers.DictField(required=False)
    institutional_state = serializers.DictField(required=False, allow_null=True)
    version = serializers.IntegerField()
    last_synchronized_at = serializers.CharField(required=False, allow_null=True)


class LearningCompetencyProgressSnapshotSerializer(serializers.Serializer):
    journey_id = serializers.UUIDField()
    completed_competencies = serializers.ListField()
    active_competencies = serializers.ListField()
    emerging_competencies = serializers.ListField()
    review_competencies = serializers.ListField()
    locked_competencies = serializers.ListField()
    next_available_competencies = serializers.ListField()


class LearningJourneyProgressSnapshotSerializer(serializers.Serializer):
    journey_id = serializers.UUIDField()
    current_learning_phase = serializers.CharField()
    active_competency = serializers.DictField(required=False, allow_null=True)
    next_competency = serializers.DictField(required=False, allow_null=True)
    blocked_competencies = serializers.ListField()
    available_competencies = serializers.ListField()
    completed_competency_count = serializers.IntegerField()
