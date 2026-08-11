import pytest
from rest_framework.test import APIClient

from apps.study_lab.application.interoperability_services import CreateStudyArtefactService, RequestStudyScaffoldGenerationService, CompleteStudyScaffoldGenerationService
from apps.study_lab.application.services import CreateStudyWorkspaceService
from apps.study_lab.domain.enums import StudyArtefactLineageRelation, StudyArtefactOrigin, StudyArtefactType, StudyScaffoldGenerationType, WorkspaceType
from apps.study_lab.infrastructure.scaffold_adapters import DeterministicStudyScaffoldGenerationProvider, ScaffoldGenerationProviderRegistry
from apps.study_lab.domain.models import StudyArtefactLineage


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def learner(django_user_model):
    return django_user_model.objects.create_user(email="scaffold@example.com", password="secret")


@pytest.fixture
def workspace(learner):
    return CreateStudyWorkspaceService.execute(learner_id=learner.id, workspace_type=WorkspaceType.SELF_STUDY, title="Desk")


@pytest.fixture
def scaffold_provider():
    provider = DeterministicStudyScaffoldGenerationProvider()
    ScaffoldGenerationProviderRegistry.register_provider("STUDY_LAB", provider)
    try:
        yield provider
    finally:
        ScaffoldGenerationProviderRegistry.reset_provider("STUDY_LAB")


@pytest.mark.django_db
def test_scaffold_generation_request_and_completion(workspace, learner, scaffold_provider):
    source = CreateStudyArtefactService.execute(
        workspace.id,
        learner.id,
        artefact_type=StudyArtefactType.TEXT_NOTE,
        title="Source",
        summary="Seed",
        creation_source=StudyArtefactOrigin.NATIVE,
        native_payload={"body": "seed"},
    )
    request = RequestStudyScaffoldGenerationService.execute(
        workspace.id,
        learner.id,
        generation_type=StudyScaffoldGenerationType.EQUATION_AND_FORMULA_SHEET.value,
        requested_artefact_type=StudyArtefactType.FORMULA_SHEET.value,
        source_artefact_ids=[source.id],
        idempotency_key="idem-1",
    )
    completed = CompleteStudyScaffoldGenerationService.execute(workspace.id, learner.id, request.id)
    completed.refresh_from_db()
    assert completed.status == "COMPLETED"
    assert completed.result_artefact is not None
    assert completed.result_artefact.artefact_type == StudyArtefactType.FORMULA_SHEET
    assert scaffold_provider.generate_calls == 1
    assert StudyArtefactLineage.objects.filter(
        workspace=workspace,
        source_artefact=source,
        target_artefact=completed.result_artefact,
        relation_type=StudyArtefactLineageRelation.DERIVED_FROM,
    ).exists()


@pytest.mark.django_db
def test_scaffold_generation_api_is_deterministic(client, learner, workspace, scaffold_provider):
    client.force_authenticate(learner)
    source = CreateStudyArtefactService.execute(workspace.id, learner.id, artefact_type=StudyArtefactType.TEXT_NOTE, title="Seed")
    response = client.post(
        f"/api/study-lab/workspaces/{workspace.id}/scaffold-generation/",
        {
            "generation_type": StudyScaffoldGenerationType.FLASHCARDS_AND_SCRATCHPAD.value,
            "requested_artefact_type": StudyArtefactType.FLASHCARD_SET.value,
            "source_artefact_ids": [str(source.id)],
            "idempotency_key": "idem-api",
            "native_payload": {"topic": "algebra"},
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["generation_type"] == StudyScaffoldGenerationType.FLASHCARDS_AND_SCRATCHPAD.value
    assert response.data["status"] == "READY"
    assert response.data["request_checksum"]
