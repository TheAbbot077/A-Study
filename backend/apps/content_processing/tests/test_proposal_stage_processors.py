from types import SimpleNamespace
from unittest.mock import Mock

from apps.content_processing.application.services import ProcessingStageContext
from apps.content_processing.application.stage_processors import GenerateAcademicImportProposalProcessor, PopulateAcademicPlatformProcessor
from apps.content_processing.domain.models import ProcessingStage


def context(stage):
    return ProcessingStageContext("job", "attempt", "resource", "file", "pipeline", stage, "correlation")


def test_validating_processor_records_approval_before_population():
    proposal = SimpleNamespace(id="proposal", review_required=False, review_state="ready_for_review", population_state="not_ready", statistics={"section_count": 1, "concept_count": 2}, result_checksum="checksum")
    service = Mock(); service.execute.return_value = (proposal, [])
    approval = Mock()
    def approve(item, **kwargs):
        item.review_state = "approved"; item.population_state = "ready_for_population"
    approval.approve.side_effect = approve
    result = GenerateAcademicImportProposalProcessor(service, approval).execute(context(ProcessingStage.VALIDATING))
    approval.approve.assert_called_once()
    assert result.next_stage == ProcessingStage.POPULATING
    assert result.output_references["academic_import_proposal_id"] == "proposal"


def test_population_processor_returns_population_identity_and_counts():
    population = SimpleNamespace(id="population", proposal_id="proposal", created_sections=1, updated_sections=0, created_concepts=2, updated_concepts=0, checksum="checksum")
    service = Mock(); service.execute.return_value = (population, [])
    result = PopulateAcademicPlatformProcessor(service).execute(context(ProcessingStage.POPULATING))
    assert result.next_stage == ProcessingStage.INDEXING
    assert result.output_references["academic_population_job_id"] == "population"
