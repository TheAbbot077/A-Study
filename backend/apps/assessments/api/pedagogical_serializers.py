from rest_framework import serializers


class PedagogicalResponseDecisionSerializer(serializers.Serializer):
    learner_id = serializers.CharField()
    content_concept_id = serializers.CharField()
    mastery_state = serializers.CharField()
    decision_code = serializers.CharField()
    decision_version = serializers.CharField()
    justification = serializers.CharField()
    requires_remediation = serializers.BooleanField()
    remediation_plan_id = serializers.CharField(allow_null=True, required=False)
    evidence_count = serializers.IntegerField()
    authoritative_evidence_ids = serializers.ListField(child=serializers.CharField())
    previous_decision = serializers.CharField(allow_null=True, required=False)
    decision_state = serializers.CharField()
    decided_at = serializers.CharField(allow_null=True, required=False)
