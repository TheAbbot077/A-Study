import pytest
from rest_framework.test import APIClient

from apps.study_lab.application.services import CreateLearnerWorkspaceNoteService, CreateStudyWorkspaceService
from apps.study_lab.domain.enums import NoteStatus, WorkspaceType
from apps.users.domain.models import Institution


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def learners(django_user_model):
    a = django_user_model.objects.create_user(email="learner-a@example.com", password="secret")
    b = django_user_model.objects.create_user(email="learner-b@example.com", password="secret")
    return a, b


@pytest.fixture
def workspace(learners):
    learner, _ = learners
    return CreateStudyWorkspaceService.execute(learner_id=learner.id, workspace_type=WorkspaceType.SELF_STUDY, title="Study")


@pytest.fixture
def note(workspace, learners):
    learner, _ = learners
    return CreateLearnerWorkspaceNoteService.execute(workspace.id, learner.id, title="Note", content="Body")


@pytest.mark.django_db
def test_note_detail_update_delete_lifecycle(api_client, workspace, note, learners):
    learner, _ = learners
    api_client.force_authenticate(learner)

    detail = api_client.get(f"/api/study-lab/workspaces/{workspace.id}/notes/{note.id}/")
    assert detail.status_code == 200
    assert detail.data["id"] == str(note.id)

    updated = api_client.patch(f"/api/study-lab/workspaces/{workspace.id}/notes/{note.id}/", {"title": "Updated", "version": note.version}, format="json")
    assert updated.status_code == 200
    assert updated.data["title"] == "Updated"

    deleted = api_client.delete(f"/api/study-lab/workspaces/{workspace.id}/notes/{note.id}/")
    assert deleted.status_code == 200


@pytest.mark.django_db
def test_note_stale_version_rejected(api_client, workspace, note, learners):
    learner, _ = learners
    api_client.force_authenticate(learner)
    response = api_client.patch(f"/api/study-lab/workspaces/{workspace.id}/notes/{note.id}/", {"title": "Updated", "version": note.version - 1}, format="json")
    assert response.status_code == 409
    assert response.data["code"] == "NOTE_VERSION_CONFLICT"


@pytest.mark.django_db
def test_cross_learner_denied(api_client, workspace, note, learners):
    _, other = learners
    api_client.force_authenticate(other)
    response = api_client.get(f"/api/study-lab/workspaces/{workspace.id}/notes/{note.id}/")
    assert response.status_code in {403, 404}


@pytest.mark.django_db
def test_authentication_required(api_client, workspace, note):
    response = api_client.get(f"/api/study-lab/workspaces/{workspace.id}/notes/{note.id}/")
    assert response.status_code in {401, 403}
