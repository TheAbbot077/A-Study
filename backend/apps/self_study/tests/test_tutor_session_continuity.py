from types import SimpleNamespace

from django.test import SimpleTestCase

from apps.self_study.application.experience_services import ExperienceBlockerCode
from apps.self_study.application.teaching_runtime_services import IntelligentTeachingExperienceService, TeachingRuntimeReadiness, TeachingStepType
from apps.self_study.application.tutor_session_services import TutorSessionOpeningReadiness, TutorSessionOpeningService
from apps.self_study.workspace_models import SelfStudyWorkspaceStatus


class TutorSessionContinuityProjectionTests(SimpleTestCase):
    def setUp(self):
        self.service = TutorSessionOpeningService()
        self.workspace = SimpleNamespace(
            id="workspace-1",
            display_name="A Level Biology",
            status=SelfStudyWorkspaceStatus.READY_TO_LEARN,
            intent_id="intent-1",
            intent=SimpleNamespace(goal_statement="Prepare calmly for A Level Biology", target_title="Biology"),
            active_bridge_plan_id="plan-1",
            active_bridge_plan=SimpleNamespace(status="ACTIVE"),
        )

    def test_ready_opening_uses_goal_destination_and_no_mastery_language(self):
        message = self.service._opening_message(
            readiness=TutorSessionOpeningReadiness.READY,
            workspace=self.workspace,
            goal="Prepare calmly for A Level Biology",
            destination={"title": "Cell structure"},
            previous_activity=None,
            blockers=[],
        )

        self.assertIn("Cell structure", message)
        self.assertIn("Prepare calmly for A Level Biology", message)
        self.assertNotIn("mastered", message.lower())
        self.assertNotIn("certified", message.lower())

    def test_blocked_opening_does_not_claim_teaching_can_continue(self):
        message = self.service._opening_message(
            readiness=TutorSessionOpeningReadiness.BLOCKED,
            workspace=self.workspace,
            goal="Prepare calmly for A Level Biology",
            destination=None,
            previous_activity=None,
            blockers=[ExperienceBlockerCode.PLAN_STALE],
        )

        self.assertIn("resolved before I can continue", message)
        self.assertNotIn("raw diagnostic", message.lower())

    def test_mentor_items_strip_internal_observation_keys(self):
        identity_items, memory_items = self.service._mentor_items(
            {
                "items": [
                    {"key": "activity_11111111-1111-4111-8111-111111111111", "label": "Learning session", "value": "Worked on cells.", "source": "Governed session"},
                    {"key": "declared_goal", "label": "Study goal", "value": "Exam preparation", "source": "Chosen by you"},
                ]
            }
        )

        self.assertEqual(identity_items, [{"label": "Study goal", "value": "Exam preparation", "source": "Chosen by you"}])
        self.assertEqual(memory_items, [{"label": "Learning session", "value": "Worked on cells.", "source": "Governed session"}])
        self.assertNotIn("11111111", str(identity_items + memory_items))

    def test_readiness_fails_closed_without_governed_destination(self):
        readiness = self.service._readiness(workspace=self.workspace, blockers=[], destination=None)

        self.assertEqual(readiness, TutorSessionOpeningReadiness.BLOCKED)


class IntelligentTeachingRuntimeContractTests(SimpleTestCase):
    def setUp(self):
        self.service = IntelligentTeachingExperienceService()
        self.opening = {
            "workspace_id": "workspace-1",
            "readiness": TutorSessionOpeningReadiness.READY,
            "opening_message": "Welcome back. Today we're focusing on Cell structure.",
            "workspace_summary": {"display_name": "Biology", "status": "READY_TO_LEARN", "goal": "Prepare for Biology", "target_title": "Biology"},
            "current_destination": {
                "title": "Cell structure",
                "node_type": "CONCEPT",
                "status": "ACTIVE",
                "coverage_state": "COVERED",
                "material_status": "FEASIBLE",
            },
            "previous_activity_summary": None,
            "blocker_codes": [],
            "warning_codes": [],
        }
        self.studio = {"blocker_codes": [], "teaching_session_id": "session-1"}

    def test_runtime_creates_ordered_steps_from_governed_destination(self):
        runtime = self.service._runtime(opening=self.opening, studio=self.studio)

        self.assertEqual(runtime["readiness"], TeachingRuntimeReadiness.READY)
        self.assertEqual([step["type"] for step in runtime["steps"]][:4], [
            TeachingStepType.OPENING,
            TeachingStepType.RECAP,
            TeachingStepType.TEACH,
            TeachingStepType.EXAMPLE,
        ])
        self.assertIn(TeachingStepType.CONCEPT_CHECK, [step["type"] for step in runtime["steps"]])

    def test_runtime_blocks_without_destination(self):
        opening = {**self.opening, "readiness": TutorSessionOpeningReadiness.BLOCKED, "current_destination": None}

        runtime = self.service._runtime(opening=opening, studio=self.studio)

        self.assertEqual(runtime["readiness"], TeachingRuntimeReadiness.BLOCKED)
        self.assertTrue(all(step["status"] == "BLOCKED" for step in runtime["steps"]))

    def test_explanation_copy_preserves_authority_boundary(self):
        explanation = self.service._mode_copy(mode="ANALOGY", title="Cell structure")

        self.assertIn("teaching aid", explanation)
        self.assertNotIn("master", explanation.lower())

    def test_response_receipt_does_not_award_mastery_or_write_identity(self):
        feedback = self.service._feedback("READY_FOR_CONCEPT_CHECK")
        receipt_id = self.service._receipt_id(workspace_id="workspace-1", response_text="Cells have parts.", interaction_type="SOCRATIC_PROMPT")

        self.assertTrue(receipt_id.startswith("receipt-"))
        self.assertIn("without treating this as mastery", feedback)

    def test_whiteboard_artifact_is_structured_not_raw_svg(self):
        artifact = self.service._whiteboard("Cell structure")

        self.assertEqual(artifact["type"], "CONCEPT_MAP")
        self.assertIn("nodes", artifact)
        self.assertIn("edges", artifact)
        self.assertNotIn("<svg", str(artifact).lower())
