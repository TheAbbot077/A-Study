from inspect import signature

from apps.content_processing.infrastructure.celery.tasks import (
    process_content_processing_stage_task as infrastructure_task,
)
from apps.content_processing.tasks import process_content_processing_stage_task


def test_app_task_bridge_exposes_the_infrastructure_task():
    assert process_content_processing_stage_task is infrastructure_task


def test_processing_task_name_and_payload_contract_are_stable():
    assert process_content_processing_stage_task.name == "content_processing.process_stage"
    assert tuple(signature(process_content_processing_stage_task.run).parameters) == (
        "job_id",
        "attempt_id",
        "expected_stage",
        "correlation_id",
    )
