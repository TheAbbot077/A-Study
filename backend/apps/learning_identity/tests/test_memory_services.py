from datetime import timedelta
from unittest.mock import Mock

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.learning_identity.application.memory_queries import BuildLearnerMentorContext, GetLearnerMemorySummary, ListLearningIdentityTimeline
from apps.learning_identity.application.memory_services import ContestLearningObservationService, SetLearnerPreferenceService, SynchronizeLearningObservationService
from apps.learning_identity.application.ports import ObservationSourceEnvelope
from apps.learning_identity.application.services import CreateLearningProfileService
from apps.learning_identity.domain.enums import (
    EvidenceAuthorityClass,
    EvidenceSourceDomain,
    EvidenceSourceType,
    LearnerPreferenceKey,
    LearningObservationStatus,
    LearningObservationType,
    MentorContextPurpose,
    ObservationSynchronizationResultCode,
)
from apps.learning_identity.domain.models import LearnerPreferenceSelection, LearningIdentityObservation
from apps.users.domain.models import Institution, InstitutionMembership, User


class FakeObservationResolver:
    def __init__(self, *, payload=None, revision="1"):
        self.payload = payload or {"status": "COMPLETED"}
        self.revision = revision

    def resolve(self, **kwargs):
        return ObservationSourceEnvelope(
            exists=True,
            tenant_id=str(kwargs["tenant_id"]),
            learner_id=str(kwargs["learner_id"]),
            source_domain=kwargs["source_domain"],
            source_type=kwargs["source_type"],
            source_identifier=kwargs["source_identifier"],
            source_revision=self.revision,
            occurred_at=timezone.now() - timedelta(minutes=5),
            observation_type=LearningObservationType.DIAGNOSTIC_COMPLETED,
            authority_class=EvidenceAuthorityClass.DIAGNOSTIC,
            controlled_payload=self.payload,
            learner_safe_title="Diagnostic completed",
            learner_safe_summary="Recorded after you completed a diagnostic. This is not mastery.",
        )


class LearningIdentityMemoryServiceTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-memory")
        self.learner = User.objects.create_user(email="memory@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        self.profile = CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.learner)
        self.profile.refresh_from_db()

    def test_observation_sync_records_neutral_event_and_is_idempotent(self):
        events = Mock()
        service = SynchronizeLearningObservationService(resolver=FakeObservationResolver(), events=events)

        first = service.execute(
            source_domain=EvidenceSourceDomain.SELF_STUDY,
            source_type=EvidenceSourceType.DIAGNOSTIC_ATTEMPT,
            source_identifier="diagnostic-1",
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
            idempotency_key="sync-diagnostic",
        )
        second = service.execute(
            source_domain=EvidenceSourceDomain.SELF_STUDY,
            source_type=EvidenceSourceType.DIAGNOSTIC_ATTEMPT,
            source_identifier="diagnostic-1",
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
            idempotency_key="sync-diagnostic",
        )

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.result_code, ObservationSynchronizationResultCode.CREATED)
        observation = LearningIdentityObservation.objects.get()
        self.assertEqual(observation.observation_type, LearningObservationType.DIAGNOSTIC_COMPLETED)
        self.assertTrue(observation.mentor_context_eligible)

    def test_observation_sync_rejects_unsafe_payload(self):
        service = SynchronizeLearningObservationService(resolver=FakeObservationResolver(payload={"mastery": "mastered algebra"}))

        with self.assertRaises(ValidationError):
            service.execute(
                source_domain=EvidenceSourceDomain.SELF_STUDY,
                source_type=EvidenceSourceType.DIAGNOSTIC_ATTEMPT,
                source_identifier="diagnostic-unsafe",
                tenant_id=self.tenant.id,
                learner_id=self.learner.id,
                actor=self.learner,
            )

    def test_preferences_are_explicit_and_versioned(self):
        service = SetLearnerPreferenceService()
        preference = service.execute(
            profile_id=self.profile.id,
            actor=self.learner,
            expected_profile_version=self.profile.version,
            preference_key=LearnerPreferenceKey.EXPLANATION_MODE,
            value="step_by_step",
            idempotency_key="pref-1",
        )
        self.profile.refresh_from_db()
        replacement = service.execute(
            profile_id=self.profile.id,
            actor=self.learner,
            expected_profile_version=self.profile.version,
            preference_key=LearnerPreferenceKey.EXPLANATION_MODE,
            value="concise",
            idempotency_key="pref-2",
        )

        self.assertNotEqual(preference.id, replacement.id)
        self.assertEqual(LearnerPreferenceSelection.objects.filter(status="ACTIVE").count(), 1)
        preference.refresh_from_db()
        self.assertEqual(preference.status, "SUPERSEDED")

    def test_contested_observation_is_removed_from_mentor_context(self):
        receipt = SynchronizeLearningObservationService(resolver=FakeObservationResolver()).execute(
            source_domain=EvidenceSourceDomain.SELF_STUDY,
            source_type=EvidenceSourceType.DIAGNOSTIC_ATTEMPT,
            source_identifier="diagnostic-2",
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
        )
        ContestLearningObservationService().execute(observation_id=receipt.observation_id, actor=self.learner, reason_code="INCORRECT")
        observation = LearningIdentityObservation.objects.get(id=receipt.observation_id)

        self.assertEqual(observation.status, LearningObservationStatus.CONTESTED)
        context = BuildLearnerMentorContext().execute(profile_id=self.profile.id, actor=self.learner, purpose=MentorContextPurpose.SESSION_OPENING)
        self.assertFalse(any(item["key"].startswith("activity_") for item in context["items"]))

    def test_memory_and_timeline_are_learner_safe(self):
        SynchronizeLearningObservationService(resolver=FakeObservationResolver()).execute(
            source_domain=EvidenceSourceDomain.SELF_STUDY,
            source_type=EvidenceSourceType.DIAGNOSTIC_ATTEMPT,
            source_identifier="diagnostic-3",
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
        )

        summary = GetLearnerMemorySummary().execute(profile_id=self.profile.id, actor=self.learner)
        timeline = ListLearningIdentityTimeline().execute(profile_id=self.profile.id, actor=self.learner)

        self.assertIn("recent_learning_activity", summary)
        self.assertNotIn("score", str(summary).lower())
        self.assertGreaterEqual(len(timeline["entries"]), 1)
