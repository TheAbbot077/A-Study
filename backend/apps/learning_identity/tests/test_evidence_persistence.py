from datetime import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from apps.learning_identity.domain.enums import (
    AttributeClassification,
    AttributeSourceType,
    AttributeVisibility,
    EvidenceAuthorityClass,
    EvidenceRelationship,
    EvidenceSourceDomain,
    EvidenceSourceType,
    LearningAttributeType,
)
from apps.learning_identity.domain.models import LearnerLearningProfile, LearningIdentityAttribute, LearningIdentityEvidenceLink, LearningProfileVersion
from apps.users.domain.models import Institution, InstitutionMembership, User


class EvidencePersistenceTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        self.profile = LearnerLearningProfile.objects.create(tenant=self.tenant, learner=self.learner)
        self.version = LearningProfileVersion.objects.create(profile=self.profile, version_number=1, created_by=self.learner)
        self.attribute = LearningIdentityAttribute.objects.create(
            profile_version=self.version,
            attribute_type=LearningAttributeType.STUDY_GOAL,
            classification=AttributeClassification.DECLARED,
            value="Learn biology",
            source_type=AttributeSourceType.LEARNER,
            visibility=AttributeVisibility.LEARNER_VISIBLE,
            created_by=self.learner,
        )

    def _link(self, **overrides):
        values = {
            "attribute": self.attribute,
            "source_domain": EvidenceSourceDomain.LEARNING_IDENTITY,
            "source_type": EvidenceSourceType.LEARNER_DECLARATION,
            "source_identifier": str(self.attribute.id),
            "source_revision": "r1",
            "relationship": EvidenceRelationship.SUPPORTS,
            "authority_class": EvidenceAuthorityClass.DECLARATIVE,
            "linked_by": self.learner,
        }
        values.update(overrides)
        return LearningIdentityEvidenceLink.objects.create(**values)

    def test_duplicate_active_semantic_link_rejected(self):
        self._link()
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._link()

    def test_bounds_and_ordering_constraints(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._link(source_identifier="weight", weight=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._link(source_identifier="confidence", confidence_contribution=2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._link(source_identifier="validity", valid_from="2026-02-01", valid_until="2026-01-01")
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._link(
                source_identifier="freshness",
                source_observed_at=datetime(2026, 2, 1, tzinfo=timezone.get_current_timezone()),
                freshness_expires_at=datetime(2026, 1, 1, tzinfo=timezone.get_current_timezone()),
            )
