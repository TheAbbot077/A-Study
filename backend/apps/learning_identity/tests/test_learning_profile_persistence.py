from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.learning_identity.domain.enums import (
    AttributeClassification,
    AttributeSourceType,
    AttributeVisibility,
    LearningAttributeType,
    LearningProfileStatus,
    ProfileVersionStatus,
)
from apps.learning_identity.domain.models import LearnerLearningProfile, LearningIdentityAttribute, LearningProfileVersion
from apps.users.domain.models import Institution, InstitutionMembership, User


class LearningProfilePersistenceTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        self.profile = LearnerLearningProfile.objects.create(tenant=self.tenant, learner=self.learner)

    def test_one_non_archived_profile_per_learner_and_tenant(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            LearnerLearningProfile.objects.create(tenant=self.tenant, learner=self.learner)

        self.profile.status = LearningProfileStatus.ARCHIVED
        self.profile.archived_at = timezone.now()
        self.profile.save()
        LearnerLearningProfile.objects.create(tenant=self.tenant, learner=self.learner)
        self.assertEqual(LearnerLearningProfile.objects.filter(tenant=self.tenant, learner=self.learner).count(), 2)

    def test_unique_version_number_and_single_draft_constraints(self):
        LearningProfileVersion.objects.create(profile=self.profile, version_number=1, created_by=self.learner)
        with self.assertRaises(IntegrityError), transaction.atomic():
            LearningProfileVersion.objects.create(profile=self.profile, version_number=1, created_by=self.learner)

        published = LearningProfileVersion.objects.get(profile=self.profile, version_number=1)
        published.status = ProfileVersionStatus.PUBLISHED
        published.published_by = self.learner
        published.published_at = timezone.now()
        published.save()
        LearningProfileVersion.objects.create(profile=self.profile, version_number=2, created_by=self.learner)
        with self.assertRaises(IntegrityError), transaction.atomic():
            LearningProfileVersion.objects.create(profile=self.profile, version_number=3, created_by=self.learner)

    def test_attribute_constraints_for_confidence_dates_and_restricted_visibility(self):
        version = LearningProfileVersion.objects.create(profile=self.profile, version_number=1, created_by=self.learner)
        with self.assertRaises(IntegrityError), transaction.atomic():
            LearningIdentityAttribute.objects.create(
                profile_version=version,
                attribute_type=LearningAttributeType.STUDY_GOAL,
                classification=AttributeClassification.OBSERVED,
                value="Observed study signal",
                confidence=2,
                source_type=AttributeSourceType.ASSESSMENT,
                visibility=AttributeVisibility.AUTHORIZED_STAFF,
                created_by=self.learner,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            LearningIdentityAttribute.objects.create(
                profile_version=version,
                attribute_type=LearningAttributeType.ACCESSIBILITY_PREFERENCE,
                classification=AttributeClassification.DECLARED,
                value="Prefer captions",
                source_type=AttributeSourceType.LEARNER,
                visibility=AttributeVisibility.LEARNER_VISIBLE,
                restricted=True,
                created_by=self.learner,
            )
