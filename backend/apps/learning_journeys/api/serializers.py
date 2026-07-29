from __future__ import annotations

from rest_framework import serializers


class CreateSelfStudyJourneySerializer(serializers.Serializer):
    workspace_id = serializers.UUIDField()


class CreateInstitutionalJourneySerializer(serializers.Serializer):
    learner_id = serializers.UUIDField()
    institution_id = serializers.UUIDField()


class JourneyVersionCommandSerializer(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1, required=False)


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
    version = serializers.IntegerField()
    last_synchronized_at = serializers.CharField(required=False, allow_null=True)
