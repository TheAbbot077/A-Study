from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import transaction

from apps.academic.services import LearningContentService, LearningResourceService
from apps.content_intelligence.domain.exceptions import ContentImportDeletionConflictError, ContentImportDeletionError
from apps.content_intelligence.domain.repositories import ContentImportJobRepository
from apps.content_intelligence.infrastructure.persistence import DjangoContentImportJobRepository
from apps.core.events import BusinessEvent, EventPublisher
from apps.storage.services.storage_service import StorageService


@dataclass
class ContentImportDeletionResult:
    content_import_job_id: str
    learning_resource_id: str | None
    stored_file_id: str | None
    deleted_sections: int
    deleted_concepts: int
    storage_deleted: bool


class ContentImportDeletionService:
    def __init__(
        self,
        job_repository: Optional[ContentImportJobRepository] = None,
        learning_resource_service: Optional[LearningResourceService] = None,
        learning_content_service: Optional[LearningContentService] = None,
        storage_service: Optional[StorageService] = None,
        event_publisher: Optional[EventPublisher] = None,
    ) -> None:
        self.job_repository = job_repository or DjangoContentImportJobRepository()
        self.learning_resource_service = learning_resource_service or LearningResourceService()
        self.learning_content_service = learning_content_service or LearningContentService()
        self.storage_service = storage_service
        self.event_publisher = event_publisher or EventPublisher()

    def _cancel_processing_service(self):
        from apps.content_processing.application import CancelContentProcessingJobService

        return CancelContentProcessingJobService(event_publisher=self.event_publisher)

    def _delete_processing_service(self):
        from apps.content_processing.application import DeleteContentProcessingJobService

        return DeleteContentProcessingJobService(event_publisher=self.event_publisher)

    def delete_import(self, job) -> ContentImportDeletionResult:
        self._ensure_deletable(job)
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_intelligence.deletion_requested",
                payload={
                    "content_import_job_id": str(job.id),
                    "learning_resource_id": str(job.learning_resource_id) if job.learning_resource_id is not None else None,
                    "stored_file_id": str(job.stored_file_id) if job.stored_file_id is not None else None,
                },
            )
        )

        learning_resource = job.learning_resource
        stored_file = job.stored_file
        deleted_concepts = 0
        deleted_sections = 0
        processing_job = getattr(job, "processing_job", None)

        if processing_job is not None:
            try:
                from apps.content_processing.domain.exceptions import ProcessingLifecycleError
                from apps.content_processing.models import JobStatus

                if processing_job.status == JobStatus.ACTIVE:
                    processing_job = self._cancel_processing_service().cancel(processing_job)
                self._delete_processing_service().mark_deleted(processing_job)
            except ProcessingLifecycleError as exc:
                raise ContentImportDeletionConflictError(
                    "This import could not be deleted safely because processing is still advancing.",
                    details={"processing_job_id": str(processing_job.id), "reason": str(exc)},
                ) from exc

        with transaction.atomic():
            sections = list(self.learning_content_service.list_sections(learning_resource))
            for section in sections:
                for concept in list(self.learning_content_service.list_concepts(section)):
                    self.learning_content_service.delete_concept(concept)
                    deleted_concepts += 1
                self.learning_content_service.delete_section(section)
                deleted_sections += 1

            self.learning_resource_service.delete_resource(learning_resource)
            job.delete()

        storage_deleted = False
        if stored_file is not None:
            if self.storage_service is None:
                raise ContentImportDeletionError(
                    "No storage deletion service is configured.",
                    code="storage_service_missing",
                    details={"stored_file_id": str(stored_file.id)},
                )
            try:
                self.storage_service.delete_file(stored_file)
                storage_deleted = True
            except Exception as exc:
                self.event_publisher.publish(
                    BusinessEvent.create(
                        "content_intelligence.stored_file_deletion_failed",
                        payload={
                            "content_import_job_id": str(job.id),
                            "stored_file_id": str(stored_file.id),
                            "error_message": str(exc),
                        },
                    )
                )
                raise ContentImportDeletionError(
                    "Database records were removed, but the stored file could not be deleted.",
                    code="stored_file_deletion_failed",
                    details={
                        "content_import_job_id": str(job.id),
                        "stored_file_id": str(stored_file.id),
                        "error_message": str(exc),
                    },
                ) from exc

        result = ContentImportDeletionResult(
            content_import_job_id=str(job.id),
            learning_resource_id=str(getattr(learning_resource, "id", None)) if learning_resource is not None else None,
            stored_file_id=str(getattr(stored_file, "id", None)) if stored_file is not None else None,
            deleted_sections=deleted_sections,
            deleted_concepts=deleted_concepts,
            storage_deleted=storage_deleted,
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "content_intelligence.deleted",
                payload={
                    "content_import_job_id": result.content_import_job_id,
                    "learning_resource_id": result.learning_resource_id,
                    "stored_file_id": result.stored_file_id,
                    "deleted_sections": result.deleted_sections,
                    "deleted_concepts": result.deleted_concepts,
                    "storage_deleted": result.storage_deleted,
                },
            )
        )
        return result

    def _ensure_deletable(self, job) -> None:
        if job.status in {job.Status.PENDING, job.Status.PROCESSING}:
            processing_job = getattr(job, "processing_job", None)
            if processing_job is None:
                raise ContentImportDeletionConflictError(
                    "This import is still processing and cannot be deleted safely yet.",
                    details={"status": job.status},
                )
