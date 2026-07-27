from dataclasses import replace
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.learning_identity.application.declaration_services import ApplyConfirmedOnboardingDeclarationsService, PreviewOnboardingDeclarationChangesService
from apps.learning_identity.application.onboarding_dto import ConfirmedLearningIdentityDeclaration, ConfirmedLearningIdentityDeclarationSet
from apps.learning_identity.domain.enums import DeclarationSynchronizationStatus, LearningAttributeType, LearningProfileStatus
from apps.learning_identity.domain.models import LearnerLearningProfile, LearningIdentityAttribute, LearningIdentityDeclarationSynchronization
from apps.self_study.onboarding_models import SelfStudyOnboarding, SelfStudyOnboardingStatus
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.domain.models import Institution, InstitutionMembership, User


class FakeDeclarationSource:
    def __init__(self, declaration_set):
        self.declaration_set = declaration_set

    def resolve_confirmed_declarations(self, **kwargs):
        return self.declaration_set


class DeclarationServiceTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        now = timezone.now()
        self.onboarding_id = uuid4()
        self.workspace = SelfStudyWorkspace.objects.create(
            tenant=self.tenant,
            learner=self.learner,
            display_name="Biology",
        )
        SelfStudyOnboarding.objects.create(
            id=self.onboarding_id,
            tenant=self.tenant,
            learner=self.learner,
            workspace=self.workspace,
            status=SelfStudyOnboardingStatus.COMPLETED,
            current_stage="COMPLETED",
            topic_query="Biology",
            qualification_query="Cambridge International A Level",
            weekly_study_minutes=300,
            completed_at=now,
            version=4,
        )
        self.declaration_set = ConfirmedLearningIdentityDeclarationSet(
            onboarding_session_id=str(self.onboarding_id),
            onboarding_revision=4,
            tenant_id=str(self.tenant.id),
            learner_id=str(self.learner.id),
            confirmed_at=now,
            confirmed_by=str(self.learner.id),
            source_event_id=f"self_study.onboarding.completed:{self.onboarding_id}:4",
            source_status="COMPLETED",
            source_completed_at=now,
            declarations=(
                ConfirmedLearningIdentityDeclaration("topic_query", "  Biology exam  ", 1, "EXPLICITLY_CONFIRMED", confirmed_at=now),
                ConfirmedLearningIdentityDeclaration("qualification_query", "Cambridge International A Level", 1, "EXPLICITLY_CONFIRMED", confirmed_at=now),
                ConfirmedLearningIdentityDeclaration("weekly_study_minutes", 300, 1, "EXPLICITLY_CONFIRMED", confirmed_at=now),
            ),
        )

    def test_preview_is_read_only_and_reports_additions(self):
        preview = PreviewOnboardingDeclarationChangesService(source=FakeDeclarationSource(self.declaration_set)).execute(
            onboarding_session_id=self.onboarding_id,
            onboarding_revision=4,
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
        )
        self.assertTrue(preview.would_publish)
        self.assertEqual(LearnerLearningProfile.objects.count(), 0)

    def test_apply_creates_profile_attributes_evidence_and_receipt(self):
        receipt = ApplyConfirmedOnboardingDeclarationsService(source=FakeDeclarationSource(self.declaration_set)).execute(
            onboarding_session_id=self.onboarding_id,
            onboarding_revision=4,
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
            idempotency_key="sync",
        )
        self.assertEqual(receipt.status, DeclarationSynchronizationStatus.APPLIED)
        profile = LearnerLearningProfile.objects.get(tenant=self.tenant, learner=self.learner)
        self.assertEqual(profile.status, LearningProfileStatus.ACTIVE)
        self.assertEqual(profile.current_version.attributes.count(), 3)
        study_goal = profile.current_version.attributes.get(attribute_type=LearningAttributeType.STUDY_GOAL)
        self.assertEqual(study_goal.value, "Biology exam")
        self.assertEqual(study_goal.source_type, "ONBOARDING")
        self.assertEqual(study_goal.evidence_links.count(), 1)

    def test_duplicate_apply_is_idempotent(self):
        service = ApplyConfirmedOnboardingDeclarationsService(source=FakeDeclarationSource(self.declaration_set))
        first = service.execute(
            onboarding_session_id=self.onboarding_id,
            onboarding_revision=4,
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
            idempotency_key="sync",
        )
        second = service.execute(
            onboarding_session_id=self.onboarding_id,
            onboarding_revision=4,
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
            idempotency_key="sync",
        )
        self.assertEqual(first.id, second.id)
        self.assertEqual(LearningIdentityDeclarationSynchronization.objects.count(), 1)

    def test_same_revision_with_changed_payload_conflicts(self):
        service = ApplyConfirmedOnboardingDeclarationsService(source=FakeDeclarationSource(self.declaration_set))
        service.execute(
            onboarding_session_id=self.onboarding_id,
            onboarding_revision=4,
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
            idempotency_key="sync",
        )
        changed = replace(
            self.declaration_set,
            declarations=(
                ConfirmedLearningIdentityDeclaration("topic_query", "Chemistry", 1, "EXPLICITLY_CONFIRMED", confirmed_at=timezone.now()),
            ),
        )
        with self.assertRaises(ValidationError):
            ApplyConfirmedOnboardingDeclarationsService(source=FakeDeclarationSource(changed)).execute(
                onboarding_session_id=self.onboarding_id,
                onboarding_revision=4,
                tenant_id=self.tenant.id,
                learner_id=self.learner.id,
                actor=self.learner,
                idempotency_key="different-key",
            )

    def test_inferred_declaration_is_not_applied(self):
        inferred = replace(
            self.declaration_set,
            onboarding_session_id=str(uuid4()),
            declarations=(
                ConfirmedLearningIdentityDeclaration("topic_query", "Biology", 1, "INFERRED", confirmed_at=timezone.now()),
            ),
        )
        receipt = ApplyConfirmedOnboardingDeclarationsService(source=FakeDeclarationSource(inferred)).execute(
            onboarding_session_id=inferred.onboarding_session_id,
            onboarding_revision=4,
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
        )
        self.assertEqual(receipt.status, DeclarationSynchronizationStatus.NO_CHANGE)
        self.assertEqual(LearningIdentityAttribute.objects.count(), 0)
