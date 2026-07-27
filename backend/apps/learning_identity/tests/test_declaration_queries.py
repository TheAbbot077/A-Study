from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from apps.learning_identity.application.declaration_queries import GetLearnerSafeDeclarationSummary, GetOnboardingDeclarationSynchronizationStatus
from apps.learning_identity.domain.enums import (
    AttributeClassification,
    AttributeSourceType,
    AttributeVisibility,
    DeclarationSynchronizationResultCode,
    DeclarationSynchronizationStatus,
    LearningAttributeType,
)
from apps.learning_identity.domain.models import (
    LearnerLearningProfile,
    LearningIdentityAttribute,
    LearningIdentityDeclarationSynchronization,
    LearningProfileVersion,
)
from apps.users.domain.models import Institution, InstitutionMembership, User


class DeclarationQueryTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        self.profile = LearnerLearningProfile.objects.create(tenant=self.tenant, learner=self.learner, status="ACTIVE")
        self.version = LearningProfileVersion.objects.create(profile=self.profile, version_number=1, status="PUBLISHED", created_by=self.learner, published_by=self.learner, published_at=timezone.now())
        self.profile.current_version = self.version
        self.profile.save(update_fields=["current_version"])
        LearningIdentityAttribute.objects.create(
            profile_version=self.version,
            attribute_type=LearningAttributeType.STUDY_GOAL,
            classification=AttributeClassification.DECLARED,
            value="Biology",
            source_type=AttributeSourceType.ONBOARDING,
            declared_at=timezone.now(),
            visibility=AttributeVisibility.LEARNER_VISIBLE,
            created_by=self.learner,
        )
        LearningIdentityAttribute.objects.create(
            profile_version=self.version,
            attribute_type=LearningAttributeType.ACCESSIBILITY_PREFERENCE,
            classification=AttributeClassification.DECLARED,
            value="Large text",
            source_type=AttributeSourceType.ONBOARDING,
            declared_at=timezone.now(),
            visibility=AttributeVisibility.RESTRICTED,
            restricted=True,
            created_by=self.learner,
        )
        self.onboarding_id = uuid4()
        self.receipt = LearningIdentityDeclarationSynchronization.objects.create(
            profile=self.profile,
            profile_version=self.version,
            tenant=self.tenant,
            learner=self.learner,
            onboarding_session_id=self.onboarding_id,
            onboarding_revision=3,
            source_event_id="event-3",
            payload_fingerprint="a" * 64,
            status=DeclarationSynchronizationStatus.APPLIED,
            result_code=DeclarationSynchronizationResultCode.APPLIED,
            readiness_status="READY",
            change_counts={"ADDED": 1},
            applied_at=timezone.now(),
        )

    def test_status_query_hides_fingerprint_and_source_event(self):
        result = GetOnboardingDeclarationSynchronizationStatus().execute(
            onboarding_session_id=self.onboarding_id,
            onboarding_revision=3,
            tenant_id=self.tenant.id,
            learner_id=self.learner.id,
            actor=self.learner,
        )
        self.assertEqual(result["status"], "APPLIED")
        self.assertNotIn("payload_fingerprint", result)
        self.assertNotIn("source_event_id", result)

    def test_learner_safe_summary_omits_restricted_attributes(self):
        summary = GetLearnerSafeDeclarationSummary().execute(profile_id=self.profile.id, actor=self.learner)
        self.assertEqual([item["attribute_type"] for item in summary], [LearningAttributeType.STUDY_GOAL])
        self.assertEqual(summary[0]["source_label"], "You told us this during onboarding.")
