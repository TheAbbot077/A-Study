from decimal import Decimal

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.academic.models import Subject
from apps.self_study.application.services import (
    ActivateSelfStudyIntentService,
    AuthorizeAutonomousCurriculumFallbackService,
    AuthorizeResourceAcquisitionService,
)
from apps.self_study.domain.policy import AcquisitionCandidate
from apps.self_study.models import (
    EffectiveLearningPolicySnapshot,
    LearningPolicyRuleSet,
    SelfStudyIntent,
)
from apps.users.models import Institution, InstitutionMembership, InstitutionRole


@pytest.fixture
def active_intent(django_user_model):
    learner = django_user_model.objects.create_user(email="policy-learner@example.com", password="secret")
    tenant = Institution.objects.create(name="Policy tenant", slug="policy-tenant")
    subject = Subject.objects.create(institution=tenant, code="POL-1", name="Policy")
    LearningPolicyRuleSet.objects.filter(
        authority=LearningPolicyRuleSet.Authority.PLATFORM,
        is_active=True,
    ).update(is_active=False)
    LearningPolicyRuleSet.objects.create(
        authority=LearningPolicyRuleSet.Authority.PLATFORM,
        allowed_provider_ids=["open-provider"],
        allowed_source_categories=["OPEN_EDUCATIONAL_RESOURCE"],
        allowed_licence_categories=["CC-BY"],
        allowed_mime_types=["application/pdf"],
        allowed_languages=["en"],
        maximum_resource_count=5,
        maximum_single_file_bytes=5_000,
        maximum_total_bytes=20_000,
        maximum_cost=Decimal("0"),
        external_network_access_enabled=True,
    )
    intent = SelfStudyIntent.objects.create(
        learner=learner,
        tenant=tenant,
        subject=subject,
        mode="SELF_STUDY",
        goal_statement="Learn policy",
        preferred_language="en",
        policy_acknowledged_at=timezone.now(),
        status="READY",
        created_by=learner,
    )
    return ActivateSelfStudyIntentService().execute(intent_id=intent.id, actor=learner, expected_version=1)


@pytest.mark.django_db
def test_activation_creates_exactly_one_immutable_snapshot(active_intent):
    assert active_intent.effective_policy_snapshot_id is not None
    assert EffectiveLearningPolicySnapshot.objects.count() == 1
    snapshot = active_intent.effective_policy_snapshot
    snapshot.maximum_resource_count = 999
    with pytest.raises(ValidationError):
        snapshot.save()


@pytest.mark.django_db
def test_acquisition_decision_is_reproducible_and_idempotent(active_intent):
    assert SelfStudyIntent._meta.get_field("effective_policy_snapshot").null is True
    candidate = AcquisitionCandidate(
        provider_id="open-provider",
        source_category="OPEN_EDUCATIONAL_RESOURCE",
        licence_category="CC-BY",
        mime_type="application/pdf",
        language="en",
        file_size=1_000,
        projected_total_size=1_000,
        projected_resource_count=1,
        price=Decimal("0"),
        currency="USD",
        trust_classification="PROVIDER_VERIFIED",
        network_acquisition_required=True,
    )
    service = AuthorizeResourceAcquisitionService()
    first = service.execute(intent_id=active_intent.id, actor=active_intent.learner, candidate=candidate, idempotency_key="same")
    second = service.execute(intent_id=active_intent.id, actor=active_intent.learner, candidate=candidate, idempotency_key="same")
    assert first.id == second.id
    assert first.policy_snapshot_id == active_intent.effective_policy_snapshot_id
    assert first.decision == "AUTO_APPROVED"


@pytest.mark.django_db
def test_unknown_licence_is_rejected_without_creating_a_resource(active_intent):
    candidate = AcquisitionCandidate(
        provider_id="open-provider",
        source_category="OPEN_EDUCATIONAL_RESOURCE",
        licence_category="UNKNOWN",
        mime_type="application/pdf",
        language="en",
        file_size=1_000,
        projected_total_size=1_000,
        projected_resource_count=1,
        price=Decimal("0"),
        currency="USD",
        trust_classification="PROVIDER_VERIFIED",
        network_acquisition_required=True,
    )
    decision = AuthorizeResourceAcquisitionService().execute(
        intent_id=active_intent.id,
        actor=active_intent.learner,
        candidate=candidate,
        idempotency_key="unknown-licence",
    )
    assert decision.decision == "REJECTED"
    assert "UNKNOWN_LICENCE" in decision.reason_codes
    assert decision.acquisition_method == "POLICY_AUTHORIZATION_ONLY"


@pytest.mark.django_db
def test_autonomous_fallback_requires_institutional_authority(active_intent):
    with pytest.raises(PermissionDenied):
        AuthorizeAutonomousCurriculumFallbackService().execute(
            intent_id=active_intent.id,
            actor=active_intent.learner,
            resolution_failure_id=None,
            idempotency_key="fallback",
        )


@pytest.mark.django_db
def test_autonomous_fallback_denied_without_recorded_resolution_failure(active_intent, django_user_model):
    administrator = django_user_model.objects.create_user(email="policy-admin@example.com", password="secret")
    InstitutionMembership.objects.create(
        user=administrator,
        institution=active_intent.tenant,
        role=InstitutionRole.ADMINISTRATOR,
    )
    decision = AuthorizeAutonomousCurriculumFallbackService().execute(
        intent_id=active_intent.id,
        actor=administrator,
        resolution_failure_id=None,
        idempotency_key="fallback-admin",
    )
    assert decision.authorized is False
    assert "CURRICULUM_RESOLUTION_FAILURE_REQUIRED" in decision.reason_codes
    assert "AUTONOMOUS_FALLBACK_NOT_ALLOWED" in decision.reason_codes
