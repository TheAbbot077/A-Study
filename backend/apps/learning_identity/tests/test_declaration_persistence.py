from uuid import uuid4

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.learning_identity.domain.enums import DeclarationSynchronizationResultCode, DeclarationSynchronizationStatus
from apps.learning_identity.domain.models import LearningIdentityDeclarationSynchronization
from apps.users.domain.models import Institution, InstitutionMembership, User


class DeclarationSynchronizationPersistenceTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        self.onboarding_id = uuid4()

    def _receipt(self, **overrides):
        values = {
            "tenant": self.tenant,
            "learner": self.learner,
            "onboarding_session_id": self.onboarding_id,
            "onboarding_revision": 1,
            "source_event_id": "event-1",
            "payload_fingerprint": "a" * 64,
            "status": DeclarationSynchronizationStatus.NO_CHANGE,
            "result_code": DeclarationSynchronizationResultCode.NO_CHANGE,
            "readiness_status": "READY",
        }
        values.update(overrides)
        return LearningIdentityDeclarationSynchronization.objects.create(**values)

    def test_unique_onboarding_revision_and_source_event(self):
        self._receipt()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._receipt(source_event_id="event-2")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._receipt(onboarding_revision=2, source_event_id="event-1")

    def test_revision_and_fingerprint_constraints(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._receipt(onboarding_revision=0)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._receipt(payload_fingerprint="not-a-fingerprint")
