from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.academic.models import ContentConcept, ContentSection, Curriculum, CurriculumUnit, LearningResource, Subject
from apps.assessments.domain.models import (
    LearningEvidence,
    LearningEvidenceSourceType,
    LearningEvidenceType,
    MasteryDecision,
    MasteryDecisionValue,
)
from apps.learning_journeys.application.progression_policy import CompetencyProgressionPolicy
from apps.learning_journeys.application.progression_services import CompetencyProgressSnapshotService, CompetencyProgressionService
from apps.learning_journeys.domain.enums import (
    LearningCompetencyProgressState,
    LearningCompetencyUnlockState,
    LearningJourneyType,
)
from apps.learning_journeys.domain.models import LearningCompetencyProgress, LearningCompetencyProgressHistory, LearningJourney
from apps.self_study.curriculum_models import (
    CompositeCurriculumProposal,
    CurriculumAuthority,
    CurriculumReference,
    CurriculumResolutionAttempt,
    CurriculumVersion,
)
from apps.self_study.graph_models import (
    ConstructionMethod,
    CurriculumEdge,
    CurriculumGraph,
    CurriculumGraphVersion,
    CurriculumNode,
    EdgeType,
    GraphStatus,
    GraphVersionStatus,
    NodeType,
    RequirementType,
)
from apps.self_study.models import EffectiveLearningPolicySnapshot, SelfStudyIntent
from apps.users.models import Institution, User


class CompetencyProgressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.learner = User.objects.create_user(email="progress@example.com", password="test")
        self.other = User.objects.create_user(email="other-progress@example.com", password="test")
        self.institution = Institution.objects.create(name="Progress Tenant", slug="progress-tenant", institution_type="individual")
        self.subject = Subject.objects.create(institution=self.institution, code="BIO", name="Biology")
        self.content_concept = self._content_concept()
        self.curriculum_version = self._curriculum_version()
        self.graph_version = self._graph_version()
        self.cell_structure = self._node("cell-structure", "Cell structure", 1)
        self.cell_function = self._node("cell-function", "Cell function", 2)
        CurriculumEdge.objects.create(
            graph_version=self.graph_version,
            stable_key="cell-function-requires-cell-structure",
            edge_type=EdgeType.REQUIRES,
            source_node=self.cell_function,
            target_node=self.cell_structure,
            ordinal=1,
            requirement=RequirementType.REQUIRED,
            source_curriculum_version=self.curriculum_version,
        )
        self.journey = LearningJourney.objects.create(
            learner=self.learner,
            institution=self.institution,
            journey_type=LearningJourneyType.SELF_STUDY,
        )

    def test_mastery_decision_demonstrates_competency_and_records_history(self):
        evidence = self._evidence(LearningEvidenceType.CORRECT_RESPONSE, score=1.0, confidence=0.92)
        mastery = self._mastery(MasteryDecisionValue.MASTERED, evidence=evidence)

        progress = CompetencyProgressionService().progress_from_mastery(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            mastery_decision_id=mastery.id,
            actor=self.learner,
        )

        self.assertEqual(progress.state, LearningCompetencyProgressState.DEMONSTRATED)
        self.assertEqual(progress.unlock_state, LearningCompetencyUnlockState.COMPLETED)
        self.assertEqual(progress.latest_mastery_decision_id, mastery.id)
        self.assertEqual(progress.latest_evidence_summary["evidence_count"], 1)
        self.assertEqual(progress.history.count(), 1)

    def test_progression_is_idempotent_for_unchanged_mastery(self):
        mastery = self._mastery(MasteryDecisionValue.MASTERED, evidence=self._evidence(LearningEvidenceType.CORRECT_RESPONSE))

        service = CompetencyProgressionService()
        service.progress_from_mastery(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            mastery_decision_id=mastery.id,
            actor=self.learner,
        )
        service.progress_from_mastery(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            mastery_decision_id=mastery.id,
            actor=self.learner,
        )

        self.assertEqual(LearningCompetencyProgress.objects.count(), 2)
        demonstrated = LearningCompetencyProgress.objects.get(journey=self.journey, competency=self.cell_structure)
        self.assertEqual(demonstrated.history.count(), 1)

    def test_unlock_policy_uses_governed_prerequisite_edges(self):
        mastery = self._mastery(MasteryDecisionValue.MASTERED, evidence=self._evidence(LearningEvidenceType.CORRECT_RESPONSE))

        CompetencyProgressionService().progress_from_mastery(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            mastery_decision_id=mastery.id,
            actor=self.learner,
        )

        downstream = LearningCompetencyProgress.objects.get(journey=self.journey, competency=self.cell_function)
        self.assertEqual(downstream.state, LearningCompetencyProgressState.NOT_STARTED)
        self.assertEqual(downstream.unlock_state, LearningCompetencyUnlockState.AVAILABLE)

    def test_review_and_regression_are_mastery_driven_not_activity_driven(self):
        service = CompetencyProgressionService()
        mastered = self._mastery(MasteryDecisionValue.MASTERED, evidence=self._evidence(LearningEvidenceType.CORRECT_RESPONSE))
        service.progress_from_mastery(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            mastery_decision_id=mastered.id,
            actor=self.learner,
        )
        review = self._mastery(MasteryDecisionValue.NEEDS_REVIEW, evidence=self._evidence(LearningEvidenceType.PARTIAL_UNDERSTANDING))
        progress = service.progress_from_mastery(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            mastery_decision_id=review.id,
            actor=self.learner,
        )
        self.assertEqual(progress.state, LearningCompetencyProgressState.REVIEW_REQUIRED)

        regression = self._mastery(MasteryDecisionValue.NOT_MASTERED, evidence=self._evidence(LearningEvidenceType.MISCONCEPTION))
        progress = service.progress_from_mastery(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            mastery_decision_id=regression.id,
            actor=self.learner,
        )
        self.assertEqual(progress.state, LearningCompetencyProgressState.REGRESSED)

    def test_invalid_transition_is_rejected_by_policy(self):
        with self.assertRaises(ValidationError):
            CompetencyProgressionPolicy().validate(
                LearningCompetencyProgressState.SUPERSEDED,
                LearningCompetencyProgressState.DEMONSTRATED,
            )

    def test_supersession_is_durable_and_history_is_append_only(self):
        mastery = self._mastery(MasteryDecisionValue.MASTERED, evidence=self._evidence(LearningEvidenceType.CORRECT_RESPONSE))
        progress = CompetencyProgressionService().progress_from_mastery(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            mastery_decision_id=mastery.id,
            actor=self.learner,
        )

        progress = CompetencyProgressionService().supersede_competency(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            successor_competency_id=self.cell_function.id,
            actor=self.learner,
        )

        self.assertEqual(progress.state, LearningCompetencyProgressState.SUPERSEDED)
        self.assertEqual(progress.unlock_state, LearningCompetencyUnlockState.SUPERSEDED)
        self.assertEqual(progress.superseded_by_id, self.cell_function.id)
        history = LearningCompetencyProgressHistory.objects.filter(progress=progress).latest("created_at")
        history.reason = "UNCHANGED"
        with self.assertRaises(ValidationError):
            history.save()

    def test_snapshot_and_read_api_expose_competency_context(self):
        mastery = self._mastery(MasteryDecisionValue.MASTERED, evidence=self._evidence(LearningEvidenceType.CORRECT_RESPONSE))
        CompetencyProgressionService().progress_from_mastery(
            journey_id=self.journey.id,
            competency_id=self.cell_structure.id,
            mastery_decision_id=mastery.id,
            actor=self.learner,
        )

        snapshot = CompetencyProgressSnapshotService().execute(journey_id=self.journey.id, actor=self.learner)
        self.assertEqual(snapshot["completed_competencies"][0]["title"], "Cell structure")
        self.assertEqual(snapshot["next_available_competencies"][0]["title"], "Cell function")

        self.client.force_authenticate(self.learner)
        response = self.client.get(f"/api/learning-journeys/{self.journey.id}/snapshot/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["progress"]["completed_competency_count"], 1)
        self.assertIn("competency_context", response.data["journey"])

        self.client.force_authenticate(self.other)
        forbidden = self.client.get(f"/api/learning-journeys/{self.journey.id}/competencies/")
        self.assertEqual(forbidden.status_code, 403)

    def _content_concept(self):
        curriculum = Curriculum.objects.create(subject=self.subject, institution=self.institution, name="Biology", version="2026")
        unit = CurriculumUnit.objects.create(curriculum=curriculum, title="Cells", sequence_number=1)
        resource = LearningResource.objects.create(
            institution=self.institution,
            subject=self.subject,
            curriculum=curriculum,
            curriculum_unit=unit,
            title="Cells resource",
            status=LearningResource.Status.ACTIVE,
        )
        section = ContentSection.objects.create(learning_resource=resource, title="Cell basics", sequence_number=1)
        return ContentConcept.objects.create(content_section=section, title="Cell structure", sequence_number=1)

    def _curriculum_version(self):
        authority = CurriculumAuthority.objects.create(
            canonical_key="progress-authority",
            name="Progress Authority",
            authority_type="NATIONAL_CURRICULUM_BODY",
            verification_status="VERIFIED",
            verified_at=timezone.now(),
            verified_by=self.learner,
        )
        reference = CurriculumReference.objects.create(
            canonical_key="progress-biology",
            title="Progress Biology",
            subject_area="Biology",
            authority=authority,
            source_classification="NATIONAL_OR_REGIONAL",
            jurisdiction="LS",
            language="en",
        )
        return CurriculumVersion.objects.create(
            curriculum_reference=reference,
            version_label="2026",
            status="ACTIVE",
            canonical_source_uri="https://example.test/progress-biology",
            content_hash="sha256:progress",
            licence_identifier="official",
            provenance_status="COMPLETE",
            language="en",
            jurisdiction="LS",
            created_by=self.learner,
        )

    def _graph_version(self):
        policy_snapshot = EffectiveLearningPolicySnapshot.objects.create(
            policy_version=1,
            source_policy_ids=["platform"],
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
            goal_statement="Learn cell biology",
            preferred_language="en",
            jurisdiction="LS",
            policy_acknowledged_at=timezone.now(),
            status="ACTIVE",
            effective_policy_snapshot=policy_snapshot,
            created_by=self.learner,
            version=2,
        )
        attempt = CurriculumResolutionAttempt.objects.create(
            intent=intent,
            intent_version=intent.version,
            policy_snapshot=policy_snapshot,
            requested_by=self.learner,
            status="SELECTED",
            goal_snapshot=intent.goal_statement,
            preferred_language="en",
            requested_depth="CONCEPT",
            algorithm_version="test",
            idempotency_key="progression",
        )
        proposal = CompositeCurriculumProposal.objects.create(attempt=attempt)
        graph = CurriculumGraph.objects.create(
            tenant=self.institution,
            intent=intent,
            composite_proposal=proposal,
            status=GraphStatus.DRAFT,
        )
        return CurriculumGraphVersion.objects.create(
            graph=graph,
            version_number=1,
            status=GraphVersionStatus.DRAFT,
            source_selection_fingerprint="test-source",
            builder_algorithm_version="test",
            validation_algorithm_version="test",
            stable_key_algorithm_version="test",
            source_language="en",
            construction_method=ConstructionMethod.CURATED_AUTHORING,
            created_by=self.learner,
        )

    def _node(self, stable_key: str, title: str, ordinal: int):
        return CurriculumNode.objects.create(
            graph_version=self.graph_version,
            stable_key=stable_key,
            node_type=NodeType.COMPETENCY,
            title=title,
            ordinal=ordinal,
            source_curriculum_version=self.curriculum_version,
            authority_namespace="progress.fixture",
        )

    def _evidence(self, evidence_type: str, *, score: float | None = 0.8, confidence: float = 0.8):
        return LearningEvidence.objects.create(
            learner=self.learner,
            content_concept=self.content_concept,
            source_type=LearningEvidenceSourceType.ASSESSMENT_RESULT,
            source_id="fixture-result",
            evidence_type=evidence_type,
            score=score,
            confidence=confidence,
            metadata={"fixture": "competency progression"},
        )

    def _mastery(self, decision: str, *, evidence: LearningEvidence):
        return MasteryDecision.objects.create(
            learner=self.learner,
            content_concept=self.content_concept,
            decision=decision,
            confidence=evidence.confidence,
            evidence_count=1,
            rationale="Fixture mastery decision.",
            metadata={"evidence_ids": [str(evidence.id)]},
        )
