from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academic.models import ContentConcept, ContentSection, Curriculum, CurriculumUnit, LearningResource, Subject
from apps.assessments.domain.models import LearningEvidence, LearningEvidenceSourceType, LearningEvidenceType, MasteryDecision, MasteryDecisionValue
from apps.learning_journeys.application.authority import InstitutionAuthorityProvider, JourneyAuthorityResolver
from apps.learning_journeys.application.institutional_services import (
    InstitutionalCompletionService,
    InstitutionalInterventionService,
    InstitutionalJourneyVisibilityPolicy,
    InstitutionalLearningPlanEvolutionService,
)
from apps.learning_journeys.application.progression_services import CompetencyProgressionService
from apps.learning_journeys.application.queries import GetLearningJourneyService
from apps.learning_journeys.application.services import CreateLearningJourneyService
from apps.learning_journeys.domain.enums import (
    InstitutionalAssignmentState,
    InstitutionalCompletionState,
    InstitutionalInterventionReason,
    InstitutionalInterventionStatus,
    JourneyAuthorityProviderType,
    LearningCompetencyProgressState,
    LearningJourneySourceType,
    LearningJourneyStatus,
    LearningJourneyType,
)
from apps.learning_journeys.domain.models import (
    InstitutionalInterventionRecommendation,
    InstitutionalLearningAssignment,
    LearningCompetencyProgress,
    LearningJourneySourceBinding,
)
from apps.self_study.curriculum_models import (
    CompositeCurriculumProposal,
    CurriculumAuthority,
    CurriculumReference,
    CurriculumResolutionAttempt,
    CurriculumVersion,
)
from apps.self_study.graph_models import ConstructionMethod, CurriculumGraph, CurriculumGraphVersion, CurriculumNode, GraphStatus, GraphVersionStatus, NodeType
from apps.self_study.models import EffectiveLearningPolicySnapshot, SelfStudyIntent
from apps.users.models import Institution, InstitutionMembership, InstitutionRole, User


class InstitutionalJourneyOrchestrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(email="institution-admin@example.com", password="test")
        self.teacher = User.objects.create_user(email="teacher@example.com", password="test")
        self.learner = User.objects.create_user(email="institution-learner@example.com", password="test")
        self.other = User.objects.create_user(email="outside@example.com", password="test")
        self.institution = Institution.objects.create(name="Demo School", slug="demo-school-pi8b4", institution_type="school")
        self.other_institution = Institution.objects.create(name="Other School", slug="other-school-pi8b4", institution_type="school")
        InstitutionMembership.objects.create(user=self.admin, institution=self.institution, role=InstitutionRole.ADMINISTRATOR)
        InstitutionMembership.objects.create(user=self.teacher, institution=self.institution, role=InstitutionRole.TEACHER)
        self.membership = InstitutionMembership.objects.create(user=self.learner, institution=self.institution, role=InstitutionRole.STUDENT)
        InstitutionMembership.objects.create(user=self.other, institution=self.other_institution, role=InstitutionRole.ADMINISTRATOR)
        self.subject = Subject.objects.create(institution=self.institution, code="BIO", name="Biology")
        self.content_concept = self._content_concept()
        self.curriculum_reference, self.curriculum_version = self._curriculum_version()
        self.graph_version = self._graph_version()
        self.competency = CurriculumNode.objects.create(
            graph_version=self.graph_version,
            stable_key="institutional-cell-structure",
            node_type=NodeType.COMPETENCY,
            title="Cell structure",
            ordinal=1,
            source_curriculum_version=self.curriculum_version,
            authority_namespace="institution.fixture",
        )

    def test_institutional_assignment_projects_authority_into_shared_journey(self):
        journey = CreateLearningJourneyService().for_institutional_membership(
            learner_id=self.learner.id,
            institution_id=self.institution.id,
            actor=self.admin,
            subject_id=self.subject.id,
            curriculum_reference_id=self.curriculum_reference.id,
            programme_label="A Level Biology",
            course_label="Cell Biology",
            required_competency_ids=[self.competency.id],
            delivery_objectives={"pace": "weekly"},
        )

        assignment = InstitutionalLearningAssignment.objects.get(journey=journey)
        binding = LearningJourneySourceBinding.objects.get(journey=journey)
        payload = GetLearningJourneyService().execute(journey_id=journey.id, actor=self.teacher)

        self.assertEqual(assignment.assignment_state, InstitutionalAssignmentState.ACTIVE)
        self.assertEqual(binding.source_type, LearningJourneySourceType.INSTITUTIONAL_ASSIGNMENT)
        self.assertEqual(payload["journey_type"], LearningJourneyType.INSTITUTIONAL)
        self.assertEqual(payload["state"], LearningJourneyStatus.LEARNING_ACTIVE)
        self.assertEqual(payload["authority"]["type"], "INSTITUTION")
        self.assertEqual(payload["institutional_state"]["assignment"], InstitutionalAssignmentState.ACTIVE)
        self.assertEqual(payload["subject"]["id"], str(self.subject.id))

    def test_authority_provider_and_visibility_enforce_institution_boundary(self):
        journey = CreateLearningJourneyService().for_institutional_membership(
            learner_id=self.learner.id,
            institution_id=self.institution.id,
            actor=self.admin,
            subject_id=self.subject.id,
            curriculum_reference_id=self.curriculum_reference.id,
        )
        assignment = InstitutionalLearningAssignment.objects.get(journey=journey)

        provider = JourneyAuthorityResolver().provider_for(journey=journey)
        self.assertIsInstance(provider, InstitutionAuthorityProvider)
        self.assertEqual(provider.authority_for(journey=journey).provider, JourneyAuthorityProviderType.INSTITUTION)
        self.assertTrue(provider.can_read(actor=self.teacher, journey=journey))
        self.assertFalse(provider.can_read(actor=self.other, journey=journey))
        self.assertTrue(InstitutionalJourneyVisibilityPolicy().can_view_assignment(actor=self.teacher, assignment=assignment))
        self.assertFalse(InstitutionalJourneyVisibilityPolicy().can_view_assignment(actor=self.other, assignment=assignment))

    def test_institutional_api_exposes_read_safe_projection_and_tenant_isolation(self):
        journey = CreateLearningJourneyService().for_institutional_membership(
            learner_id=self.learner.id,
            institution_id=self.institution.id,
            actor=self.admin,
            subject_id=self.subject.id,
            curriculum_reference_id=self.curriculum_reference.id,
        )

        self.client.force_authenticate(self.teacher)
        listed = self.client.get("/api/institutional-learning-journeys/")
        detail = self.client.get(f"/api/institutional-learning-journeys/{journey.id}/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("mentor_memory", detail.data)
        self.assertEqual(detail.data["journey"]["authority"]["type"], "INSTITUTION")

        self.client.force_authenticate(self.other)
        forbidden = self.client.get(f"/api/institutional-learning-journeys/{journey.id}/")
        self.assertEqual(forbidden.status_code, 403)

    def test_competency_progression_generates_intervention_without_changing_mastery(self):
        journey = CreateLearningJourneyService().for_institutional_membership(
            learner_id=self.learner.id,
            institution_id=self.institution.id,
            actor=self.admin,
            subject_id=self.subject.id,
            curriculum_reference_id=self.curriculum_reference.id,
            required_competency_ids=[self.competency.id],
        )
        mastery = self._mastery(MasteryDecisionValue.NEEDS_REVIEW, evidence_type=LearningEvidenceType.PARTIAL_UNDERSTANDING)

        progress = CompetencyProgressionService().progress_from_mastery(
            journey_id=journey.id,
            competency_id=self.competency.id,
            mastery_decision_id=mastery.id,
            actor=self.learner,
        )

        assignment = InstitutionalLearningAssignment.objects.get(journey=journey)
        recommendation = InstitutionalInterventionRecommendation.objects.get(journey=journey)
        self.assertEqual(progress.state, LearningCompetencyProgressState.REVIEW_REQUIRED)
        self.assertEqual(recommendation.reason, InstitutionalInterventionReason.REPEATED_REVIEW_REQUIRED)
        self.assertEqual(assignment.assignment_state, InstitutionalAssignmentState.INTERVENTION_REQUIRED)
        self.assertEqual(MasteryDecision.objects.get(id=mastery.id).decision, MasteryDecisionValue.NEEDS_REVIEW)

        resolved = InstitutionalInterventionService().resolve(recommendation_id=recommendation.id, actor=self.admin)
        self.assertEqual(resolved.status, InstitutionalInterventionStatus.RESOLVED)

    def test_completion_readiness_reuses_competency_progression(self):
        journey = CreateLearningJourneyService().for_institutional_membership(
            learner_id=self.learner.id,
            institution_id=self.institution.id,
            actor=self.admin,
            subject_id=self.subject.id,
            curriculum_reference_id=self.curriculum_reference.id,
            required_competency_ids=[self.competency.id],
        )
        blocked = InstitutionalCompletionService().evaluate(journey_id=journey.id, actor=self.teacher)
        self.assertFalse(blocked["ready"])

        mastery = self._mastery(MasteryDecisionValue.MASTERED, evidence_type=LearningEvidenceType.CORRECT_RESPONSE)
        CompetencyProgressionService().progress_from_mastery(
            journey_id=journey.id,
            competency_id=self.competency.id,
            mastery_decision_id=mastery.id,
            actor=self.learner,
        )
        ready = InstitutionalCompletionService().evaluate(journey_id=journey.id, actor=self.teacher)
        self.assertTrue(ready["ready"])
        self.assertEqual(ready["completion_state"], InstitutionalCompletionState.READY)

        completed = InstitutionalCompletionService().complete(journey_id=journey.id, actor=self.admin)
        self.assertEqual(completed["completion_state"], InstitutionalCompletionState.COMPLETED)

    def test_learning_plan_projection_keeps_institutional_objectives_separate_from_adaptation(self):
        journey = CreateLearningJourneyService().for_institutional_membership(
            learner_id=self.learner.id,
            institution_id=self.institution.id,
            actor=self.admin,
            subject_id=self.subject.id,
            curriculum_reference_id=self.curriculum_reference.id,
            required_competency_ids=[self.competency.id],
            delivery_objectives={"deadline": "term-end"},
        )
        assignment = InstitutionalLearningAssignment.objects.get(journey=journey)

        projection = InstitutionalLearningPlanEvolutionService().request_projection(assignment=assignment)

        self.assertEqual(projection["adaptation_boundary"], "INSTITUTIONAL_AUTHORITY")
        self.assertEqual(projection["delivery_objectives"]["deadline"], "term-end")
        self.assertEqual(projection["required_competency_ids"], [str(self.competency.id)])

    def _content_concept(self):
        curriculum = Curriculum.objects.create(subject=self.subject, institution=self.institution, name="Biology", version="2026")
        unit = CurriculumUnit.objects.create(curriculum=curriculum, title="Cells", sequence_number=1)
        resource = LearningResource.objects.create(institution=self.institution, subject=self.subject, curriculum=curriculum, curriculum_unit=unit, title="Cells")
        section = ContentSection.objects.create(learning_resource=resource, title="Cell basics", sequence_number=1)
        return ContentConcept.objects.create(content_section=section, title="Cell structure", sequence_number=1)

    def _curriculum_version(self):
        authority = CurriculumAuthority.objects.create(
            canonical_key="institutional-authority",
            name="Institutional Authority",
            authority_type="NATIONAL_CURRICULUM_BODY",
            verification_status="VERIFIED",
            verified_at=timezone.now(),
            verified_by=self.admin,
        )
        reference = CurriculumReference.objects.create(
            canonical_key="institutional-biology",
            title="Institutional Biology",
            subject_area="Biology",
            authority=authority,
            source_classification="NATIONAL_OR_REGIONAL",
            jurisdiction="LS",
            language="en",
            tenant=self.institution,
        )
        version = CurriculumVersion.objects.create(
            curriculum_reference=reference,
            version_label="2026",
            status="ACTIVE",
            canonical_source_uri="https://example.test/institutional-biology",
            content_hash="sha256:institutional",
            licence_identifier="official",
            provenance_status="COMPLETE",
            language="en",
            jurisdiction="LS",
            created_by=self.admin,
        )
        return reference, version

    def _graph_version(self):
        snapshot = EffectiveLearningPolicySnapshot.objects.create(
            policy_version=1,
            source_policy_ids=["institutional"],
            allowed_provider_ids=["registry"],
            allowed_source_categories=["OPEN_EDUCATIONAL_RESOURCE"],
            allowed_licence_categories=["official"],
            allowed_mime_types=["application/pdf"],
            allowed_languages=["en"],
            maximum_resource_count=10,
            maximum_single_file_bytes=10_000,
            maximum_total_bytes=100_000,
            maximum_cost=Decimal("0"),
        )
        intent = SelfStudyIntent.objects.create(
            learner=self.learner,
            tenant=self.institution,
            subject=self.subject,
            mode="SELF_STUDY",
            goal_statement="Institutional biology",
            preferred_language="en",
            policy_acknowledged_at=timezone.now(),
            status="ACTIVE",
            effective_policy_snapshot=snapshot,
            created_by=self.learner,
            version=2,
        )
        attempt = CurriculumResolutionAttempt.objects.create(
            intent=intent,
            intent_version=intent.version,
            policy_snapshot=snapshot,
            requested_by=self.learner,
            status="SELECTED",
            goal_snapshot=intent.goal_statement,
            preferred_language="en",
            requested_depth="CONCEPT",
            algorithm_version="test",
            idempotency_key="institutional",
        )
        proposal = CompositeCurriculumProposal.objects.create(attempt=attempt)
        graph = CurriculumGraph.objects.create(tenant=self.institution, intent=intent, composite_proposal=proposal, status=GraphStatus.DRAFT)
        return CurriculumGraphVersion.objects.create(
            graph=graph,
            version_number=1,
            status=GraphVersionStatus.DRAFT,
            source_selection_fingerprint="institutional",
            builder_algorithm_version="test",
            validation_algorithm_version="test",
            stable_key_algorithm_version="test",
            source_language="en",
            construction_method=ConstructionMethod.CURATED_AUTHORING,
            created_by=self.admin,
        )

    def _mastery(self, decision: str, *, evidence_type: str):
        evidence = LearningEvidence.objects.create(
            learner=self.learner,
            content_concept=self.content_concept,
            source_type=LearningEvidenceSourceType.ASSESSMENT_RESULT,
            source_id="institutional-result",
            evidence_type=evidence_type,
            score=1.0 if decision == MasteryDecisionValue.MASTERED else 0.4,
            confidence=0.9,
            metadata={"fixture": "institutional journey"},
        )
        return MasteryDecision.objects.create(
            learner=self.learner,
            content_concept=self.content_concept,
            decision=decision,
            confidence=evidence.confidence,
            evidence_count=1,
            rationale="Fixture institutional mastery decision.",
            metadata={"evidence_ids": [str(evidence.id)]},
        )
