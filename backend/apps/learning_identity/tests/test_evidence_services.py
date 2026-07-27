from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from apps.learning_identity.application.evidence_services import (
    InvalidateLearningIdentityEvidenceService,
    LinkLearningIdentityEvidenceService,
    MarkLearningIdentityEvidenceStaleService,
    WithdrawLearningIdentityEvidenceService,
)
from apps.learning_identity.application.services import AddDeclaredIdentityAttributeService, CreateDraftProfileVersionService, CreateLearningProfileService
from apps.learning_identity.domain.enums import EvidenceRelationship, EvidenceSourceDomain, EvidenceSourceType, LearningAttributeType
from apps.learning_identity.domain.models import LearningIdentityEvidenceLink
from apps.users.domain.models import Institution, InstitutionMembership, InstitutionRole, User


class EvidenceServiceTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.admin = User.objects.create_user(email="admin@example.com", password="test")
        self.other = User.objects.create_user(email="other@example.com", password="test")
        self.membership = InstitutionMembership.objects.create(
            user=self.learner,
            institution=self.tenant,
            role=InstitutionRole.STUDENT,
            is_active=True,
        )
        InstitutionMembership.objects.create(user=self.admin, institution=self.tenant, role=InstitutionRole.ADMINISTRATOR, is_active=True)
        self.profile = CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.learner)
        self.version = CreateDraftProfileVersionService().execute(profile_id=self.profile.id, actor=self.learner, expected_version=self.profile.version)
        self.attribute = AddDeclaredIdentityAttributeService().execute(
            profile_version_id=self.version.id,
            actor=self.learner,
            attribute_type=LearningAttributeType.STUDY_GOAL,
            value="Learn biology",
        )
        self.profile.refresh_from_db()

    def test_link_declaration_support_is_idempotent_and_preserves_safe_metadata(self):
        service = LinkLearningIdentityEvidenceService()
        link = service.execute(
            profile_id=self.profile.id,
            profile_version_id=self.version.id,
            attribute_id=self.attribute.id,
            source_domain=EvidenceSourceDomain.LEARNING_IDENTITY,
            source_type=EvidenceSourceType.LEARNER_DECLARATION,
            source_identifier=str(self.attribute.id),
            relationship=EvidenceRelationship.SUPPORTS,
            actor=self.learner,
            expected_version=self.profile.version,
            idempotency_key="link",
        )
        repeated = service.execute(
            profile_id=self.profile.id,
            profile_version_id=self.version.id,
            attribute_id=self.attribute.id,
            source_domain=EvidenceSourceDomain.LEARNING_IDENTITY,
            source_type=EvidenceSourceType.LEARNER_DECLARATION,
            source_identifier=str(self.attribute.id),
            relationship=EvidenceRelationship.SUPPORTS,
            actor=self.learner,
            expected_version=self.profile.version,
            idempotency_key="link",
        )
        self.assertEqual(link.id, repeated.id)
        self.assertEqual(link.authority_class, "DECLARATIVE")
        self.assertNotIn("Learn biology", link.safe_summary)

    def test_cross_tenant_or_wrong_learner_source_rejected(self):
        with self.assertRaises(PermissionDenied):
            LinkLearningIdentityEvidenceService().execute(
                profile_id=self.profile.id,
                profile_version_id=self.version.id,
                attribute_id=self.attribute.id,
                source_domain=EvidenceSourceDomain.INSTITUTION,
                source_type=EvidenceSourceType.INSTITUTIONAL_MEMBERSHIP,
                source_identifier=str(InstitutionMembership.objects.create(user=self.other, institution=self.tenant).id),
                relationship=EvidenceRelationship.CONFIRMS,
                actor=self.admin,
                expected_version=self.profile.version,
            )

    def test_contradiction_marks_review_and_lifecycle_preserves_history(self):
        link = LinkLearningIdentityEvidenceService().execute(
            profile_id=self.profile.id,
            profile_version_id=self.version.id,
            attribute_id=self.attribute.id,
            source_domain=EvidenceSourceDomain.INSTITUTION,
            source_type=EvidenceSourceType.INSTITUTIONAL_MEMBERSHIP,
            source_identifier=str(self.membership.id),
            relationship=EvidenceRelationship.CONTRADICTS,
            actor=self.admin,
            expected_version=self.profile.version,
        )
        self.attribute.refresh_from_db()
        self.assertTrue(self.attribute.review_required)

        self.profile.refresh_from_db()
        stale = MarkLearningIdentityEvidenceStaleService().execute(
            evidence_link_id=link.id,
            actor=self.admin,
            reason_code="SOURCE_STALE",
            expected_version=self.profile.version,
        )
        self.assertEqual(stale.status, "STALE")

        self.profile.refresh_from_db()
        withdrawn = WithdrawLearningIdentityEvidenceService().execute(
            evidence_link_id=link.id,
            actor=self.admin,
            reason_code="SOURCE_WITHDRAWN",
            expected_version=self.profile.version,
        )
        self.assertEqual(withdrawn.status, "WITHDRAWN")
        self.assertEqual(LearningIdentityEvidenceLink.objects.count(), 1)

    def test_invalidate_requires_institutional_authority(self):
        link = LinkLearningIdentityEvidenceService().execute(
            profile_id=self.profile.id,
            profile_version_id=self.version.id,
            attribute_id=self.attribute.id,
            source_domain=EvidenceSourceDomain.LEARNING_IDENTITY,
            source_type=EvidenceSourceType.LEARNER_DECLARATION,
            source_identifier=str(self.attribute.id),
            relationship=EvidenceRelationship.SUPPORTS,
            actor=self.learner,
            expected_version=self.profile.version,
        )
        self.profile.refresh_from_db()
        with self.assertRaises(PermissionDenied):
            InvalidateLearningIdentityEvidenceService().execute(
                evidence_link_id=link.id,
                actor=self.learner,
                reason_code="SOURCE_INVALIDATED",
                expected_version=self.profile.version,
            )
