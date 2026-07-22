from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import reverse

from apps.academic.domain.models import LearningResource
from apps.content_processing.domain.models import JobStatus, ProcessingStage
from apps.self_study.application.workspace_services import project_material_status
from apps.self_study.domain.workspace import SelfStudyNextAction, WorkspaceBlockerCode, build_next_action
from apps.self_study.workspace_models import SelfStudyWorkspace, WorkspaceMaterialStatus


class SelfStudyWorkspaceModelContractTests(SimpleTestCase):
    def test_workspace_display_name_is_not_academic_subject_authority(self):
        field_names = {field.name for field in SelfStudyWorkspace._meta.fields}

        self.assertIn("display_name", field_names)
        self.assertNotIn("subject", field_names)

    def test_workspace_routes_are_registered(self):
        self.assertEqual(reverse("self-study-workspace-list"), "/api/self-study/workspaces/")
        workspace_id = "11111111-1111-4111-8111-111111111111"
        self.assertEqual(
            reverse("self-study-workspace-next-action", kwargs={"pk": workspace_id}),
            f"/api/self-study/workspaces/{workspace_id}/next-action/",
        )
        self.assertEqual(
            reverse("self-study-workspace-diagnostic-start", kwargs={"pk": workspace_id}),
            f"/api/self-study/workspaces/{workspace_id}/diagnostic/start/",
        )


class SelfStudyNextActionTests(SimpleTestCase):
    def test_next_action_projection_uses_safe_routes_and_stable_blockers(self):
        projection = build_next_action(
            SelfStudyNextAction.COMPLETE_INTENT,
            workspace_id="workspace-1",
            blockers=[WorkspaceBlockerCode.INTENT_REQUIRED.value],
            safe_ids={"workspace_id": "workspace-1"},
            summary={"workspace_status": "INTENT_REQUIRED"},
        ).to_dict()

        self.assertEqual(projection["code"], "COMPLETE_INTENT")
        self.assertEqual(projection["target_route"], "/dashboard/self-study/workspace-1/intent")
        self.assertEqual(projection["blocker_codes"], ["INTENT_REQUIRED"])
        self.assertEqual(projection["safe_status_summary"]["workspace_status"], "INTENT_REQUIRED")


class WorkspaceMaterialProjectionTests(SimpleTestCase):
    def test_archived_resource_is_retired_and_blocking(self):
        resource = SimpleNamespace(status=LearningResource.Status.ARCHIVED)

        status, blockers, summary = project_material_status(resource, None)

        self.assertEqual(status, WorkspaceMaterialStatus.RETIRED)
        self.assertEqual(blockers, ["MATERIAL_RETIRED"])
        self.assertEqual(summary["resource_status"], LearningResource.Status.ARCHIVED)

    def test_active_processing_job_waits_for_processing(self):
        resource = SimpleNamespace(status=LearningResource.Status.ACTIVE)
        job = SimpleNamespace(status=JobStatus.ACTIVE, current_stage=ProcessingStage.EXTRACTING, failure={})

        status, blockers, summary = project_material_status(resource, job)

        self.assertEqual(status, WorkspaceMaterialStatus.PROCESSING)
        self.assertEqual(blockers, ["MATERIALS_PROCESSING"])
        self.assertEqual(summary["processing_stage"], ProcessingStage.EXTRACTING)

    def test_unsupported_format_is_sanitized_as_stable_blocker(self):
        resource = SimpleNamespace(status=LearningResource.Status.ACTIVE)
        job = SimpleNamespace(
            status=JobStatus.FAILED,
            current_stage=ProcessingStage.INSPECTING,
            failure={"code": "unsupported_format", "internal_message": "raw parser trace"},
        )

        status, blockers, summary = project_material_status(resource, job)

        self.assertEqual(status, WorkspaceMaterialStatus.UNSUPPORTED_FORMAT)
        self.assertEqual(blockers, ["MATERIAL_UNSUPPORTED_FORMAT"])
        self.assertNotIn("internal_message", summary)
