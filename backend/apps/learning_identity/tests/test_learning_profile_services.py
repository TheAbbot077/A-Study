from unittest.mock import Mock, patch

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from apps.learning_identity.application.services import (
    AddDeclaredIdentityAttributeService,
    ArchiveLearningProfileService,
    CreateDraftProfileVersionService,
    CreateLearningProfileService,
    PublishLearningProfileVersionService,
    RestrictLearningProfileService,
)
from apps.learning_identity.domain.enums import LearningAttributeType, LearningProfileStatus, ProfileVersionStatus
from apps.learning_identity.domain.models import LearnerLearningProfile, LearningIdentityAttribute, LearningProfileVersion
from apps.users.domain.models import Institution, InstitutionMembership, InstitutionRole, User


class LearningProfileServiceTests(TestCase):
    def setUp(self):
        self.tenant = Institution.objects.create(name="Demo Tenant", slug="demo-tenant")
        self.other_tenant = Institution.objects.create(name="Other Tenant", slug="other-tenant")
        self.learner = User.objects.create_user(email="learner@example.com", password="test")
        self.actor = self.learner
        self.admin = User.objects.create_user(email="admin@example.com", password="test")
        InstitutionMembership.objects.create(user=self.learner, institution=self.tenant, is_active=True)
        InstitutionMembership.objects.create(
            user=self.admin,
            institution=self.tenant,
            role=InstitutionRole.ADMINISTRATOR,
            is_active=True,
        )

    def test_create_profile_is_idempotent_and_rejects_second_open_profile(self):
        events = Mock()
        service = CreateLearningProfileService(events=events)
        with patch("apps.learning_identity.application.services.transaction.on_commit") as on_commit:
            first = service.execute(tenant=self.tenant, learner=self.learner, actor=self.actor, idempotency_key="create")
            second = service.execute(tenant=self.tenant, learner=self.learner, actor=self.actor, idempotency_key="create")

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.status, LearningProfileStatus.DRAFT)
        self.assertEqual(LearnerLearningProfile.objects.filter(tenant=self.tenant, learner=self.learner).count(), 1)
        self.assertTrue(on_commit.called)

        with self.assertRaises(ValidationError):
            service.execute(tenant=self.tenant, learner=self.learner, actor=self.actor, idempotency_key="other")

    def test_cross_tenant_profile_creation_is_rejected(self):
        with self.assertRaises(PermissionDenied):
            CreateLearningProfileService().execute(tenant=self.other_tenant, learner=self.learner, actor=self.actor)

    def test_draft_attribute_publish_and_supersession_flow(self):
        profile = CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.actor)
        draft = CreateDraftProfileVersionService().execute(profile_id=profile.id, actor=self.actor, expected_version=profile.version)
        attribute = AddDeclaredIdentityAttributeService().execute(
            profile_version_id=draft.id,
            actor=self.actor,
            attribute_type=LearningAttributeType.STUDY_GOAL,
            value="Learn biology for an exam",
            idempotency_key="goal",
        )
        repeated = AddDeclaredIdentityAttributeService().execute(
            profile_version_id=draft.id,
            actor=self.actor,
            attribute_type=LearningAttributeType.STUDY_GOAL,
            value="Learn biology for an exam",
            idempotency_key="goal",
        )
        self.assertEqual(attribute.id, repeated.id)

        profile.refresh_from_db()
        published = PublishLearningProfileVersionService().execute(profile_version_id=draft.id, actor=self.actor, expected_version=profile.version)
        profile.refresh_from_db()
        self.assertEqual(published.status, ProfileVersionStatus.PUBLISHED)
        self.assertEqual(profile.current_version_id, published.id)
        self.assertEqual(profile.status, LearningProfileStatus.ACTIVE)

        next_draft = CreateDraftProfileVersionService().execute(profile_id=profile.id, actor=self.actor, expected_version=profile.version)
        AddDeclaredIdentityAttributeService().execute(
            profile_version_id=next_draft.id,
            actor=self.actor,
            attribute_type=LearningAttributeType.WEEKLY_STUDY_CAPACITY,
            value=240,
        )
        profile.refresh_from_db()
        second_published = PublishLearningProfileVersionService().execute(profile_version_id=next_draft.id, actor=self.actor, expected_version=profile.version)
        published.refresh_from_db()
        self.assertEqual(published.status, ProfileVersionStatus.SUPERSEDED)
        self.assertEqual(second_published.supersedes_version_id, published.id)

    def test_expected_version_conflict_is_rejected(self):
        profile = CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.actor)
        with self.assertRaises(ValidationError):
            CreateDraftProfileVersionService().execute(profile_id=profile.id, actor=self.actor, expected_version=profile.version + 1)

    def test_restrict_and_archive_preserve_history(self):
        profile = CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.actor)
        restricted = RestrictLearningProfileService().execute(profile_id=profile.id, actor=self.admin, expected_version=profile.version, reason="privacy")
        self.assertEqual(restricted.status, LearningProfileStatus.RESTRICTED)
        archived = ArchiveLearningProfileService().execute(profile_id=profile.id, actor=self.admin, expected_version=restricted.version)
        self.assertEqual(archived.status, LearningProfileStatus.ARCHIVED)

    def test_no_cross_domain_records_are_created(self):
        from apps.academic.models import Subject
        from apps.self_study.models import SelfStudyIntent

        subject_count = Subject.objects.count()
        intent_count = SelfStudyIntent.objects.count()
        CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.actor)
        self.assertEqual(Subject.objects.count(), subject_count)
        self.assertEqual(SelfStudyIntent.objects.count(), intent_count)

    def test_client_cannot_create_observed_attribute_through_declared_command(self):
        profile = CreateLearningProfileService().execute(tenant=self.tenant, learner=self.learner, actor=self.actor)
        draft = CreateDraftProfileVersionService().execute(profile_id=profile.id, actor=self.actor, expected_version=profile.version)
        attribute = AddDeclaredIdentityAttributeService().execute(
            profile_version_id=draft.id,
            actor=self.actor,
            attribute_type=LearningAttributeType.PREFERRED_LEARNING_LANGUAGE,
            value="en",
        )
        self.assertEqual(attribute.classification, "DECLARED")
        self.assertEqual(LearningIdentityAttribute.objects.count(), 1)
