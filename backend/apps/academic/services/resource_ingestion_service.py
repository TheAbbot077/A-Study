from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from django.utils import timezone

from apps.academic.domain.models import LearningResource, ResourceIngestionJob
from apps.core.events import BusinessEvent, EventPublisher


class ResourceIngestionService:
    def __init__(self, event_publisher: Optional[EventPublisher] = None) -> None:
        self.event_publisher = event_publisher or EventPublisher()

    def create_job(
        self,
        learning_resource: LearningResource,
        stored_file=None,
        source_type: str = ResourceIngestionJob.SourceType.MANUAL,
        requested_by=None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> ResourceIngestionJob:
        job = ResourceIngestionJob.objects.create(
            learning_resource=learning_resource,
            stored_file=stored_file,
            status=ResourceIngestionJob.Status.PENDING,
            source_type=source_type,
            requested_by=requested_by,
            metadata=metadata or {},
        )
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.resource_ingestion_job_created",
                payload={"job_id": str(job.id), "learning_resource_id": str(learning_resource.id)},
            )
        )
        return job

    def start_job(self, job: ResourceIngestionJob) -> ResourceIngestionJob:
        job.status = ResourceIngestionJob.Status.PROCESSING
        job.started_at = timezone.now()
        job.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.resource_ingestion_job_started",
                payload={"job_id": str(job.id), "learning_resource_id": str(job.learning_resource_id)},
            )
        )
        return job

    def complete_job(self, job: ResourceIngestionJob) -> ResourceIngestionJob:
        job.status = ResourceIngestionJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.resource_ingestion_job_completed",
                payload={"job_id": str(job.id), "learning_resource_id": str(job.learning_resource_id)},
            )
        )
        return job

    def fail_job(self, job: ResourceIngestionJob, error_message: str) -> ResourceIngestionJob:
        job.status = ResourceIngestionJob.Status.FAILED
        job.error_message = error_message
        job.completed_at = timezone.now()
        job.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.resource_ingestion_job_failed",
                payload={
                    "job_id": str(job.id),
                    "learning_resource_id": str(job.learning_resource_id),
                    "error_message": error_message,
                },
            )
        )
        return job

    def cancel_job(self, job: ResourceIngestionJob) -> ResourceIngestionJob:
        job.status = ResourceIngestionJob.Status.CANCELLED
        job.completed_at = timezone.now()
        job.save()
        self.event_publisher.publish(
            BusinessEvent.create(
                "academic.resource_ingestion_job_cancelled",
                payload={"job_id": str(job.id), "learning_resource_id": str(job.learning_resource_id)},
            )
        )
        return job

    def get_job(self, learning_resource: LearningResource, job_id: str) -> ResourceIngestionJob:
        return ResourceIngestionJob.objects.get(learning_resource=learning_resource, id=job_id)

    def list_jobs(self) -> list[ResourceIngestionJob]:
        return list(ResourceIngestionJob.objects.all().order_by("-created_at"))

    def list_jobs_for_resource(self, learning_resource: LearningResource) -> list[ResourceIngestionJob]:
        return list(ResourceIngestionJob.objects.filter(learning_resource=learning_resource).order_by("-created_at"))
