from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.learning_identity.application.queries import GetLearnerSafeProfileSummary
from apps.learning_identity.application.services import (
    AddDeclaredIdentityAttributeService,
    CreateDraftProfileVersionService,
    CreateLearningProfileService,
    PublishLearningProfileVersionService,
)
from apps.learning_identity.domain.enums import AttributeVisibility, LearningAttributeType
from apps.users.domain.models import Institution, InstitutionMembership, User


class LearningProfileQueryTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.other = User.objects.create_user(email="other@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        self.profile = CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.learner)
        self.draft = CreateDraftProfileVersionService().execute(profile_id=self.profile.id, actor=self.learner, expected_version=self.profile.version)
        AddDeclaredIdentityAttributeService().execute(
            profile_version_id=self.draft.id,
            actor=self.learner,
            attribute_type=LearningAttributeType.STUDY_GOAL,
            value="Learn biology",
        )
        AddDeclaredIdentityAttributeService().execute(
            profile_version_id=self.draft.id,
            actor=self.learner,
            attribute_type=LearningAttributeType.ACCESSIBILITY_PREFERENCE,
            value="Prefer captions",
            visibility=AttributeVisibility.RESTRICTED,
            restricted=True,
        )
        self.profile.refresh_from_db()
        PublishLearningProfileVersionService().execute(profile_version_id=self.draft.id, actor=self.learner, expected_version=self.profile.version)

    def test_learner_safe_summary_omits_restricted_attributes(self):
        summary = GetLearnerSafeProfileSummary().execute(profile_id=self.profile.id, actor=self.learner)
        self.assertEqual(summary.current_version_number, 1)
        self.assertEqual([item.attribute_type for item in summary.attributes], [LearningAttributeType.STUDY_GOAL])
        self.assertEqual(summary.attributes[0].learner_safe_value, "Learn biology")

    def test_cross_tenant_query_fails_closed(self):
        with self.assertRaises(PermissionDenied):
            GetLearnerSafeProfileSummary().execute(profile_id=self.profile.id, actor=self.other)

