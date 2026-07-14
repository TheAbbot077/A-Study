from rest_framework import serializers

from apps.academic.domain.models import ContentConcept
from apps.learning.domain.models import PedagogicalSession


class PedagogicalSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PedagogicalSession
        fields = [
            "id",
            "learner",
            "content_concept",
            "status",
            "started_at",
            "ended_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ConceptBrowserStateSerializer(serializers.Serializer):
    concept_id = serializers.CharField()
    status = serializers.ChoiceField(choices=["locked", "available", "in_progress", "mastered", "needs_remediation"])
    can_start_or_resume = serializers.BooleanField()
    action_label = serializers.CharField(allow_null=True, required=False)
    session_id = serializers.CharField(allow_null=True, required=False)
    session_status = serializers.CharField(allow_null=True, required=False)
    mastery_decision = serializers.CharField(allow_null=True, required=False)
    remediation_plan_id = serializers.CharField(allow_null=True, required=False)


class StartOrResumeConceptSerializer(serializers.Serializer):
    content_concept = serializers.PrimaryKeyRelatedField(queryset=ContentConcept.objects.all())


class ConversationTurnSerializer(serializers.Serializer):
    sequence_number = serializers.IntegerField()
    sender_type = serializers.CharField()
    message_type = serializers.CharField()
    content = serializers.CharField()
    timestamp = serializers.DateTimeField()
    metadata = serializers.JSONField(required=False)


class SourceReferenceSerializer(serializers.Serializer):
    academic_object_type = serializers.CharField()
    object_id = serializers.CharField()
    title = serializers.CharField()
    relationship = serializers.CharField()
    sequence_number = serializers.IntegerField(allow_null=True, required=False)


class AbbotResponseSectionSerializer(serializers.Serializer):
    sequence_number = serializers.IntegerField()
    title = serializers.CharField()
    content = serializers.CharField()
    source_reference_ids = serializers.ListField(child=serializers.CharField(), required=False)
    metadata = serializers.JSONField(required=False)


class AbbotTeachingResponseSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    concept_title = serializers.CharField()
    response_type = serializers.CharField()
    sections = AbbotResponseSectionSerializer(many=True)
    source_references = SourceReferenceSerializer(many=True)
    strategy_used = serializers.CharField(allow_null=True, required=False)
    metadata = serializers.JSONField(required=False)


class AskQuestionSerializer(serializers.Serializer):
    question = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)


class LearningConversationStateSerializer(serializers.Serializer):
    session = PedagogicalSessionSerializer()
    turns = ConversationTurnSerializer(many=True)
    next_expected_interaction = serializers.CharField()
    streaming_supported = serializers.BooleanField()
