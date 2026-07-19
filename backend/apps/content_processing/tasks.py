"""Celery task discovery bridge for content processing."""

from apps.content_processing.infrastructure.celery.tasks import (
    process_content_processing_stage_task,
)

__all__ = ["process_content_processing_stage_task"]
