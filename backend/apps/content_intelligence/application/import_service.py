from __future__ import annotations

from typing import Any, Optional

from apps.content_intelligence.domain.exceptions import UnsupportedFormatError
from apps.content_intelligence.domain.models import ContentImportJob
from apps.content_intelligence.domain.repositories import ContentImportJobRepository
from apps.content_intelligence.infrastructure.persistence import DjangoContentImportJobRepository
from apps.core.events import BusinessEvent, EventPublisher


class ImportService:
    def __init__(
        self,
        job_repository: Optional[ContentImportJobRepository] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentImportJobRepository()
        self.event_publisher = event_publisher or EventPublisher()

    def _create_processing_job_service(self):
        from apps.content_processing.application import CreateContentProcessingJobService

        return CreateContentProcessingJobService(event_publisher=self.event_publisher)

    def _queue_processing_job_service(self):
        from apps.content_processing.application import QueueContentProcessingJobService

        return QueueContentProcessingJobService(event_publisher=self.event_publisher)

    def _retry_processing_job_service(self):
        from apps.content_processing.application import RetryContentProcessingJobService

        return RetryContentProcessingJobService(event_publisher=self.event_publisher)

    def create_import_job(
        self,
        learning_resource: Any,
        requested_by=None,
        metadata: dict | None = None,
    ) -> ContentImportJob:
        stored_file = learning_resource.stored_file
        format_type = self._detect_format(learning_resource, stored_file)
        job = ContentImportJob(
            learning_resource=learning_resource,
            stored_file=stored_file,
            format_type=format_type,
            requested_by=requested_by,
            metadata=metadata or {},
        )
        job = self.job_repository.add(job)
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_intelligence.import_started",
                payload={
                    "content_import_job_id": str(job.id),
                    "learning_resource_id": str(learning_resource.id),
                    "stored_file_id": str(stored_file.id) if stored_file else None,
                    "format_type": job.format_type,
                },
            )
        )
        processing_job = self._create_processing_job_service().create_or_resolve(
            resource=learning_resource,
            stored_file=stored_file,
            legacy_import_job=job,
            requested_by=requested_by,
        )
        self._queue_processing_job_service().queue(processing_job)
        return self.job_repository.get(str(job.id))

    def get_job(self, job_id: str) -> ContentImportJob:
        return self.job_repository.get(job_id)

    def list_jobs(self) -> list[ContentImportJob]:
        return self.job_repository.list_all()

    def retry_failed_import(self, job: ContentImportJob) -> ContentImportJob:
        metadata = dict(job.metadata or {})
        metadata["retry_count"] = int(metadata.get("retry_count", 0) or 0) + 1
        metadata.pop("failure", None)
        job.metadata = metadata
        self.job_repository.save(job)
        processing_job = getattr(job, "processing_job", None)
        if processing_job is None:
            processing_job = self._create_processing_job_service().create_or_resolve(
                resource=job.learning_resource,
                stored_file=job.stored_file,
                legacy_import_job=job,
                requested_by=job.requested_by,
            )
            self._queue_processing_job_service().queue(processing_job)
        else:
            self._retry_processing_job_service().retry(processing_job, actor=job.requested_by)
        return self.job_repository.get(str(job.id))

    def _detect_format(self, learning_resource: Any, stored_file: Any) -> str:
        filename = (
            (getattr(stored_file, "original_filename", "") if stored_file else "")
            or getattr(learning_resource, "source_label", "")
            or learning_resource.title
        ).lower()
        content_type = (getattr(stored_file, "content_type", "") or "").lower()
        if filename.endswith(".pdf"):
            return ContentImportJob.FormatType.PDF
        if filename.endswith(".docx"):
            return ContentImportJob.FormatType.DOCX
        if content_type == "application/pdf":
            return ContentImportJob.FormatType.PDF
        if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return ContentImportJob.FormatType.DOCX
        raise UnsupportedFormatError("Only PDF and DOCX uploads are supported.")
