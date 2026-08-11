import pytest
from rest_framework.test import APIClient

from apps.study_lab.application.interoperability_services import CreateStudyArtefactService, RegisterStudyToolService
from apps.study_lab.application.services import CreateStudyWorkspaceService
from apps.study_lab.domain.enums import StudyArtefactType, WorkspaceType


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def learner(django_user_model):
    return django_user_model.objects.create_user(email="interop@example.com", password="secret")


@pytest.fixture
def workspace(learner):
    return CreateStudyWorkspaceService.execute(learner_id=learner.id, workspace_type=WorkspaceType.SELF_STUDY, title="Desk")


@pytest.mark.django_db
def test_tool_list_requires_auth(client):
    assert client.get("/api/study-lab/tools/").status_code in {401, 403}


@pytest.mark.django_db
def test_artefact_lifecycle_api(client, learner, workspace):
    client.force_authenticate(learner)
    created = client.post(
        f"/api/study-lab/workspaces/{workspace.id}/artefacts/",
        {
            "artefact_type": StudyArtefactType.TEXT_NOTE.value,
            "title": "Note",
            "summary": "Short",
            "visibility": "PRIVATE",
            "creation_source": "NATIVE",
            "native_payload": {"body": "Short"},
        },
        format="json",
    )
    assert created.status_code == 201, created.data
    artefact_id = created.data["id"]
    fetched = client.get(f"/api/study-lab/workspaces/{workspace.id}/artefacts/{artefact_id}/")
    assert fetched.status_code == 200


@pytest.mark.django_db
def test_tool_launch_fails_closed(client, learner, workspace):
    client.force_authenticate(learner)
    RegisterStudyToolService.execute(tool_key="ABBOT_MENTOR", display_name="Abbot Mentor", provider_context="ABBOT")
    response = client.post(f"/api/study-lab/workspaces/{workspace.id}/tools/ABBOT_MENTOR/launch/", {"idempotency_key": "one"}, format="json")
    assert response.status_code in {400, 409, 503}


@pytest.mark.django_db
def test_tool_launch_provider_unavailable_is_translated(client, learner, workspace):
    client.force_authenticate(learner)
    RegisterStudyToolService.execute(tool_key="ARIEL_TEACH", display_name="Ariel Teach", provider_context="ARIEL")
    response = client.post(f"/api/study-lab/workspaces/{workspace.id}/tools/ARIEL_TEACH/launch/", {"idempotency_key": "one"}, format="json")
    assert response.status_code == 503
    assert response.data["code"] == "PROVIDER_UNAVAILABLE"
