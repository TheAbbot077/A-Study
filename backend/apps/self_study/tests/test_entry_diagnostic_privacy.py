from unittest.mock import Mock
from apps.self_study.api.diagnostic_serializers import PublicDiagnosticSerializer,PublicPresentationSerializer,SubmitDiagnosticResponseSerializer

def test_public_item_never_serializes_scoring_specification():
    item=Mock(id="item",item_type="NUMERIC",prompt="2 + 2",response_schema={"type":"number"},language="en",scoring_specification={"answer":4})
    presentation=Mock(id="presentation",sequence=1,item=item,item_id="item")
    data=PublicPresentationSerializer(presentation).data
    assert "scoring_specification" not in str(data)
    assert "answer" not in str(data)

def test_client_controlled_scoring_fields_are_rejected():
    serializer=SubmitDiagnosticResponseSerializer(data={"presentation_id":"11111111-1111-4111-8111-111111111111","response":{"answer":"a","confidence":1},"idempotency_key":"one"})
    assert not serializer.is_valid()

def test_public_diagnostic_contract_has_no_internal_estimates_or_confidence():
    policy=Mock(learner_can_challenge=True,learner_can_retake=True,learner_can_attempt_checkpoint=True)
    diagnostic=Mock(id="d",status="COMPLETED",minimum_items=8,maximum_items=15,expires_at=None,policy_snapshot=policy)
    diagnostic.responses.count.return_value=8
    data=PublicDiagnosticSerializer(diagnostic).data
    serialized=str(data).lower()
    assert "estimate" not in serialized and "confidence" not in serialized and "score" not in serialized and "ranking" not in serialized
