from django.core.exceptions import PermissionDenied
from django.test import TestCase

from apps.learning_identity.application.evidence_services import LinkLearningIdentityEvidenceService, MarkLearningIdentityEvidenceStaleService
from apps.learning_identity.application.provenance_queries import (
    GetAttributeProvenance,
    GetLearnerSafeProvenanceSummary,
    GetProfileVersionProvenanceReadiness,
    ListProfileVersionEvidence,
)
from apps.learning_identity.application.services import AddDeclaredIdentityAttributeService, CreateDraftProfileVersionService, CreateLearningProfileService
from apps.learning_identity.domain.enums import EvidenceRelationship, EvidenceSourceDomain, EvidenceSourceType, LearningAttributeType
from apps.users.domain.models import Institution, InstitutionMembership, User


class ProvenanceQueryTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.other = User.objects.create_user(email="other@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        self.profile = CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.learner)
        self.version = CreateDraftProfileVersionService().execute(profile_id=self.profile.id, actor=self.learner, expected_version=self.profile.version)
        self.attribute = AddDeclaredIdentityAttributeService().execute(
            profile_version_id=self.version.id,
            actor=self.learner,
            attribute_type=LearningAttributeType.STUDY_GOAL,
            value="Learn biology",
        )
        self.profile.refresh_from_db()
        self.link = LinkLearningIdentityEvidenceService().execute(
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

    def test_internal_queries_return_deterministic_safe_metadata(self):
        attribute_links = GetAttributeProvenance().execute(attribute_id=self.attribute.id, actor=self.learner)
        version_links = ListProfileVersionEvidence().execute(profile_version_id=self.version.id, actor=self.learner)
        self.assertEqual([item.evidence_link_id for item in attribute_links], [str(self.link.id)])
        self.assertEqual([item.evidence_link_id for item in version_links], [str(self.link.id)])
        self.assertEqual(attribute_links[0].safe_summary, "Declared by the learner")

    def test_readiness_and_learner_safe_summary_hide_internal_source_identifiers(self):
        readiness = GetProfileVersionProvenanceReadiness().execute(profile_version_id=self.version.id, actor=self.learner)
        self.assertEqual(readiness.status, "READY")

        self.profile.refresh_from_db()
        MarkLearningIdentityEvidenceStaleService().execute(
            evidence_link_id=self.link.id,
            actor=self.learner,
            reason_code="SOURCE_STALE",
            expected_version=self.profile.version,
        )
        safe = GetLearnerSafeProvenanceSummary().execute(profile_version_id=self.version.id, actor=self.learner)
        self.assertIn("This information may be out of date.", safe)
        self.assertNotIn(str(self.link.source_identifier), " ".join(safe))

    def test_cross_learner_query_rejected(self):
        with self.assertRaises(PermissionDenied):
            ListProfileVersionEvidence().execute(profile_version_id=self.version.id, actor=self.other)

