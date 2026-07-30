from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.assessments.domain.models import MasteryDecisionValue
from apps.core.events.registry import default_event_registry
from apps.learning_journeys.application.backfill import LearningJourneyBackfillService
from apps.learning_journeys.application.operational import LearningJourneyOperationalViewService
from apps.learning_journeys.application.observability import LearningJourneyOperationalMetricsService
from apps.learning_journeys.application.progression_services import CompetencyProgressionService
from apps.learning_journeys.application.release_readiness import LearningJourneyReleaseReadinessService, REQUIRED_JOURNEY_EVENTS, REQUIRED_SELF_STUDY_TASKS
from apps.learning_journeys.domain.enums import (
    LearningCompetencyProgressState,
    LearningJourneyActionCode,
    LearningJourneyActionReceiptStatus,
    LearningJourneyIntegrityFindingCode,
    LearningJourneyIntegritySeverity,
    LearningJourneyOperationStatus,
)
from apps.learning_journeys.domain.models import (
    LearningCompetencyProgress,
    LearningJourney,
    LearningJourneyActionReceipt,
    LearningJourneyIntegrityFinding,
    LearningJourneyOperation,
)
from apps.learning_journeys.tests.scenarios import JourneyScenarioFactory


class LearningJourneyReleaseHardeningTests(TestCase):
    def setUp(self):
        self.factory = JourneyScenarioFactory(prefix="hardening")

    def test_release_readiness_reports_registered_events_and_state_counts(self):
        self.factory.self_study_journey()

        report = LearningJourneyReleaseReadinessService().report()

        self.assertIn(report["result"], {"READY", "READY_WITH_WARNINGS"})
        self.assertEqual(report["summary"]["journey_count"], 1)
        self.assertEqual(report["summary"]["journey_counts_by_type"]["SELF_STUDY"], 1)
        for event_name in REQUIRED_JOURNEY_EVENTS:
            self.assertIn(event_name, default_event_registry._subscribers)

    def test_release_readiness_detects_open_critical_integrity_findings(self):
        learner, institution, workspace, journey = self.factory.self_study_journey()
        LearningJourneyIntegrityFinding.objects.create(
            journey=journey,
            code=LearningJourneyIntegrityFindingCode.MISSING_SOURCE_BINDING,
            severity=LearningJourneyIntegritySeverity.CRITICAL,
            message="fixture",
        )

        report = LearningJourneyReleaseReadinessService().report()

        self.assertEqual(report["result"], "NOT_READY")
        self.assertEqual(report["blockers"][0]["code"], "OPEN_CRITICAL_INTEGRITY_FINDINGS")

    def test_backfill_self_study_workspaces_is_bounded_dry_run_and_explicit_execute(self):
        staff = self.factory.learner("staff@example.com")
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        learner = self.factory.learner("legacy@example.com")
        institution = self.factory.institution(name="Legacy Tenant", institution_type="individual")
        workspace = self.factory.workspace(learner=learner, institution=institution)

        dry_run = LearningJourneyBackfillService().backfill_self_study_workspaces(actor=staff, limit=1, dry_run=True)
        executed = LearningJourneyBackfillService().backfill_self_study_workspaces(actor=staff, limit=1, dry_run=False)

        self.assertEqual(dry_run["processed"], 1)
        self.assertEqual(dry_run["created"], 0)
        self.assertEqual(executed["created"], 1)
        self.assertTrue(LearningJourney.objects.filter(learner=learner, source_bindings__source_id=workspace.id).exists())

    def test_operational_reads_do_not_create_receipts_operations_or_progress(self):
        learner, institution, workspace, journey = self.factory.self_study_journey()
        before = (
            LearningJourneyActionReceipt.objects.count(),
            LearningJourneyOperation.objects.count(),
            LearningCompetencyProgress.objects.count(),
        )

        LearningJourneyOperationalViewService().execute(journey_id=journey.id, actor=learner)
        LearningJourneyOperationalViewService().execute(journey_id=journey.id, actor=learner)

        after = (
            LearningJourneyActionReceipt.objects.count(),
            LearningJourneyOperation.objects.count(),
            LearningCompetencyProgress.objects.count(),
        )
        self.assertEqual(before, after)

    def test_self_study_mastery_to_progression_to_operational_view_chain(self):
        learner, institution, workspace, journey = self.factory.self_study_journey()
        subject = self.factory.subject(institution=institution)
        concept = self.factory.content_concept(institution=institution, subject=subject)
        reference, version = self.factory.curriculum_reference(actor=learner, institution=institution)
        competency = self.factory.competency(learner=learner, institution=institution, subject=subject, curriculum_version=version)
        evidence, mastery = self.factory.mastery_decision(learner=learner, concept=concept, decision=MasteryDecisionValue.MASTERED)

        progress = CompetencyProgressionService().progress_from_mastery(
            journey_id=journey.id,
            competency_id=competency.id,
            mastery_decision_id=mastery.id,
            actor=learner,
        )
        view = LearningJourneyOperationalViewService().execute(journey_id=journey.id, actor=learner)

        self.assertEqual(progress.state, LearningCompetencyProgressState.DEMONSTRATED)
        self.assertEqual(progress.latest_mastery_decision_id, mastery.id)
        self.assertEqual(view["progress"]["competencies"]["demonstrated"], 1)
        self.assertEqual(view["operational_metadata"]["stale"], False)

    def test_institutional_visibility_hides_private_operational_internals_from_learner(self):
        admin, learner, institution, subject, reference, competency, journey = self.factory.institutional_journey()

        learner_view = LearningJourneyOperationalViewService().execute(journey_id=journey.id, actor=learner)
        admin_view = LearningJourneyOperationalViewService().execute(journey_id=journey.id, actor=admin)

        self.assertEqual(learner_view["view_policy"]["role"], "LEARNER")
        self.assertEqual(admin_view["view_policy"]["role"], "INSTITUTIONAL_ADMINISTRATOR")
        serialized = str(learner_view).lower()
        self.assertNotIn("mentor_memory", serialized)
        self.assertNotIn("raw diagnostic", serialized)
        self.assertNotIn("concept-check response", serialized)
        learner_action_codes = {action["code"] for action in learner_view["available_actions"]}
        self.assertNotIn("SYNCHRONIZE", learner_action_codes)

    def test_rejected_action_records_operation_without_private_payload_leakage(self):
        learner, institution, workspace, journey = self.factory.self_study_journey()
        receipt = LearningJourneyActionReceipt.objects.create(
            journey=journey,
            actor=learner,
            action_code=LearningJourneyActionCode.SELECT_CURRICULUM,
            idempotency_key="rejected",
            request_metadata={"payload_hash": "hash-only"},
        )
        receipt.mark_rejected(code="LEARNING_JOURNEY_ACTION_NOT_AVAILABLE", message="Journey action is not available.")
        receipt.save()
        operation = LearningJourneyOperation.objects.create(
            journey=journey,
            action_code=receipt.action_code,
            receipt=receipt,
            actor=learner,
            status=LearningJourneyOperationStatus.FAILED,
            progress_phase="rejected",
            completed_at=timezone.now(),
            result_reference={"receipt_id": str(receipt.id)},
        )

        self.assertEqual(receipt.status, LearningJourneyActionReceiptStatus.REJECTED)
        self.assertNotIn("candidate_id", receipt.request_metadata)
        self.assertEqual(operation.result_reference["receipt_id"], str(receipt.id))

    def test_task_registration_contract_is_identifier_only(self):
        from apps.self_study.infrastructure.celery import tasks as self_study_tasks

        registered = {getattr(value, "name", "") for value in vars(self_study_tasks).values()}
        for task_name in REQUIRED_SELF_STUDY_TASKS:
            self.assertIn(task_name, registered)

    def test_management_release_report_command_is_non_mutating(self):
        before = LearningJourney.objects.count()

        call_command("report_learning_journey_release_readiness")

        self.assertEqual(LearningJourney.objects.count(), before)

    def test_operational_metrics_use_bounded_labels(self):
        learner, institution, workspace, journey = self.factory.self_study_journey()
        LearningJourneyActionReceipt.objects.create(
            journey=journey,
            actor=learner,
            action_code=LearningJourneyActionCode.BEGIN_GOAL_DISCOVERY,
            status=LearningJourneyActionReceiptStatus.SUCCEEDED,
        )

        snapshot = LearningJourneyOperationalMetricsService().snapshot()

        self.assertIn("journey_action_total", snapshot)
        serialized = str(snapshot)
        self.assertNotIn(str(journey.id), serialized)
        self.assertNotIn(str(learner.id), serialized)
