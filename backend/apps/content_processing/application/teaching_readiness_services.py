from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services.audit_service import AuditService
from apps.content_processing.domain.models import ContentProcessingJob, JobStatus
from apps.content_processing.domain.teaching_readiness import (
    CheckSeverity, TeachingReadinessDecision, TeachingReadinessPolicy,
)
from apps.content_processing.infrastructure.persistence.teaching_readiness_models import TeachingReadinessEvaluation
from apps.content_processing.infrastructure.teaching_readiness_gateway import DjangoTeachingReadinessSnapshotGateway
from apps.core.events import BusinessEvent, EventPublisher


def _fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


class AssembleTeachingReadinessSnapshotService:
    def __init__(self, gateway=None, policy=None):
        self.gateway = gateway or DjangoTeachingReadinessSnapshotGateway()
        self.policy = policy or TeachingReadinessPolicy()

    def assemble(self, resource_id: str):
        return self.gateway.assemble(str(resource_id), self.policy.version)


class EvaluateTeachingReadinessService:
    def __init__(self, assembler=None, policy=None, events=None, audit=None):
        self.policy = policy or TeachingReadinessPolicy()
        self.assembler = assembler or AssembleTeachingReadinessSnapshotService(policy=self.policy)
        self.events = events or EventPublisher()
        self.audit = audit or AuditService(event_publisher=self.events)

    def execute(self, *, resource_id, idempotency_key, actor=None, trigger="staff", reason="", expected_lineage_fingerprint=""):
        key = (idempotency_key or "").strip()
        if not key:
            raise ValidationError("READINESS_IDEMPOTENCY_CONFLICT")
        if trigger == "staff" and (actor is None or not actor.is_staff):
            raise PermissionDenied("READINESS_EVALUATION_NOT_AUTHORIZED")
        request_fingerprint = _fingerprint([str(resource_id), expected_lineage_fingerprint, trigger])
        replay = TeachingReadinessEvaluation.objects.filter(idempotency_key=key).first()
        if replay:
            if replay.request_fingerprint != request_fingerprint:
                raise ValidationError("READINESS_IDEMPOTENCY_CONFLICT")
            return replay, True

        snapshot = self.assembler.assemble(str(resource_id))
        lineage_fingerprint = snapshot.lineage_fingerprint()
        if expected_lineage_fingerprint and expected_lineage_fingerprint != lineage_fingerprint:
            raise ValidationError("READINESS_LINEAGE_CONFLICT")
        equivalent = TeachingReadinessEvaluation.objects.filter(
            resource_id=resource_id, lineage_fingerprint=lineage_fingerprint,
            policy_version=self.policy.version, invalidated_at__isnull=True,
        ).first()
        if equivalent:
            return equivalent, True

        checks = self.policy.evaluate(snapshot)
        blockers = [item for item in checks if not item.passed and item.severity == CheckSeverity.BLOCKER]
        warnings = [item for item in checks if not item.passed and item.severity == CheckSeverity.WARNING]
        decision = TeachingReadinessDecision.BLOCKED if blockers else TeachingReadinessDecision.READY
        with transaction.atomic():
            job = ContentProcessingJob.objects.select_for_update().get(id=snapshot.processing_job_id)
            current = self.assembler.assemble(str(resource_id))
            if current.lineage_fingerprint() != lineage_fingerprint:
                decision = TeachingReadinessDecision.STALE
                blockers = list(blockers) + []
            prior = TeachingReadinessEvaluation.objects.filter(
                resource_id=resource_id, invalidated_at__isnull=True
            ).order_by("-evaluated_at").first()
            if prior and prior.lineage_fingerprint != lineage_fingerprint:
                prior.invalidated_at = timezone.now()
                prior.invalidation_reason = "AUTHORITATIVE_LINEAGE_CHANGED"
                prior.save(update_fields=["invalidated_at", "invalidation_reason"])
                if job.status == JobStatus.READY_FOR_TEACHING:
                    job.status = JobStatus.READY_FOR_REVIEW
                    job.progress = 98
                    job.transition_version += 1
                    job.last_transition_at = timezone.now()
            evaluation = TeachingReadinessEvaluation.objects.create(
                resource_id=resource_id, subject_id=snapshot.subject_id,
                processing_job_id=snapshot.processing_job_id,
                processing_attempt_id=snapshot.processing_attempt_id or None,
                approved_projection_id=snapshot.approved_projection_id or None,
                approval_decision_id=snapshot.approval_decision_id or None,
                academic_population_run_id=snapshot.academic_population_run_id or None,
                retrieval_synchronization_run_id=snapshot.retrieval_synchronization_run_id or None,
                retrieval_generation_id=snapshot.retrieval_generation_id or None,
                requested_by=actor, trigger=trigger, reason=reason, idempotency_key=key,
                request_fingerprint=request_fingerprint, lineage_fingerprint=lineage_fingerprint,
                policy_version=self.policy.version, decision=decision,
                checks_passed=sum(item.passed for item in checks),
                checks_failed=sum(not item.passed for item in checks),
                blocker_count=len(blockers), warning_count=len(warnings),
                snapshot=asdict(snapshot), checks=[asdict(item) for item in checks],
                supersedes_evaluation=prior,
            )
            if decision == TeachingReadinessDecision.READY:
                job.grant_teaching_readiness(str(evaluation.id))
                job.save()
            transaction.on_commit(lambda: self._after_commit(evaluation, job, actor))
        return evaluation, False

    def _after_commit(self, evaluation, job, actor):
        event_name = (
            "teaching_readiness.granted"
            if evaluation.decision == TeachingReadinessDecision.READY
            else "teaching_readiness.blocked"
        )
        payload = {
            "evaluation_id": str(evaluation.id), "resource_id": str(evaluation.resource_id),
            "subject_id": str(evaluation.subject_id), "processing_job_id": str(evaluation.processing_job_id),
            "lineage_fingerprint": evaluation.lineage_fingerprint,
            "policy_version": evaluation.policy_version, "decision": evaluation.decision,
            "blocker_count": evaluation.blocker_count, "warning_count": evaluation.warning_count,
        }
        self.events.publish(BusinessEvent.create("teaching_readiness.evaluation_started", payload=payload))
        self.events.publish(BusinessEvent.create(event_name, payload=payload))
        if evaluation.decision == TeachingReadinessDecision.READY:
            self.events.publish(BusinessEvent.create("resource.ready_for_teaching", payload=payload))
            self.events.publish(BusinessEvent.create("content_processing.ready_for_teaching", payload={"job_id": str(job.id), "evaluation_id": str(evaluation.id)}))
        self.audit.record_action(
            actor=actor, institution=job.resource.institution or job.resource.subject.institution,
            action=event_name, target_type="teaching_readiness_evaluation",
            target_id=str(evaluation.id), target_display=job.resource.title,
            metadata={"resource_id": str(evaluation.resource_id), "decision": evaluation.decision,
                      "policy_version": evaluation.policy_version, "blocker_count": evaluation.blocker_count},
        )


class InvalidateTeachingReadinessService:
    def __init__(self, events=None, audit=None):
        self.events = events or EventPublisher()
        self.audit = audit or AuditService(event_publisher=self.events)

    def invalidate(self, *, resource_id, reason, actor=None):
        if not (reason or "").strip():
            raise ValidationError("READINESS_INVALIDATION_REASON_REQUIRED")
        with transaction.atomic():
            evaluation = TeachingReadinessEvaluation.objects.select_for_update().filter(
                resource_id=resource_id, decision=TeachingReadinessDecision.READY,
                invalidated_at__isnull=True,
            ).order_by("-evaluated_at").first()
            if evaluation is None:
                return None
            evaluation.invalidated_at, evaluation.invalidation_reason = timezone.now(), reason
            evaluation.save(update_fields=["invalidated_at", "invalidation_reason"])
            job = ContentProcessingJob.objects.select_for_update().get(id=evaluation.processing_job_id)
            if job.status == JobStatus.READY_FOR_TEACHING:
                job.status = JobStatus.READY_FOR_REVIEW
                job.progress = 98
                job.transition_version += 1
                job.last_transition_at = timezone.now()
                job.save()
            transaction.on_commit(lambda: self._after_commit(evaluation, job, actor))
        return evaluation

    def _after_commit(self, evaluation, job, actor):
        payload = {
            "evaluation_id": str(evaluation.id), "resource_id": str(evaluation.resource_id),
            "processing_job_id": str(evaluation.processing_job_id),
            "invalidation_reason": evaluation.invalidation_reason,
        }
        self.events.publish(BusinessEvent.create("teaching_readiness.invalidated", payload=payload))
        self.events.publish(BusinessEvent.create("resource.teaching_readiness_revoked", payload=payload))
        self.audit.record_action(
            actor=actor, institution=job.resource.institution or job.resource.subject.institution,
            action="teaching_readiness.invalidated", target_type="teaching_readiness_evaluation",
            target_id=str(evaluation.id), target_display=job.resource.title,
            metadata={"reason": evaluation.invalidation_reason, "resource_id": str(evaluation.resource_id)},
        )
