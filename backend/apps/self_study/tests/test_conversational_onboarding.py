from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.academic.models import Subject
from apps.self_study.application.onboarding_services import SelfStudyConversationalOnboardingService
from apps.self_study.curriculum_models import (
    AuthorityType,
    CandidateEligibility,
    CurriculumAuthority,
    CurriculumReference,
    CurriculumResolutionCandidate,
    CurriculumSubjectBinding,
    CurriculumVersion,
    CurriculumVersionStatus,
    MatchClassification,
    ProvenanceStatus,
    RegistryStatus,
    SourceClassification,
    VerificationStatus,
)
from apps.self_study.models import LearningPolicyRuleSet, SelfStudyIntent
from apps.self_study.onboarding_models import SelfStudyOnboarding, SelfStudyOnboardingIntent, SelfStudyOnboardingStage
from apps.self_study.workspace_models import SelfStudyWorkspace
from apps.users.models import Institution


def configure_active_platform_policy() -> LearningPolicyRuleSet:
    policy, _ = LearningPolicyRuleSet.objects.get_or_create(
        authority=LearningPolicyRuleSet.Authority.PLATFORM,
        is_active=True,
        defaults={
            "allowed_provider_ids": ["registry"],
            "allowed_source_categories": ["OPEN_EDUCATIONAL_RESOURCE"],
            "allowed_licence_categories": ["official"],
            "allowed_mime_types": ["application/pdf"],
            "allowed_languages": ["en"],
            "maximum_resource_count": 10,
            "maximum_single_file_bytes": 10_000,
            "maximum_total_bytes": 100_000,
        },
    )
    policy.allowed_provider_ids = ["registry"]
    policy.allowed_source_categories = ["OPEN_EDUCATIONAL_RESOURCE"]
    policy.allowed_licence_categories = ["official"]
    policy.allowed_mime_types = ["application/pdf"]
    policy.allowed_languages = ["en"]
    policy.maximum_resource_count = 10
    policy.maximum_single_file_bytes = 10_000
    policy.maximum_total_bytes = 100_000
    policy.save()
    return policy


class ConversationalOnboardingServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(email="learner@example.com", password="pw")
        self.tenant = Institution.objects.create(name="Learner Space", slug="learner-space", institution_type="individual")
        self.subject = Subject.objects.create(institution=self.tenant, code="BIO", name="Biology")
        self.platform_policy = configure_active_platform_policy()
        self.assertEqual(
            LearningPolicyRuleSet.objects.filter(
                authority=LearningPolicyRuleSet.Authority.PLATFORM,
                is_active=True,
            ).count(),
            1,
        )
        self.workspace = SelfStudyWorkspace.objects.create(
            tenant=self.tenant,
            learner=self.user,
            display_name="Biology",
        )
        authority = CurriculumAuthority.objects.create(
            canonical_key="cambridge-international",
            name="Cambridge International",
            authority_type=AuthorityType.QUALIFICATION_PROVIDER,
            verification_status=VerificationStatus.VERIFIED,
            status=RegistryStatus.ACTIVE,
        )
        reference = CurriculumReference.objects.create(
            canonical_key="cambridge-a-level-biology",
            title="Cambridge International AS & A Level Biology",
            subject_area="Biology",
            authority=authority,
            source_classification=SourceClassification.INSTITUTION_OR_QUALIFICATION,
            jurisdiction="International",
            education_stage="A Level",
            qualification_type="A Level",
            language="en",
            status=RegistryStatus.ACTIVE,
        )
        self.version = CurriculumVersion.objects.create(
            curriculum_reference=reference,
            version_label="2026",
            status=CurriculumVersionStatus.ACTIVE,
            canonical_source_uri="https://example.test/biology",
            content_hash="hash",
            licence_identifier="official",
            provenance_status=ProvenanceStatus.COMPLETE,
            language="en",
            jurisdiction="International",
            education_stage="A Level",
            qualification_type="A Level",
            created_by=self.user,
        )
        CurriculumSubjectBinding.objects.create(
            curriculum_version=self.version,
            subject=self.subject,
            tenant=self.tenant,
            created_by=self.user,
            authority_note="Governed fixture binding",
        )

    def test_start_is_idempotent_for_workspace_key(self):
        service = SelfStudyConversationalOnboardingService()

        first = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="same")
        second = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="same")

        self.assertEqual(first.id, second.id)
        self.assertEqual(first.current_stage, SelfStudyOnboardingStage.STUDY_TOPIC)

    def test_reading_onboarding_does_not_create_or_advance_session(self):
        service = SelfStudyConversationalOnboardingService()

        self.assertIsNone(service.get_for_workspace(workspace_id=self.workspace.id, actor=self.user))
        self.assertEqual(SelfStudyOnboarding.objects.count(), 0)

    def test_start_resumes_existing_active_session_without_duplicate(self):
        service = SelfStudyConversationalOnboardingService()

        first = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="first")
        second = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="second")

        self.assertEqual(first.id, second.id)
        self.assertEqual(SelfStudyOnboarding.objects.count(), 1)

    def test_context_update_advances_to_curriculum_discovery(self):
        service = SelfStudyConversationalOnboardingService()
        onboarding = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="context")

        updated = service.update_context(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            changes={
                "topic_query": "Biology",
                "study_intent": SelfStudyOnboardingIntent.EXAM,
                "qualification_query": "Cambridge International A Level",
            },
        )

        self.assertEqual(updated.current_stage, SelfStudyOnboardingStage.CURRICULUM_DISCOVERY)

    def test_candidates_are_projected_from_resolver_attempt(self):
        service = SelfStudyConversationalOnboardingService()
        onboarding = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="candidate")
        onboarding = service.update_context(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            changes={
                "topic_query": "Biology",
                "study_intent": SelfStudyOnboardingIntent.EXAM,
                "qualification_query": "Cambridge International A Level",
            },
        )
        onboarding = service.resolve_curriculum(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
        )

        candidates = service.candidates(onboarding_id=onboarding.id, actor=self.user)

        self.assertEqual(candidates[0]["curriculum_version_id"], str(self.version.id))
        self.assertEqual(candidates[0]["resolution_attempt_id"], str(onboarding.active_resolution_attempt_id))
        self.assertTrue(CurriculumResolutionCandidate.objects.filter(id=candidates[0]["candidate_id"]).exists())
        self.assertEqual(candidates[0]["authority"], "Cambridge International")

    def test_selection_rejects_candidate_not_offered_by_session(self):
        service = SelfStudyConversationalOnboardingService()
        onboarding = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="foreign")
        onboarding = service.update_context(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            changes={"topic_query": "Chemistry", "study_intent": SelfStudyOnboardingIntent.LEARN_NEW},
        )
        onboarding = service.resolve_curriculum(onboarding_id=onboarding.id, actor=self.user, expected_version=onboarding.version)

        with self.assertRaisesMessage(Exception, "Selected curriculum was not offered"):
            service.select_candidate(
                onboarding_id=onboarding.id,
                actor=self.user,
                expected_version=onboarding.version,
                candidate_id=self.version.id,
            )

    def test_selection_rejects_stale_expected_version(self):
        service = SelfStudyConversationalOnboardingService()
        onboarding = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="stale-version")
        onboarding = service.update_context(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            changes={
                "topic_query": "Biology",
                "study_intent": SelfStudyOnboardingIntent.EXAM,
                "qualification_query": "Cambridge International A Level",
            },
        )
        onboarding = service.resolve_curriculum(onboarding_id=onboarding.id, actor=self.user, expected_version=onboarding.version)
        candidate = service.candidates(onboarding_id=onboarding.id, actor=self.user)[0]

        with self.assertRaisesMessage(Exception, "Onboarding version is stale"):
            service.select_candidate(
                onboarding_id=onboarding.id,
                actor=self.user,
                expected_version=onboarding.version - 1,
                candidate_id=candidate["candidate_id"],
            )

    def test_completion_uses_governed_subject_binding_without_creating_subject(self):
        service = SelfStudyConversationalOnboardingService()
        onboarding = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="complete")
        onboarding = service.update_context(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            changes={
                "topic_query": "Biology",
                "study_intent": SelfStudyOnboardingIntent.EXAM,
                "qualification_query": "Cambridge International A Level",
                "weekly_study_minutes": 300,
            },
        )
        onboarding = service.resolve_curriculum(onboarding_id=onboarding.id, actor=self.user, expected_version=onboarding.version)
        candidate = service.candidates(onboarding_id=onboarding.id, actor=self.user)[0]
        resolver_candidate = CurriculumResolutionCandidate.objects.get(id=candidate["candidate_id"])
        self.assertEqual(resolver_candidate.attempt_id, onboarding.active_resolution_attempt_id)
        self.assertEqual(resolver_candidate.curriculum_version_id, self.version.id)
        self.assertEqual(resolver_candidate.eligibility, CandidateEligibility.ELIGIBLE)
        self.assertIn(
            resolver_candidate.match_classification,
            {MatchClassification.EXACT, MatchClassification.STRONG},
        )
        onboarding = service.select_candidate(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            candidate_id=candidate["candidate_id"],
        )
        subject_count = Subject.objects.count()

        completed = service.complete(onboarding_id=onboarding.id, actor=self.user, expected_version=onboarding.version)

        self.assertEqual(Subject.objects.count(), subject_count)
        self.assertEqual(completed.created_intent.subject_id, self.subject.id)
        self.assertEqual(completed.selected_resolution_candidate_id, resolver_candidate.id)

    def test_candidate_without_subject_binding_is_not_selectable(self):
        CurriculumSubjectBinding.objects.all().delete()
        service = SelfStudyConversationalOnboardingService()
        onboarding = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="unbound")
        onboarding = service.update_context(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            changes={
                "topic_query": "Biology",
                "study_intent": SelfStudyOnboardingIntent.EXAM,
                "qualification_query": "Cambridge International A Level",
            },
        )
        onboarding = service.resolve_curriculum(onboarding_id=onboarding.id, actor=self.user, expected_version=onboarding.version)

        candidate = service.candidates(onboarding_id=onboarding.id, actor=self.user)[0]

        self.assertFalse(candidate["selectable"])
        self.assertIn("CURRICULUM_SUBJECT_BINDING_MISSING", candidate["blocker_codes"])

    def test_weak_or_partial_candidate_is_visible_but_not_selectable(self):
        service = SelfStudyConversationalOnboardingService()
        onboarding = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="weak-candidate")
        onboarding = service.update_context(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            changes={
                "topic_query": "Biology",
                "study_intent": SelfStudyOnboardingIntent.LEARN_NEW,
                "target_description": "cell respiration photosynthesis genetics ecology evolution",
            },
        )
        onboarding = service.resolve_curriculum(onboarding_id=onboarding.id, actor=self.user, expected_version=onboarding.version)
        candidate = service.candidates(onboarding_id=onboarding.id, actor=self.user)[0]
        resolver_candidate = CurriculumResolutionCandidate.objects.get(id=candidate["candidate_id"])

        self.assertEqual(resolver_candidate.eligibility, CandidateEligibility.ELIGIBLE)
        self.assertNotIn(
            resolver_candidate.match_classification,
            {MatchClassification.EXACT, MatchClassification.STRONG},
        )
        self.assertFalse(candidate["selectable"])
        intent_count = SelfStudyIntent.objects.count()
        subject_count = Subject.objects.count()

        with self.assertRaisesMessage(Exception, "Selected curriculum is not available for self-study"):
            service.select_candidate(
                onboarding_id=onboarding.id,
                actor=self.user,
                expected_version=onboarding.version,
                candidate_id=candidate["candidate_id"],
            )

        self.assertEqual(SelfStudyIntent.objects.count(), intent_count)
        self.assertEqual(Subject.objects.count(), subject_count)

    def test_stale_resolver_candidate_cannot_be_selected_after_reresolution(self):
        service = SelfStudyConversationalOnboardingService()
        onboarding = service.start(workspace_id=self.workspace.id, actor=self.user, idempotency_key="stale-candidate")
        onboarding = service.update_context(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            changes={
                "topic_query": "Biology",
                "study_intent": SelfStudyOnboardingIntent.EXAM,
                "qualification_query": "Cambridge International A Level",
            },
        )
        onboarding = service.resolve_curriculum(onboarding_id=onboarding.id, actor=self.user, expected_version=onboarding.version)
        stale_candidate_id = service.candidates(onboarding_id=onboarding.id, actor=self.user)[0]["candidate_id"]
        onboarding = service.update_context(
            onboarding_id=onboarding.id,
            actor=self.user,
            expected_version=onboarding.version,
            changes={"level_query": "A Level updated"},
        )
        onboarding = service.resolve_curriculum(onboarding_id=onboarding.id, actor=self.user, expected_version=onboarding.version)

        with self.assertRaisesMessage(Exception, "Selected curriculum was not offered"):
            service.select_candidate(
                onboarding_id=onboarding.id,
                actor=self.user,
                expected_version=onboarding.version,
                candidate_id=stale_candidate_id,
            )
