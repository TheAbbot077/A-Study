from decimal import Decimal

import pytest
from django.utils import timezone

from apps.academic.models import Subject
from apps.self_study.application.curriculum_services import (
    ResolveCurriculumAttemptService,
    StartCurriculumResolutionService,
)
from apps.self_study.curriculum_models import (
    CurriculumAuthority,
    CurriculumReference,
    CurriculumResolutionAttempt,
    CurriculumSelectionDecision,
    CurriculumVersion,
)
from apps.self_study.models import EffectiveLearningPolicySnapshot, SelfStudyIntent
from apps.users.models import Institution


@pytest.fixture
def resolution_scope(django_user_model):
    learner = django_user_model.objects.create_user(email="resolver@example.com", password="secret")
    tenant = Institution.objects.create(name="Resolver tenant", slug="resolver-tenant")
    subject = Subject.objects.create(institution=tenant, code="MATH-R", name="mathematics")
    snapshot = EffectiveLearningPolicySnapshot.objects.create(
        policy_version=1,
        source_policy_ids=["platform-policy"],
        allowed_provider_ids=["registry"],
        allowed_source_categories=["OPEN_EDUCATIONAL_RESOURCE"],
        allowed_licence_categories=["CC-BY"],
        allowed_mime_types=["application/pdf"],
        allowed_languages=["en"],
        maximum_resource_count=10,
        maximum_single_file_bytes=10000,
        maximum_total_bytes=100000,
        maximum_cost=Decimal("0"),
    )
    intent = SelfStudyIntent.objects.create(
        learner=learner,
        tenant=tenant,
        subject=subject,
        mode="SELF_STUDY",
        goal_statement="advanced mathematics calculus",
        preferred_language="en",
        jurisdiction="LS",
        policy_acknowledged_at=timezone.now(),
        status="ACTIVE",
        effective_policy_snapshot=snapshot,
        created_by=learner,
        version=2,
    )
    return learner, tenant, intent


def add_version(*, actor, source, key, title, outcomes):
    authority = CurriculumAuthority.objects.create(
        canonical_key=f"{key}-authority",
        name=f"{title} authority",
        authority_type="NATIONAL_CURRICULUM_BODY",
        verification_status="VERIFIED",
        verified_at=timezone.now(),
        verified_by=actor,
    )
    reference = CurriculumReference.objects.create(
        canonical_key=key,
        title=title,
        subject_area="mathematics",
        authority=authority,
        source_classification=source,
        jurisdiction="LS",
        language="en",
    )
    return CurriculumVersion.objects.create(
        curriculum_reference=reference,
        version_label="2026",
        status="ACTIVE",
        canonical_source_uri=f"https://example.edu/{key}",
        content_hash=f"sha256:{key}",
        licence_identifier="CC-BY",
        provenance_status="COMPLETE",
        language="en",
        jurisdiction="LS",
        target_outcomes_summary=outcomes,
        created_by=actor,
    )


@pytest.mark.django_db
def test_activated_intent_starts_exactly_one_attempt(resolution_scope):
    learner, _, intent = resolution_scope
    service = StartCurriculumResolutionService(enqueue=False)
    first, replayed = service.execute(intent_id=intent.id, actor=learner, idempotency_key="start")
    second, second_replayed = service.execute(intent_id=intent.id, actor=learner, idempotency_key="replay")
    assert replayed is False
    assert second_replayed is True
    assert first.id == second.id
    assert CurriculumResolutionAttempt.objects.count() == 1


@pytest.mark.django_db
def test_higher_hierarchy_candidate_wins_over_lower_candidate_score(resolution_scope):
    learner, _, intent = resolution_scope
    national = add_version(
        actor=learner,
        source="NATIONAL_OR_REGIONAL",
        key="national-math",
        title="Advanced mathematics calculus",
        outcomes="advanced mathematics calculus",
    )
    add_version(
        actor=learner,
        source="CURATED_REFERENCE",
        key="curated-math",
        title="Advanced mathematics calculus complete",
        outcomes="advanced mathematics calculus complete",
    )
    attempt, _ = StartCurriculumResolutionService(enqueue=False).execute(
        intent_id=intent.id, actor=learner, idempotency_key="resolve"
    )
    ResolveCurriculumAttemptService().execute(attempt.id)
    decision = CurriculumSelectionDecision.objects.get(attempt=attempt)
    assert decision.curriculum_version_id == national.id
    assert attempt.candidates.count() == 2


@pytest.mark.django_db
def test_failure_requires_exhausted_candidates_and_is_fallback_evidence(resolution_scope):
    learner, _, intent = resolution_scope
    attempt, _ = StartCurriculumResolutionService(enqueue=False).execute(
        intent_id=intent.id, actor=learner, idempotency_key="no-match"
    )
    ResolveCurriculumAttemptService().execute(attempt.id)
    attempt.refresh_from_db()
    assert attempt.status == "FAILED"
    assert attempt.resolution_failure.policy_snapshot_id == intent.effective_policy_snapshot_id
    assert attempt.resolution_failure.reason_codes == ["NO_CURRICULA_REGISTERED"]


@pytest.mark.django_db
def test_explicit_suspended_version_is_not_silently_replaced(resolution_scope):
    learner, _, intent = resolution_scope
    suspended = add_version(
        actor=learner,
        source="NATIONAL_OR_REGIONAL",
        key="suspended",
        title="Advanced mathematics calculus",
        outcomes="advanced mathematics calculus",
    )
    CurriculumVersion.objects.filter(id=suspended.id).update(status="SUSPENDED")
    add_version(
        actor=learner,
        source="NATIONAL_OR_REGIONAL",
        key="alternative",
        title="Advanced mathematics calculus",
        outcomes="advanced mathematics calculus",
    )
    attempt, _ = StartCurriculumResolutionService(enqueue=False).execute(
        intent_id=intent.id,
        actor=learner,
        idempotency_key="explicit",
        requested_version_id=suspended.id,
    )
    ResolveCurriculumAttemptService().execute(attempt.id)
    attempt.refresh_from_db()
    assert attempt.status == "AWAITING_APPROVAL"
    requested = attempt.candidates.get(curriculum_version=suspended)
    assert "CURRICULUM_SUSPENDED" in requested.rejection_reasons
    assert not hasattr(attempt, "selection")
    assert not hasattr(attempt, "resolution_failure")
