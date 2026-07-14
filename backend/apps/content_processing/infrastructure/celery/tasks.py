from __future__ import annotations

from celery import shared_task

from apps.content_processing.application.services import OrchestrateContentProcessingStageService


@shared_task(name="content_processing.process_stage")
def process_content_processing_stage_task(job_id: str, attempt_id: str, expected_stage: str, correlation_id: str = "") -> None:
    OrchestrateContentProcessingStageService().execute(job_id, attempt_id, expected_stage, correlation_id)

