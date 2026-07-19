import pytest
from django.core.exceptions import ValidationError

from apps.academic_review.domain.models import AcademicPopulationRun, PopulationRunStatus


def unsaved_run(**overrides):
    values = {
        "plan_snapshot": {"expected_section_count": 2, "expected_concept_count": 3},
        "status": PopulationRunStatus.PLANNED,
    }
    values.update(overrides)
    return AcademicPopulationRun(**values)


def test_population_run_valid_lifecycle_and_reconciliation():
    run = unsaved_run()
    run.start()
    run.complete(created_sections=2, matched_sections=0, created_concepts=2, matched_concepts=1)
    assert run.status == PopulationRunStatus.POPULATED


def test_population_run_rejects_unresolved_plan():
    run = unsaved_run()
    run.start()
    with pytest.raises(ValidationError):
        run.complete(created_sections=1, matched_sections=0, created_concepts=3, matched_concepts=0)


def test_population_run_failure_requires_stable_code():
    with pytest.raises(ValidationError):
        unsaved_run().fail(code="")


def test_populated_run_is_terminal():
    run = unsaved_run(status=PopulationRunStatus.POPULATED)
    with pytest.raises(ValidationError):
        run.fail(code="ACADEMIC_POPULATION_FAILED")
