from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.learning_identity.infrastructure.onboarding_resolver import SelfStudyConfirmedOnboardingDeclarationResolver
from apps.self_study.onboarding_models import SelfStudyOnboarding, SelfStudyOnboardingIntent, SelfStudyOnboardingStatus
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.domain.models import Institution, InstitutionMembership, User


class OnboardingResolverTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.other = User.objects.create_user(email="other@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        self.workspace = SelfStudyWorkspace.objects.create(
            tenant=self.tenant,
            learner=self.learner,
            display_name="Biology",
        )
        self.onboarding = SelfStudyOnboarding.objects.create(
            tenant=self.tenant,
            learner=self.learner,
            workspace=self.workspace,
            status=SelfStudyOnboardingStatus.COMPLETED,
            current_stage="COMPLETED",
            topic_query="Biology",
            study_intent=SelfStudyOnboardingIntent.EXAM,
            qualification_query="Cambridge International A Level",
            weekly_study_minutes=300,
            completed_at=timezone.now(),
            version=7,
        )

    def test_resolves_completed_onboarding_as_safe_confirmed_declarations(self):
        declaration_set = SelfStudyConfirmedOnboardingDeclarationResolver().resolve_confirmed_declarations(
            onboarding_session_id=self.onboarding.id,
            onboarding_revision=self.onboarding.version,
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
        )
        self.assertEqual(declaration_set.onboarding_revision, 7)
        self.assertEqual({item.source_field for item in declaration_set.declarations}, {"topic_query", "qualification_query", "weekly_study_minutes"})
        for declaration in declaration_set.declarations:
            self.assertEqual(declaration.confirmation_disposition, "EXPLICITLY_CONFIRMED")
            self.assertNotIn("transcript", declaration.source_metadata)

    def test_wrong_tenant_or_learner_fails_closed(self):
        with self.assertRaises(ValidationError):
            SelfStudyConfirmedOnboardingDeclarationResolver().resolve_confirmed_declarations(
                onboarding_session_id=self.onboarding.id,
                onboarding_revision=self.onboarding.version,
                tenant_id=self.tenant.id,
                learner_id=self.other.id,
            )

    def test_incomplete_or_wrong_revision_is_rejected(self):
        self.onboarding.status = SelfStudyOnboardingStatus.COLLECTING_CONTEXT
        self.onboarding.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            SelfStudyConfirmedOnboardingDeclarationResolver().resolve_confirmed_declarations(
                onboarding_session_id=self.onboarding.id,
                onboarding_revision=7,
                tenant_id=self.tenant.id,
                learner_id=self.learner.id,
            )
        self.onboarding.status = SelfStudyOnboardingStatus.COMPLETED
        self.onboarding.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            SelfStudyConfirmedOnboardingDeclarationResolver().resolve_confirmed_declarations(
                onboarding_session_id=self.onboarding.id,
                onboarding_revision=6,
                tenant_id=self.tenant.id,
                learner_id=self.learner.id,
            )
