from django.test import SimpleTestCase
from django.urls import reverse

from apps.self_study.application.experience_services import DiagnosticExperience, PlacementSummary


class SelfStudyDiagnosticPlanExperienceRouteTests(SimpleTestCase):
    def test_workspace_diagnostic_experience_routes_are_registered(self):
        workspace_id = "11111111-1111-4111-8111-111111111111"

        assert reverse("self-study-workspace-diagnostic-experience", args=[workspace_id]).endswith(
            f"/self-study/workspaces/{workspace_id}/diagnostic/experience/"
        )
        assert reverse("self-study-workspace-diagnostic-resume", args=[workspace_id]).endswith(
            f"/self-study/workspaces/{workspace_id}/diagnostic/resume/"
        )
        assert reverse("self-study-workspace-diagnostic-summary", args=[workspace_id]).endswith(
            f"/self-study/workspaces/{workspace_id}/diagnostic/summary/"
        )

    def test_workspace_plan_experience_routes_are_registered(self):
        workspace_id = "11111111-1111-4111-8111-111111111111"

        assert reverse("self-study-workspace-plan-experience", args=[workspace_id]).endswith(
            f"/self-study/workspaces/{workspace_id}/plan/experience/"
        )
        assert reverse("self-study-workspace-plan-nodes", args=[workspace_id]).endswith(
            f"/self-study/workspaces/{workspace_id}/plan/nodes/"
        )
        assert reverse("self-study-workspace-plan-findings", args=[workspace_id]).endswith(
            f"/self-study/workspaces/{workspace_id}/plan/findings/"
        )
        assert reverse("self-study-workspace-plan-start-learning", args=[workspace_id]).endswith(
            f"/self-study/workspaces/{workspace_id}/plan/start-learning/"
        )

    def test_workspace_learning_studio_routes_are_registered(self):
        workspace_id = "11111111-1111-4111-8111-111111111111"

        expected = {
            "self-study-workspace-learn-experience": "learn/experience",
            "self-study-workspace-learn-start": "learn/start",
            "self-study-workspace-learn-resume": "learn/resume",
            "self-study-workspace-learn-pause": "learn/pause",
            "self-study-workspace-learn-turns": "learn/turns",
            "self-study-workspace-learn-next-turn": "learn/turns/next",
            "self-study-workspace-learn-recap": "learn/recap",
            "self-study-workspace-learn-review": "learn/review",
            "self-study-workspace-learn-current-node": "learn/current-node",
            "self-study-workspace-learn-progress": "learn/progress",
            "self-study-workspace-learn-citations": "learn/citations",
        }

        for route_name, suffix in expected.items():
            assert reverse(route_name, args=[workspace_id]).endswith(
                f"/self-study/workspaces/{workspace_id}/{suffix}/"
            )


class SelfStudyDiagnosticPlanExperiencePrivacyTests(SimpleTestCase):
    def test_diagnostic_experience_projection_excludes_raw_scores(self):
        payload = DiagnosticExperience(
            workspace_id="workspace-1",
            diagnostic_session_id="diagnostic-1",
            status="READY_TO_START",
            can_start=True,
            can_resume=False,
            can_submit=False,
            progress={"answered": 0, "minimum_items": 8, "maximum_items": 12},
            disclosure_complete=True,
            privacy_notice_version="1",
            next_action="diagnostic",
            blocker_codes=[],
        ).to_dict()

        assert "raw_score" not in payload
        assert "ability_estimate" not in payload
        assert "item_scores" not in payload
        assert payload["can_start"] is True

    def test_placement_summary_projection_is_learner_safe(self):
        payload = PlacementSummary(
            workspace_id="workspace-1",
            diagnostic_result_id="diagnostic-1",
            summary_state="FINAL",
            placement_band="starting point identified",
            ready_domains=["Functions"],
            needs_review_domains=["Equations"],
            not_yet_ready_domains=["Calculus"],
            confidence_label="moderate",
            generated_at="2026-07-22T00:00:00+00:00",
            privacy_warnings=[
                "This is not a grade and does not award mastery.",
                "Item-level scores and adaptive routing details are private and hidden.",
            ],
        ).to_dict()

        assert payload["privacy_warnings"][0] == "This is not a grade and does not award mastery."
        assert "raw_score" not in payload
        assert "comparative_rank" not in payload
        assert "adaptive_route" not in payload
