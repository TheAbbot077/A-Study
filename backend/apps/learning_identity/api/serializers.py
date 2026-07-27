from rest_framework import serializers

from apps.learning_identity.domain.enums import LearnerPreferenceKey, MentorContextPurpose


class SetPreferenceSerializer(serializers.Serializer):
    expected_profile_version = serializers.IntegerField(min_value=1)
    preference_key = serializers.ChoiceField(choices=LearnerPreferenceKey.choices)
    value = serializers.JSONField()
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class WithdrawPreferenceSerializer(serializers.Serializer):
    expected_profile_version = serializers.IntegerField(min_value=1)
    preference_key = serializers.ChoiceField(choices=LearnerPreferenceKey.choices)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class ContestObservationSerializer(serializers.Serializer):
    reason_code = serializers.CharField(max_length=64)
    learner_note = serializers.CharField(required=False, allow_blank=True, max_length=500)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class WithdrawDeclarationSerializer(serializers.Serializer):
    expected_profile_version = serializers.IntegerField(min_value=1)
    reason_code = serializers.CharField(max_length=64)
    idempotency_key = serializers.CharField(required=False, allow_blank=True, max_length=128)


class MentorContextSerializer(serializers.Serializer):
    purpose = serializers.ChoiceField(choices=MentorContextPurpose.choices)
