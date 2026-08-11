import pytest

from apps.study_lab.application.services import CreateStudyWorkspaceService, SetWorkspaceContextService
from apps.study_lab.domain.enums import WorkspaceType
from apps.study_lab.domain.exceptions import ContextMismatchError
from apps.study_lab.domain.models import WorkspaceContext


@pytest.mark.django_db
def test_workspace_can_select_own_context(django_user_model):
    learner = django_user_model.objects.create_user(email="ctx-a@example.com", password="secret")
    workspace = CreateStudyWorkspaceService.execute(learner_id=learner.id, workspace_type=WorkspaceType.SELF_STUDY, title="A")
    context = SetWorkspaceContextService.execute(workspace.id, learner.id)
    assert context.workspace_id == workspace.id


@pytest.mark.django_db
def test_workspace_cannot_select_another_workspace_context(django_user_model):
    learner = django_user_model.objects.create_user(email="ctx-b@example.com", password="secret")
    other = django_user_model.objects.create_user(email="ctx-c@example.com", password="secret")
    workspace_a = CreateStudyWorkspaceService.execute(learner_id=learner.id, workspace_type=WorkspaceType.SELF_STUDY, title="A")
    workspace_b = CreateStudyWorkspaceService.execute(learner_id=other.id, workspace_type=WorkspaceType.SELF_STUDY, title="B")
    context_b = WorkspaceContext.objects.get(workspace=workspace_b)

    with pytest.raises(ContextMismatchError):
        SetWorkspaceContextService.execute(workspace_a.id, learner.id, context_id=context_b.id)


@pytest.mark.django_db
def test_cross_learner_context_selection_denied(django_user_model):
    learner = django_user_model.objects.create_user(email="ctx-d@example.com", password="secret")
    other = django_user_model.objects.create_user(email="ctx-e@example.com", password="secret")
    workspace = CreateStudyWorkspaceService.execute(learner_id=learner.id, workspace_type=WorkspaceType.SELF_STUDY, title="A")
    other_workspace = CreateStudyWorkspaceService.execute(learner_id=other.id, workspace_type=WorkspaceType.SELF_STUDY, title="B")
    context = WorkspaceContext.objects.get(workspace=other_workspace)

    with pytest.raises(ContextMismatchError):
        SetWorkspaceContextService.execute(workspace.id, learner.id, context_id=context.id)
