from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.learning_identity.application.evidence_services import LinkLearningIdentityEvidenceService
from apps.learning_identity.application.services import AddDeclaredIdentityAttributeService, CreateDraftProfileVersionService, CreateLearningProfileService, PublishLearningProfileVersionService
from apps.learning_identity.domain.enums import (
    AttributeClassification,
    AttributeSourceType,
    AttributeVisibility,
    EvidenceRelationship,
    EvidenceSourceDomain,
    EvidenceSourceType,
    LearningAttributeType,
)
from apps.learning_identity.domain.models import LearningIdentityAttribute
from apps.users.domain.models import Institution, InstitutionMembership, InstitutionRole, User


class ProvenancePublicationTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.admin = User.objects.create_user(email="admin@example.com", password="test")
        self.membership = InstitutionMembership.objects.create(
            user=self.learner,
            institution=self.tenant,
            role=InstitutionRole.STUDENT,
            is_active=True,
        )
        InstitutionMembership.objects.create(user=self.admin, institution=self.tenant, role=InstitutionRole.ADMINISTRATOR, is_active=True)

    def _draft(self):
        profile = CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.learner)
        draft = CreateDraftProfileVersionService().execute(profile_id=profile.id, actor=self.learner, expected_version=profile.version)
        return profile, draft

    def test_declared_attribute_with_declaration_provenance_publishes(self):
        profile, draft = self._draft()
        AddDeclaredIdentityAttributeService().execute(
            profile_version_id=draft.id,
            actor=self.learner,
            attribute_type=LearningAttributeType.STUDY_GOAL,
            value="Learn biology",
        )
        profile.refresh_from_db()
        published = PublishLearningProfileVersionService().execute(profile_version_id=draft.id, actor=self.learner, expected_version=profile.version)
        self.assertEqual(published.status, "PUBLISHED")

    def test_declared_attribute_without_declaration_source_blocks(self):
        profile, draft = self._draft()
        LearningIdentityAttribute.objects.create(
            profile_version=draft,
            attribute_type=LearningAttributeType.STUDY_GOAL,
            classification=AttributeClassification.DECLARED,
            value="Learn biology",
            source_type=AttributeSourceType.LEARNER,
            visibility=AttributeVisibility.LEARNER_VISIBLE,
            created_by=self.learner,
        )
        profile.refresh_from_db()
        with self.assertRaises(ValidationError):
            PublishLearningProfileVersionService().execute(profile_version_id=draft.id, actor=self.learner, expected_version=profile.version)

    def test_verified_attribute_requires_active_authoritative_confirming_evidence(self):
        profile, draft = self._draft()
        verified = LearningIdentityAttribute.objects.create(
            profile_version=draft,
            attribute_type=LearningAttributeType.TARGET_QUALIFICATION,
            classification=AttributeClassification.VERIFIED,
            value="Cambridge International A Level",
            source_type=AttributeSourceType.INSTITUTION,
            source_reference={"record": "membership"},
            visibility=AttributeVisibility.AUTHORIZED_STAFF,
            created_by=self.admin,
        )
        profile.refresh_from_db()
        with self.assertRaises(ValidationError):
            PublishLearningProfileVersionService().execute(profile_version_id=draft.id, actor=self.admin, expected_version=profile.version)

        LinkLearningIdentityEvidenceService().execute(
            profile_id=profile.id,
            profile_version_id=draft.id,
            attribute_id=verified.id,
            source_domain=EvidenceSourceDomain.INSTITUTION,
            source_type=EvidenceSourceType.INSTITUTIONAL_MEMBERSHIP,
            source_identifier=str(self.membership.id),
            relationship=EvidenceRelationship.CONFIRMS,
            actor=self.admin,
            expected_version=profile.version,
        )
        profile.refresh_from_db()
        published = PublishLearningProfileVersionService().execute(profile_version_id=draft.id, actor=self.admin, expected_version=profile.version)
        self.assertEqual(published.status, "PUBLISHED")
