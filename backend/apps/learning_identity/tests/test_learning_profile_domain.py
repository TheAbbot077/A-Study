from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

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


class LearningProfileDomainTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.actor = self.learner
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        self.profile = LearnerLearningProfile.objects.create(tenant=self.tenant, learner=self.learner)
        self.version = LearningProfileVersion.objects.create(profile=self.profile, version_number=1, created_by=self.actor)

    def test_profile_lifecycle_restrict_and_archive_preserve_history(self):
        self.profile.restrict(reason="privacy review")
        self.profile.full_clean()
        self.assertEqual(self.profile.status, LearningProfileStatus.RESTRICTED)
        self.assertIsNotNone(self.profile.restricted_at)

        self.profile.archive()
        self.profile.full_clean()
        self.assertEqual(self.profile.status, LearningProfileStatus.ARCHIVED)
        self.assertIsNotNone(self.profile.archived_at)

    def test_archived_profile_cannot_receive_draft(self):
        self.profile.archive()
        with self.assertRaises(ValidationError):
            self.profile.ensure_can_receive_draft()

    def test_published_version_is_not_mutable_for_attribute_creation(self):
        self.version.publish(actor=self.actor)
        with self.assertRaisesMessage(ValidationError, "Only draft profile versions may be modified"):
            LearningIdentityAttribute(
                profile_version=self.version,
                attribute_type=LearningAttributeType.STUDY_GOAL,
                classification=AttributeClassification.DECLARED,
                value="Learn biology",
                source_type=AttributeSourceType.LEARNER,
                visibility=AttributeVisibility.LEARNER_VISIBLE,
                created_by=self.actor,
            ).full_clean()

    def test_declared_attribute_validation_and_safe_vocabulary(self):
        attribute = LearningIdentityAttribute(
            profile_version=self.version,
            attribute_type=LearningAttributeType.WEEKLY_STUDY_CAPACITY,
            classification=AttributeClassification.DECLARED,
            value=300,
            source_type=AttributeSourceType.LEARNER,
            visibility=AttributeVisibility.LEARNER_VISIBLE,
            created_by=self.actor,
        )
        attribute.full_clean()
        self.assertEqual(attribute.value, 300)

        harmful = LearningIdentityAttribute(
            profile_version=self.version,
            attribute_type=LearningAttributeType.PREFERRED_EXPLANATION_FORMAT,
            classification=AttributeClassification.DECLARED,
            value="I am a visual learner",
            source_type=AttributeSourceType.LEARNER,
            visibility=AttributeVisibility.LEARNER_VISIBLE,
            created_by=self.actor,
        )
        with self.assertRaises(ValidationError):
            harmful.full_clean()

    def test_non_declared_attributes_require_provenance_and_confidence_where_needed(self):
        verified = LearningIdentityAttribute(
            profile_version=self.version,
            attribute_type=LearningAttributeType.TARGET_QUALIFICATION,
            classification=AttributeClassification.VERIFIED,
            value="Cambridge International A Level",
            source_type=AttributeSourceType.INSTITUTION,
            visibility=AttributeVisibility.AUTHORIZED_STAFF,
            created_by=self.actor,
        )
        with self.assertRaises(ValidationError):
            verified.full_clean()

        observed = LearningIdentityAttribute(
            profile_version=self.version,
            attribute_type=LearningAttributeType.PRIOR_STUDY_EXPERIENCE,
            classification=AttributeClassification.OBSERVED,
            value="Completed introductory unit",
            source_type=AttributeSourceType.ASSESSMENT,
            source_reference={"attempt_id": "attempt-1"},
            visibility=AttributeVisibility.AUTHORIZED_STAFF,
            created_by=self.actor,
        )
        with self.assertRaises(ValidationError):
            observed.full_clean()

        observed.confidence = Decimal("0.700")
        observed.full_clean()

    def test_restricted_attribute_cannot_be_learner_visible(self):
        attribute = LearningIdentityAttribute(
            profile_version=self.version,
            attribute_type=LearningAttributeType.ACCESSIBILITY_PREFERENCE,
            classification=AttributeClassification.DECLARED,
            value="Prefer captions",
            source_type=AttributeSourceType.LEARNER,
            visibility=AttributeVisibility.LEARNER_VISIBLE,
            restricted=True,
            created_by=self.actor,
        )
        with self.assertRaises(ValidationError):
            attribute.full_clean()

    def test_supersession_requires_same_profile_published_predecessor(self):
        other_profile = LearnerLearningProfile.objects.create(
            tenant=self.tenant,
            learner=User.objects.create_user(email="other@example.com", password="test"),
        )
        other_version = LearningProfileVersion.objects.create(profile=other_profile, version_number=1, created_by=self.actor)
        self.version.publish(actor=self.actor)
        second = LearningProfileVersion(profile=self.profile, version_number=2, created_by=self.actor, supersedes_version=other_version)
        second.status = ProfileVersionStatus.PUBLISHED
        with self.assertRaises(ValidationError):
            second.full_clean()
