from __future__ import annotations

from dataclasses import asdict, dataclass

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.academic.services.population_gateway import (
    DjangoAcademicPopulationGateway, PopulateConceptSpecification,
    PopulateSectionSpecification,
)
from apps.academic_review.application.approval_services import stable_checksum
from apps.academic_review.application.services import ensure_approver
from apps.academic_review.domain.models import (
    AcademicPopulationRun, ApprovalProjectionStatus, ConceptPopulationMapping,
    PopulationRunStatus, SectionPopulationMapping,
)
from apps.academic_review.infrastructure.persistence import DjangoApprovedProjectionRepository
from apps.core.events import BusinessEvent, EventPublisher


@dataclass(frozen=True)
class PopulationBlocker:
    code: str
    message: str


@dataclass(frozen=True)
class PopulationReadinessResult:
    approved_projection_id: str
    status: str
    ready: bool
    expected_section_count: int
    expected_concept_count: int
    existing_population_run_id: str | None
    blockers: tuple[PopulationBlocker, ...]


@dataclass(frozen=True)
class PopulationPlan:
    approved_projection_id: str
    approval_decision_id: str
    projection_fingerprint: str
    resource_id: str
    subject_id: str
    conflict_policy: str
    sections: tuple[dict, ...]
    concepts: tuple[dict, ...]
    expected_section_count: int
    expected_concept_count: int

    def snapshot(self):
        return asdict(self)


@dataclass(frozen=True)
class PopulationResult:
    population_run_id: str
    approved_projection_id: str
    status: str
    resource_id: str
    created_sections: int
    matched_sections: int
    created_concepts: int
    matched_concepts: int
    failed_items: int
    populated_at: object
    replayed: bool = False


class BuildPopulationPlanService:
    version = "6d3-population-plan-1"

    def build(self, projection):
        approved_sections = list(projection.sections.all())
        approved_concepts = list(projection.concepts.all())
        if any(item.projection_id != projection.id for item in approved_sections) or any(
            item.projection_id != projection.id or item.section.projection_id != projection.id
            for item in approved_concepts
        ):
            raise ValidationError("The approved projection graph is malformed.", code="projection_integrity_failed")
        hierarchy = [{
            "source_id": item.source_id, "title": item.title,
            "canonical_title": item.canonical_title, "ordinal": item.ordering,
            "parent_source_id": item.parent_source_id, "depth": item.depth,
        } for item in sorted(approved_sections, key=lambda row: (row.ordering, row.id))]
        concepts_material = [{
            "source_id": item.source_id, "section_source_id": item.section.source_id,
            "title": item.title, "canonical_title": item.canonical_title,
            "ordinal": item.ordering,
        } for item in sorted(approved_concepts, key=lambda row: (row.section.ordering, row.ordering, row.id))]
        provenance = [{
            "source_id": str(item.source_id), "decision_id": item.review_decision_id,
            "edit_id": item.edit_reference_id, "override_references": item.override_references,
            "evidence": item.evidence_references,
        } for item in sorted(approved_sections, key=lambda row: (row.ordering, row.id))]
        provenance += [{
            "source_id": str(item.source_id), "decision_id": item.review_decision_id,
            "edit_id": item.edit_reference_id, "override_references": item.override_references,
            "evidence": item.supporting_evidence,
        } for item in sorted(approved_concepts, key=lambda row: (row.section.ordering, row.ordering, row.id))]
        if stable_checksum({"hierarchy": hierarchy, "concepts": concepts_material, "provenance": provenance}) != projection.checksum:
            raise ValidationError("The approved projection fingerprint no longer matches its contents.", code="projection_integrity_failed")
        sections = tuple({
            "approved_section_id": str(item.id),
            "stable_source_key": f"approved-projection:{projection.id}:section:{item.id}",
            "title": item.title,
            "description": "",
            "sequence_number": item.ordering,
            "source_provenance": {
                "source_id": str(item.source_id), "page_range": item.page_range,
                "evidence_references": item.evidence_references,
            },
        } for item in sorted(approved_sections, key=lambda row: (row.ordering, row.id)))
        section_keys = {item.id: row["stable_source_key"] for item, row in zip(sorted(approved_sections, key=lambda item: (item.ordering, item.id)), sections)}
        concepts = []
        for item in sorted(approved_concepts, key=lambda row: (row.section.ordering, row.ordering, row.id)):
            if item.section_id not in section_keys or item.projection_id != projection.id or item.section.projection_id != projection.id:
                raise ValidationError("The approved projection graph is malformed.", code="projection_integrity_failed")
            concepts.append({
                "approved_concept_id": str(item.id),
                "stable_source_key": f"approved-projection:{projection.id}:concept:{item.id}",
                "parent_section_source_key": section_keys[item.section_id],
                "title": item.title, "description": item.supporting_text,
                "learning_objective": item.explanation, "sequence_number": item.ordering,
                "source_provenance": {
                    "source_id": str(item.source_id), "page_range": item.page_range,
                    "supporting_evidence": item.supporting_evidence,
                },
            })
        return PopulationPlan(
            approved_projection_id=str(projection.id),
            approval_decision_id=str(projection.approval_decision_id),
            projection_fingerprint=projection.checksum,
            resource_id=str(projection.resource_id), subject_id=str(projection.subject_id),
            conflict_policy="provenance_only_no_fuzzy_matching", sections=sections,
            concepts=tuple(concepts), expected_section_count=len(sections),
            expected_concept_count=len(concepts),
        )


class EvaluatePopulationReadinessService:
    def __init__(self, projections=None, gateway=None, plans=None):
        self.projections = projections or DjangoApprovedProjectionRepository()
        self.gateway = gateway or DjangoAcademicPopulationGateway()
        self.plans = plans or BuildPopulationPlanService()

    def execute(self, projection_id, actor):
        projection = self.projections.get(projection_id)
        ensure_approver(actor, projection.proposal)
        blockers = []
        if not projection.approval_decision_id or projection.approval_decision.decision not in {"approved", "approved_with_edits"}:
            blockers.append(PopulationBlocker("PROJECTION_NOT_APPROVED", "The projection has no approved decision lineage."))
        if projection.status != ApprovalProjectionStatus.READY_FOR_POPULATION:
            blockers.append(PopulationBlocker("PROJECTION_NOT_READY", "The projection is not ready for population."))
        if not projection.resource_id or not projection.subject_id or not self.gateway.validate_target(resource_id=projection.resource_id, subject_id=projection.subject_id):
            blockers.append(PopulationBlocker("INVALID_ACADEMIC_TARGET", "The target resource or subject is invalid."))
        existing = AcademicPopulationRun.objects.filter(approved_projection=projection, status=PopulationRunStatus.POPULATED).first()
        if existing:
            blockers.append(PopulationBlocker("ALREADY_POPULATED", "This projection has already populated academic truth."))
        try:
            plan = self.plans.build(projection)
        except ValidationError:
            plan = None
            blockers.append(PopulationBlocker("PROJECTION_INTEGRITY_FAILED", "The immutable projection graph is invalid."))
        return PopulationReadinessResult(
            str(projection.id), projection.status, not blockers,
            plan.expected_section_count if plan else 0, plan.expected_concept_count if plan else 0,
            str(existing.id) if existing else None, tuple(blockers),
        )


class PopulateApprovedProjectionService:
    def __init__(self, projections=None, gateway=None, plans=None, events=None):
        self.projections = projections or DjangoApprovedProjectionRepository()
        self.gateway = gateway or DjangoAcademicPopulationGateway()
        self.plans = plans or BuildPopulationPlanService()
        self.events = events or EventPublisher()

    def execute(self, projection_id, actor, *, expected_fingerprint, idempotency_key):
        key = (idempotency_key or "").strip()
        fingerprint = (expected_fingerprint or "").strip()
        if not key or not fingerprint:
            raise ValidationError("Idempotency key and expected projection fingerprint are required.")
        projection = self.projections.get(projection_id)
        ensure_approver(actor, projection.proposal)
        request_fingerprint = stable_checksum({"projection_id": str(projection_id), "expected_fingerprint": fingerprint})
        replay = AcademicPopulationRun.objects.filter(idempotency_key=key).first()
        if replay:
            if replay.request_fingerprint != request_fingerprint:
                raise ValidationError("The idempotency key was used for different material input.", code="population_conflict")
            if replay.status == PopulationRunStatus.POPULATED:
                return self._result(replay, replayed=True)
            raise ValidationError("A failed attempt is immutable; retry with a new idempotency key.", code="population_conflict")
        if projection.checksum != fingerprint:
            raise ValidationError("The approved projection fingerprint is stale.", code="projection_version_conflict")
        if AcademicPopulationRun.objects.filter(approved_projection=projection, status=PopulationRunStatus.POPULATED).exists():
            raise ValidationError("The approved projection has already been populated.", code="population_conflict")
        readiness = EvaluatePopulationReadinessService(self.projections, self.gateway, self.plans).execute(projection_id, actor)
        if not readiness.ready:
            raise ValidationError([blocker.code for blocker in readiness.blockers], code="projection_not_ready")
        plan = self.plans.build(projection)
        try:
            return self._execute_atomic(projection_id, actor, key, request_fingerprint, plan)
        except ValidationError as exc:
            self._record_failure(projection, actor, key, request_fingerprint, plan, getattr(exc, "code", None) or "ACADEMIC_POPULATION_FAILED")
            raise

    @transaction.atomic
    def _execute_atomic(self, projection_id, actor, key, request_fingerprint, plan):
        projection = self.projections.get_for_population(projection_id)
        if projection.status != ApprovalProjectionStatus.READY_FOR_POPULATION or projection.checksum != plan.projection_fingerprint:
            raise ValidationError("The projection changed before population.", code="projection_version_conflict")
        if AcademicPopulationRun.objects.filter(approved_projection=projection, status=PopulationRunStatus.POPULATED).exists():
            raise ValidationError("The approved projection has already been populated.", code="population_conflict")
        run = AcademicPopulationRun.objects.create(
            approved_projection=projection, approval_decision=projection.approval_decision,
            resource=projection.resource, subject=projection.subject, requested_by=actor,
            idempotency_key=key, request_fingerprint=request_fingerprint,
            projection_fingerprint=projection.checksum, plan_snapshot=plan.snapshot(),
        )
        run.start()
        run.save(update_fields=["status", "started_at", "version", "updated_at"])
        type(projection).objects.filter(pk=projection.pk).update(status=ApprovalProjectionStatus.POPULATING)
        section_ids = {}
        created_sections = created_concepts = 0
        for row in plan.sections:
            result = self.gateway.populate_section(
                resource_id=projection.resource_id,
                specification=PopulateSectionSpecification(
                    row["stable_source_key"], row["title"], row["description"], row["sequence_number"],
                ),
            )
            section_ids[row["stable_source_key"]] = result.academic_id
            SectionPopulationMapping.objects.create(
                population_run=run, approved_section_id=row["approved_section_id"],
                academic_section_id=result.academic_id, stable_source_key=row["stable_source_key"],
                outcome=result.outcome, sequence_number=row["sequence_number"],
            )
            created_sections += result.outcome == "created"
        for row in plan.concepts:
            result = self.gateway.populate_concept(
                academic_section_id=section_ids[row["parent_section_source_key"]],
                specification=PopulateConceptSpecification(
                    row["stable_source_key"], row["parent_section_source_key"], row["title"],
                    row["description"], row["learning_objective"], row["sequence_number"],
                ),
            )
            ConceptPopulationMapping.objects.create(
                population_run=run, approved_concept_id=row["approved_concept_id"],
                academic_concept_id=result.academic_id,
                academic_section_id=section_ids[row["parent_section_source_key"]],
                stable_source_key=row["stable_source_key"], outcome=result.outcome,
                sequence_number=row["sequence_number"],
            )
            created_concepts += result.outcome == "created"
        run.complete(
            created_sections=created_sections, matched_sections=len(plan.sections) - created_sections,
            created_concepts=created_concepts, matched_concepts=len(plan.concepts) - created_concepts,
        )
        run.save()
        type(projection).objects.filter(pk=projection.pk).update(status=ApprovalProjectionStatus.POPULATED)
        payload = {
            "population_run_id": str(run.id), "approved_projection_id": str(projection.id),
            "approval_decision_id": str(projection.approval_decision_id),
            "resource_id": str(projection.resource_id), "subject_id": str(projection.subject_id),
            "created_sections": run.created_section_count, "matched_sections": run.matched_section_count,
            "created_concepts": run.created_concept_count, "matched_concepts": run.matched_concept_count,
            "requested_by": str(actor.id),
        }
        transaction.on_commit(lambda: [
            self.events.publish(BusinessEvent.create(name, payload=payload))
            for name in ("academic_population.planned", "academic_population.started", "academic_population.completed", "approved_proposal.populated")
        ])
        return self._result(run)

    def _record_failure(self, projection, actor, key, request_fingerprint, plan, code):
        if AcademicPopulationRun.objects.filter(idempotency_key=key).exists():
            return
        run = AcademicPopulationRun(
            approved_projection=projection, approval_decision=projection.approval_decision,
            resource=projection.resource, subject=projection.subject, requested_by=actor,
            idempotency_key=key, request_fingerprint=request_fingerprint,
            projection_fingerprint=projection.checksum, plan_snapshot=plan.snapshot(),
        )
        run.fail(code=str(code).upper(), message="Academic population did not complete.")
        run.save()
        self.events.publish(BusinessEvent.create("academic_population.failed", payload={
            "population_run_id": str(run.id), "approved_projection_id": str(projection.id),
            "failure_code": run.failure_code, "requested_by": str(actor.id),
        }))

    @staticmethod
    def _result(run, replayed=False):
        return PopulationResult(
            str(run.id), str(run.approved_projection_id), run.status, str(run.resource_id),
            run.created_section_count, run.matched_section_count, run.created_concept_count,
            run.matched_concept_count, 0, run.completed_at, replayed,
        )
