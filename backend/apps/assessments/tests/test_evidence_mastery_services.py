from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.db import models
from django.test import SimpleTestCase

from apps.assessments.domain.models import (
    LearningEvidence,
    LearningEvidenceSourceType,
    LearningEvidenceType,
    MasteryDecision,
    MasteryDecisionValue,
    MasteryProfile,
)
from apps.assessments.services import EvidenceService, MasteryService
from apps.core.events import default_event_registry


class DummyContentConcept:
    id = "concept-1"


class DummyLearner:
    id = "learner-1"


class EvidenceServiceTests(SimpleTestCase):
    def test_recording_learning_evidence(self):
        publisher = Mock()
        service = EvidenceService(event_publisher=publisher)
        learner = DummyLearner()
        concept = DummyContentConcept()

        with patch("apps.assessments.services.evidence_service.LearningEvidence.objects") as evidence_objects:
            fake_evidence = Mock(spec=LearningEvidence)
            fake_evidence.id = "evidence-1"
            fake_evidence.source_type = LearningEvidenceSourceType.ASSESSMENT_ATTEMPT
            fake_evidence.source_id = "attempt-1"
            fake_evidence.evidence_type = LearningEvidenceType.CORRECT_RESPONSE
            fake_evidence.confidence = 0.9
            evidence_objects.create.return_value = fake_evidence

            evidence = service.record_evidence(
                learner=learner,
                content_concept=concept,
                source_type=LearningEvidenceSourceType.ASSESSMENT_ATTEMPT,
                source_id="attempt-1",
                evidence_type=LearningEvidenceType.CORRECT_RESPONSE,
                score=0.95,
                confidence=0.9,
            )

        self.assertIs(evidence, fake_evidence)
        evidence_objects.create.assert_called_once_with(
            learner=learner,
            content_concept=concept,
            source_type=LearningEvidenceSourceType.ASSESSMENT_ATTEMPT,
            source_id="attempt-1",
            evidence_type=LearningEvidenceType.CORRECT_RESPONSE,
            score=0.95,
            confidence=0.9,
            metadata={},
        )
        event = publisher.publish.call_args.args[0]
        self.assertEqual(event.event_name, "assessment.learning_evidence_recorded")

    def test_listing_evidence_by_learner(self):
        service = EvidenceService(event_publisher=Mock())
        learner = DummyLearner()
        expected = [Mock(spec=LearningEvidence)]

        with patch("apps.assessments.services.evidence_service.LearningEvidence.objects") as evidence_objects:
            evidence_objects.filter.return_value.order_by.return_value = expected
            evidence = service.list_evidence_for_learner(learner)

        self.assertEqual(evidence, expected)
        evidence_objects.filter.assert_called_once_with(learner=learner)
        evidence_objects.filter.return_value.order_by.assert_called_once_with("-created_at")

    def test_listing_evidence_by_concept(self):
        service = EvidenceService(event_publisher=Mock())
        concept = DummyContentConcept()
        expected = [Mock(spec=LearningEvidence)]

        with patch("apps.assessments.services.evidence_service.LearningEvidence.objects") as evidence_objects:
            evidence_objects.filter.return_value.order_by.return_value = expected
            evidence = service.list_evidence_for_concept(concept)

        self.assertEqual(evidence, expected)
        evidence_objects.filter.assert_called_once_with(content_concept=concept)
        evidence_objects.filter.return_value.order_by.assert_called_once_with("-created_at")

    def test_listing_evidence_by_learner_and_concept(self):
        service = EvidenceService(event_publisher=Mock())
        learner = DummyLearner()
        concept = DummyContentConcept()
        expected = [Mock(spec=LearningEvidence)]

        with patch("apps.assessments.services.evidence_service.LearningEvidence.objects") as evidence_objects:
            evidence_objects.filter.return_value.order_by.return_value = expected
            evidence = service.list_evidence_for_learner_concept(learner, concept)

        self.assertEqual(evidence, expected)
        evidence_objects.filter.assert_called_once_with(learner=learner, content_concept=concept)
        evidence_objects.filter.return_value.order_by.assert_called_once_with("-created_at")

    def test_confidence_bounds(self):
        service = EvidenceService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.record_evidence(
                DummyLearner(),
                DummyContentConcept(),
                LearningEvidenceSourceType.SYSTEM,
                "source-1",
                LearningEvidenceType.OTHER,
                confidence=1.1,
            )

    def test_score_bounds(self):
        service = EvidenceService(event_publisher=Mock())

        with self.assertRaises(ValueError):
            service.record_evidence(
                DummyLearner(),
                DummyContentConcept(),
                LearningEvidenceSourceType.SYSTEM,
                "source-1",
                LearningEvidenceType.OTHER,
                score=-0.1,
                confidence=0.5,
            )


class MasteryServiceTests(SimpleTestCase):
    def test_mastery_decision_with_no_evidence(self):
        service, publisher, evidence_service = self._service_with_evidence([])

        with self._patched_mastery_storage():
            decision = service.evaluate_mastery(DummyLearner(), DummyContentConcept())

        self.assertEqual(decision.decision, MasteryDecisionValue.NOT_ENOUGH_EVIDENCE)
        self.assertEqual(decision.confidence, 0.0)
        self.assertEqual(decision.evidence_count, 0)
        evidence_service.list_evidence_for_learner_concept.assert_called_once()
        self.assertEqual(publisher.publish.call_args_list[0].args[0].event_name, "assessment.mastery_decision_created")
        self.assertEqual(publisher.publish.call_args_list[1].args[0].event_name, "assessment.mastery_profile_updated")

    def test_mastery_decision_with_positive_evidence(self):
        evidence = [
            self._evidence(LearningEvidenceType.CORRECT_RESPONSE, confidence=0.92, score=0.95),
            self._evidence(LearningEvidenceType.APPLIED_REASONING, confidence=0.84, score=0.8),
        ]
        service, _publisher, _evidence_service = self._service_with_evidence(evidence)

        with self._patched_mastery_storage():
            decision = service.evaluate_mastery(DummyLearner(), DummyContentConcept())

        self.assertEqual(decision.decision, MasteryDecisionValue.MASTERED)
        self.assertEqual(decision.confidence, 0.92)
        self.assertEqual(decision.evidence_count, 2)

    def test_mastery_decision_with_misconception_evidence(self):
        evidence = [self._evidence(LearningEvidenceType.MISCONCEPTION, confidence=0.88)]
        service, _publisher, _evidence_service = self._service_with_evidence(evidence)

        with self._patched_mastery_storage():
            decision = service.evaluate_mastery(DummyLearner(), DummyContentConcept())

        self.assertEqual(decision.decision, MasteryDecisionValue.NOT_MASTERED)
        self.assertEqual(decision.confidence, 0.88)

    def test_mastery_profile_creation(self):
        service = MasteryService(event_publisher=Mock())
        decision = self._decision(MasteryDecisionValue.MASTERED, confidence=0.9, evidence_count=1)

        with patch("apps.assessments.services.mastery_service.MasteryProfile.objects") as profile_objects:
            profile_objects.update_or_create.return_value = (self._profile(decision), True)
            profile = service.update_mastery_profile(decision, evidence=[self._evidence(LearningEvidenceType.CORRECT_RESPONSE)])

        self.assertEqual(profile.current_decision, MasteryDecisionValue.MASTERED)
        profile_objects.update_or_create.assert_called_once()

    def test_mastery_profile_update(self):
        service = MasteryService(event_publisher=Mock())
        decision = self._decision(MasteryDecisionValue.NEEDS_REVIEW, confidence=0.6, evidence_count=3)

        with patch("apps.assessments.services.mastery_service.MasteryProfile.objects") as profile_objects:
            profile_objects.update_or_create.return_value = (self._profile(decision), False)
            profile = service.update_mastery_profile(decision)

        self.assertEqual(profile.current_decision, MasteryDecisionValue.NEEDS_REVIEW)
        defaults = profile_objects.update_or_create.call_args.kwargs["defaults"]
        self.assertEqual(defaults["current_decision"], MasteryDecisionValue.NEEDS_REVIEW)

    def test_uniqueness_of_mastery_profile_per_learner_concept(self):
        constraints = {constraint.name: constraint for constraint in MasteryProfile._meta.constraints}

        self.assertIsInstance(constraints["unique_mastery_profile_learner_concept"], models.UniqueConstraint)

    def test_event_publication(self):
        expected_event_names = {
            "assessment.learning_evidence_recorded",
            "assessment.mastery_decision_created",
            "assessment.mastery_profile_updated",
        }

        self.assertTrue(expected_event_names.issubset(set(default_event_registry._subscribers)))

    def test_model_constraints(self):
        evidence_constraints = {constraint.name for constraint in LearningEvidence._meta.constraints}
        decision_constraints = {constraint.name for constraint in MasteryDecision._meta.constraints}
        profile_constraints = {constraint.name for constraint in MasteryProfile._meta.constraints}

        self.assertIn("learning_evidence_confidence_0_1", evidence_constraints)
        self.assertIn("learning_evidence_score_null_or_0_1", evidence_constraints)
        self.assertIn("mastery_decision_confidence_0_1", decision_constraints)
        self.assertIn("mastery_profile_confidence_0_1", profile_constraints)

    def _service_with_evidence(self, evidence):
        publisher = Mock()
        evidence_service = Mock(spec=EvidenceService)
        evidence_service.list_evidence_for_learner_concept.return_value = evidence
        service = MasteryService(event_publisher=publisher, evidence_service=evidence_service)
        return service, publisher, evidence_service

    def _patched_mastery_storage(self):
        return patch.multiple(
            "apps.assessments.services.mastery_service",
            MasteryDecision=Mock(objects=Mock(create=self._create_decision)),
            MasteryProfile=Mock(objects=Mock(update_or_create=self._update_profile)),
        )

    def _create_decision(self, **kwargs):
        return SimpleNamespace(id="decision-1", **kwargs)

    def _update_profile(self, learner, content_concept, defaults):
        return (
            SimpleNamespace(
                id="profile-1",
                learner=learner,
                content_concept=content_concept,
                current_decision=defaults["current_decision"],
                confidence=defaults["confidence"],
                evidence_count=defaults["evidence_count"],
                last_evidence_at=defaults["last_evidence_at"],
            ),
            True,
        )

    def _evidence(self, evidence_type, confidence=0.5, score=None):
        return SimpleNamespace(
            id=f"evidence-{evidence_type}",
            evidence_type=evidence_type,
            confidence=confidence,
            score=score,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    def _decision(self, decision, confidence, evidence_count):
        return SimpleNamespace(
            id="decision-1",
            learner=DummyLearner(),
            content_concept=DummyContentConcept(),
            decision=decision,
            confidence=confidence,
            evidence_count=evidence_count,
            rationale="Test decision",
            metadata={},
        )

    def _profile(self, decision):
        return SimpleNamespace(
            id="profile-1",
            learner=decision.learner,
            content_concept=decision.content_concept,
            current_decision=decision.decision,
            confidence=decision.confidence,
            evidence_count=decision.evidence_count,
        )
