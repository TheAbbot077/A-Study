import pytest
from unittest.mock import patch

from apps.study_lab.application.interoperability_services import (
    CreateStudyArtefactService,
    LaunchWorkspaceToolService,
    RegisterStudyToolService,
    ResolveArtefactCompatibilityService,
    ResolveToolAvailabilityService,
    SuspendWorkspaceToolSessionService,
    ResumeWorkspaceToolService,
    RequestTransformationService,
    VersionStudyArtefactService,
)
from apps.study_lab.application.services import InvokeWorkspaceToolService
from apps.study_lab.domain.enums import StudyArtefactOrigin, StudyArtefactType, StudyArtefactVisibility, ToolAvailabilityReasonCode, ToolInvocationLifecycleStatus, WorkspaceType, WorkspaceToolSessionStatus
from apps.study_lab.domain.exceptions import ArtefactVersionConflictError, ToolProviderUnavailableError
from apps.study_lab.domain.models import WorkspaceToolInvocation, WorkspaceToolSession
from apps.study_lab.infrastructure.adapters import ProviderAdapterRegistry


class DeterministicAvailableTestProvider:
    def __init__(self):
        self.launch_calls = 0
        self.resume_calls = 0

    def evaluate_availability(self, workspace, tool):
        return ToolAvailabilityReasonCode.AVAILABLE, "available"

    def launch(self, workspace, tool, learner_id, **kwargs):
        self.launch_calls += 1
        return f"test-session:{tool.tool_key}:{self.launch_calls}"

    def resume(self, workspace, session, learner_id):
        self.resume_calls += 1
        return f"test-resume:{session.id}:{self.resume_calls}"

    def import_artefact(self, workspace, learner_id, provider_reference):
        return {"metadata": {}, "schema_version": "1", "title": "", "summary": ""}

    def export_artefact(self, workspace, artefact, learner_id):
        return f"test-export:{artefact.id}"


@pytest.fixture
def available_provider():
    provider = DeterministicAvailableTestProvider()
    ProviderAdapterRegistry.register_adapter("ABBOT", provider)
    try:
        yield provider
    finally:
        ProviderAdapterRegistry.reset_adapter("ABBOT")


@pytest.fixture
def learner(django_user_model):
    return django_user_model.objects.create_user(email="tool-learner@example.com", password="secret")


@pytest.fixture
def workspace(learner):
    from apps.study_lab.application.services import CreateStudyWorkspaceService

    return CreateStudyWorkspaceService.execute(learner_id=learner.id, workspace_type=WorkspaceType.SELF_STUDY, title="Desk")


@pytest.mark.django_db
def test_tool_registry_and_availability(workspace, learner):
    RegisterStudyToolService.execute(
        tool_key="ABBOT_MENTOR",
        display_name="Abbot Mentor",
        provider_context="ABBOT",
        supported_workspace_types=[WorkspaceType.SELF_STUDY],
        supported_artefact_inputs=["CONCEPT_REFERENCE"],
        supported_artefact_outputs=["SESSION_SUMMARY"],
        supports_resume=True,
    )
    availability = ResolveToolAvailabilityService.execute(workspace.id, learner.id, "ABBOT_MENTOR")
    assert availability["reason_code"] == ToolAvailabilityReasonCode.PROVIDER_UNAVAILABLE


@pytest.mark.django_db
def test_artefact_create_version_and_compatibility(workspace, learner):
    artefact = CreateStudyArtefactService.execute(
        workspace.id,
        learner.id,
        artefact_type=StudyArtefactType.TEXT_NOTE,
        title="Note",
        summary="Summary",
        visibility=StudyArtefactVisibility.PRIVATE,
        creation_source=StudyArtefactOrigin.NATIVE,
        native_payload={"body": "safe"},
    )
    assert artefact.version == 1
    updated = VersionStudyArtefactService.execute(workspace.id, learner.id, artefact.id, version=1, title="Updated")
    assert updated.version == 2
    compat = ResolveArtefactCompatibilityService.execute(workspace.id, learner.id, artefact_type=StudyArtefactType.TEXT_NOTE, schema_version="1")
    assert compat["status"] == "COMPATIBLE"


@pytest.mark.django_db
def test_version_conflict_rejected(workspace, learner):
    artefact = CreateStudyArtefactService.execute(workspace.id, learner.id, artefact_type=StudyArtefactType.TEXT_NOTE)
    with pytest.raises(ArtefactVersionConflictError):
        VersionStudyArtefactService.execute(workspace.id, learner.id, artefact.id, version=0, title="stale")


@pytest.mark.django_db
def test_launch_fails_closed_when_provider_unavailable(workspace, learner):
    RegisterStudyToolService.execute(tool_key="ARIEL_TEACH", display_name="Ariel Teach", provider_context="ARIEL")
    with pytest.raises(ToolProviderUnavailableError):
        LaunchWorkspaceToolService.execute(workspace.id, learner.id, "ARIEL_TEACH")


@pytest.mark.django_db
def test_transformation_request_works_internally(workspace, learner):
    artefact = CreateStudyArtefactService.execute(workspace.id, learner.id, artefact_type=StudyArtefactType.TEXT_NOTE)
    RegisterStudyToolService.execute(tool_key="CONCEPT_CHECK", display_name="Concept Check", provider_context="CONCEPT_CHECK")
    from apps.study_lab.domain.models import StudyArtefactTransformationDefinition

    StudyArtefactTransformationDefinition.objects.create(
        transformation_key="text-note-to-summary",
        source_artefact_types=[StudyArtefactType.TEXT_NOTE],
        destination_type=StudyArtefactType.REVISION_SUMMARY,
        deterministic=True,
        provider_context="STUDY_LAB",
        learner_approval_required=False,
        supported_schema_versions=["1"],
    )
    request = RequestTransformationService.execute(workspace.id, learner.id, source_artefact_id=artefact.id, transformation_key="text-note-to-summary")
    assert request.status == "READY"


@pytest.mark.django_db
def test_legacy_invocation_delegates_to_canonical_launch(workspace, learner):
    RegisterStudyToolService.execute(tool_key="ABBOT_MENTOR", display_name="Abbot Mentor", provider_context="ABBOT")
    with patch("apps.study_lab.application.services.CanonicalLaunchWorkspaceToolService.execute") as delegate:
        delegate.return_value = ("session", "invocation")
        result = InvokeWorkspaceToolService.execute(workspace.id, learner.id, "ABBOT_MENTOR", idempotency_key="idem-1", input_artefact_ids=["x"])
    assert result == "invocation"
    delegate.assert_called_once()


@pytest.mark.django_db
def test_new_invocation_uses_canonical_lifecycle(workspace, learner, available_provider):
    RegisterStudyToolService.execute(tool_key="ABBOT_MENTOR", display_name="Abbot Mentor", provider_context="ABBOT")
    session, invocation = LaunchWorkspaceToolService.execute(workspace.id, learner.id, "ABBOT_MENTOR")
    assert isinstance(invocation, WorkspaceToolInvocation)
    assert invocation.status == ToolInvocationLifecycleStatus.COMPLETED
    assert session.status == WorkspaceToolSessionStatus.OPEN
    assert available_provider.launch_calls == 1


@pytest.mark.django_db
def test_resume_session_is_idempotent_on_open_session(workspace, learner, available_provider):
    RegisterStudyToolService.execute(tool_key="ABBOT_MENTOR", display_name="Abbot Mentor", provider_context="ABBOT")
    session, _ = LaunchWorkspaceToolService.execute(workspace.id, learner.id, "ABBOT_MENTOR")
    SuspendWorkspaceToolSessionService.execute(workspace.id, learner.id, session.id, idempotency_key="suspend-1")
    resumed = ResumeWorkspaceToolService.execute(workspace.id, learner.id, session.id, idempotency_key="resume-1")
    assert resumed.id == session.id
    assert resumed.status == WorkspaceToolSessionStatus.OPEN
    assert available_provider.resume_calls == 1
