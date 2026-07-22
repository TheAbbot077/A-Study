from rest_framework import serializers
from ..diagnostic_models import DiagnosticItemPresentation,EntryDiagnostic

PURPOSE="Personalize where your learning begins."
class CreateDiagnosticSerializer(serializers.Serializer): purpose_acknowledged=serializers.BooleanField()
class SubmitDiagnosticResponseSerializer(serializers.Serializer):
    presentation_id=serializers.UUIDField();response=serializers.JSONField();idempotency_key=serializers.CharField(max_length=128)
    def validate(self,data):
        forbidden={"correctness","score","confidence","normalized_score"}
        if isinstance(data["response"],dict) and forbidden & set(data["response"]):raise serializers.ValidationError("Client scoring fields are prohibited.",code="DIAGNOSTIC_RESPONSE_INVALID")
        return data
class ChallengeSerializer(serializers.Serializer):reason=serializers.CharField(max_length=2000)
class BlueprintSerializer(serializers.Serializer):
    minimum_items=serializers.IntegerField(min_value=2,max_value=50,default=8);maximum_items=serializers.IntegerField(min_value=2,max_value=50,default=15)
class DiagnosticItemRegistrationSerializer(serializers.Serializer):
    stable_key=serializers.CharField(max_length=128);graph_node_ids=serializers.ListField(child=serializers.UUIDField(),allow_empty=False);item_type=serializers.ChoiceField(choices=["SINGLE_CHOICE","MULTIPLE_CHOICE","NUMERIC","SHORT_STRUCTURED","ORDERING","MATCHING"]);prompt=serializers.CharField();response_schema=serializers.JSONField();scoring_specification=serializers.JSONField(write_only=True);difficulty_band=serializers.IntegerField(min_value=1,max_value=5,default=2);discrimination_band=serializers.IntegerField(min_value=1,max_value=5,default=2);language=serializers.CharField(max_length=16);source=serializers.CharField(max_length=128);generation_method=serializers.ChoiceField(choices=["CURATED","STRUCTURED_IMPORT"],default="CURATED");review_status=serializers.ChoiceField(choices=["VALIDATED"],default="VALIDATED")
class PublicDiagnosticSerializer(serializers.ModelSerializer):
    purpose=serializers.SerializerMethodField();progress=serializers.SerializerMethodField();message=serializers.SerializerMethodField();controls=serializers.SerializerMethodField()
    class Meta:model=EntryDiagnostic;fields=["id","status","purpose","progress","message","controls","expires_at"]
    def get_purpose(self,obj):return PURPOSE
    def get_progress(self,obj):return {"answered":obj.responses.count(),"minimum_items":obj.minimum_items,"maximum_items":obj.maximum_items}
    def get_message(self,obj):return "Your personalized starting point is ready." if obj.status=="COMPLETED" else "Additional information may be needed." if obj.status=="INCONCLUSIVE" else ""
    def get_controls(self,obj):return {"can_pause":obj.status=="IN_PROGRESS","can_cancel":obj.status in {"READY","IN_PROGRESS"},"can_challenge":obj.status=="COMPLETED" and obj.policy_snapshot.learner_can_challenge,"can_retake":obj.status in {"COMPLETED","INCONCLUSIVE","CHALLENGED"} and obj.policy_snapshot.learner_can_retake,"can_checkpoint":obj.status in {"COMPLETED","INCONCLUSIVE"} and obj.policy_snapshot.learner_can_attempt_checkpoint}
class PublicPresentationSerializer(serializers.ModelSerializer):
    item=serializers.SerializerMethodField()
    class Meta:model=DiagnosticItemPresentation;fields=["id","sequence","item"]
    def get_item(self,obj):
        allowed={"choices","minimum","maximum","step","max_length","fields","left","right"}
        public_schema={key:value for key,value in obj.item.response_schema.items() if key in allowed}
        return {"id":obj.item_id,"type":obj.item.item_type,"prompt":obj.item.prompt,"response_schema":public_schema,"language":obj.item.language}
