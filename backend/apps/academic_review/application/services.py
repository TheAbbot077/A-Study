from __future__ import annotations

import hashlib
import json
import re

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academic_review.domain.models import (
    ApprovedConcept, ApprovedProposalProjection, ApprovedSection, FindingResolutionType,
    ItemDecisionType, ProposalBulkDecision, ProposalFindingResolution, ProposalItemDecision,
    ProposalItemEdit, ProposalOverride, ProposalReviewSession, ProposalReviewSummary,
    ReviewItemType, ReviewSessionStatus,
)
from apps.academic_review.infrastructure.persistence import DjangoAcademicReviewRepository
from apps.audit.services.audit_service import AuditService
from apps.content_processing.application.proposal_services import RejectProposalService
from apps.content_processing.domain.proposal import ProposalDecision, ProposalReviewState
from apps.content_processing.domain.models import AttemptStatus, AttemptTrigger, JobStatus, ProcessingAttempt, ProcessingStage
from apps.content_processing.infrastructure.celery.tasks import process_content_processing_stage_task
from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import InstitutionMembership, InstitutionRole


REVIEW_POLICY_VERSION = "6d1-review-policy-1"
PROJECTION_VERSION = "6d1-approved-projection-1"
BULK_POLICIES = {
    "reject_toc": {"roles": {"table_of_contents"}, "types": {"toc_entry"}},
    "reject_front_matter": {"roles": {"front_matter"}, "types": set()},
    "reject_page_markers": {"roles": {"page_marker", "header", "footer"}, "types": {"page_number"}},
    "reject_heading_only_concepts": {"roles": set(), "types": {"heading_only"}},
    "reject_synthetic_navigation": {"roles": {"navigation"}, "types": {"navigation", "synthetic"}},
}


def create_automatic_projection(proposal):
    """Create the immutable all-items projection for a policy-approved proposal."""
    existing = ApprovedProposalProjection.objects.filter(proposal=proposal).order_by("-created_at").first()
    if existing:
        return existing
    payload = []
    sections = list(proposal.proposed_sections.order_by("ordering"))
    concepts = list(proposal.proposed_concepts.select_related("proposed_section").order_by("proposed_section__ordering", "ordering"))
    for section in sections: payload.append(("section", str(section.id), section.title, section.ordering))
    for concept in concepts: payload.append(("concept", str(concept.id), concept.title, concept.ordering, str(concept.proposed_section_id)))
    checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    with transaction.atomic():
        approval_version = hashlib.sha256(f"automatic:{proposal.proposal_version}:{checksum}".encode()).hexdigest()
        projection = ApprovedProposalProjection.objects.create(proposal=proposal, proposal_checksum=proposal.result_checksum, approval_version=approval_version, projection_version=PROJECTION_VERSION, resource=proposal.resource, subject=proposal.resource.subject, institution=proposal.resource.institution or proposal.resource.subject.institution, status="ready_for_population", checksum=checksum, hierarchy_checksum=checksum, concepts_checksum=checksum, provenance_checksum=checksum)
        section_map = {}
        for section in sections:
            approved = ApprovedSection.objects.create(projection=projection, source=section, title=section.title, canonical_title=section.normalized_title, ordering=section.ordering, page_range={"start": section.source_page_start, "end": section.source_page_end})
            section_map[section.id] = approved
        for concept in concepts:
            ApprovedConcept.objects.create(projection=projection, source=concept, section=section_map[concept.proposed_section_id], title=concept.title, canonical_title=concept.normalized_title, ordering=concept.ordering, supporting_text=concept.supporting_text, explanation=concept.explanation, page_range={"start": concept.source_page_start, "end": concept.source_page_end})
    return projection


def _has_role(user, proposal, roles):
    if user.is_superuser:
        return True
    institution_id = proposal.resource.institution_id or proposal.resource.subject.institution_id
    return InstitutionMembership.objects.filter(user=user, institution_id=institution_id, is_active=True, role__in=roles).exists()


def ensure_reviewer(user, proposal):
    if not _has_role(user, proposal, {InstitutionRole.REVIEWER, InstitutionRole.ADMINISTRATOR, InstitutionRole.INSTITUTION_OWNER, InstitutionRole.SYSTEM_ADMINISTRATOR}):
        raise PermissionDenied("Academic reviewer access is required.")


def ensure_approver(user, proposal):
    if not (user.is_staff or _has_role(user, proposal, {InstitutionRole.ADMINISTRATOR, InstitutionRole.INSTITUTION_OWNER, InstitutionRole.SYSTEM_ADMINISTRATOR})):
        raise PermissionDenied("Academic administrator access is required.")


class ProposalReviewQueryService:
    def summary(self, session):
        decisions = session.item_decisions.values_list("item_type", "decision")
        counts = {(item, decision): 0 for item in ReviewItemType.values for decision in ItemDecisionType.values}
        for item, decision in decisions:
            counts[(item, decision)] += 1
        blocking = session.proposal.validations.filter(passed=False, severity="blocking").count()
        resolved = session.finding_resolutions.filter(validation__passed=False, validation__severity="blocking").count()
        outstanding = max(blocking - resolved, 0)
        pending = counts[(ReviewItemType.SECTION, ItemDecisionType.PENDING)] + counts[(ReviewItemType.CONCEPT, ItemDecisionType.PENDING)]
        return ProposalReviewSummary(
            section_accepted=sum(counts[(ReviewItemType.SECTION, state)] for state in (ItemDecisionType.ACCEPTED, ItemDecisionType.EDITED, ItemDecisionType.MOVED)),
            section_rejected=counts[(ReviewItemType.SECTION, ItemDecisionType.REJECTED)], section_pending=counts[(ReviewItemType.SECTION, ItemDecisionType.PENDING)],
            concept_accepted=sum(counts[(ReviewItemType.CONCEPT, state)] for state in (ItemDecisionType.ACCEPTED, ItemDecisionType.EDITED, ItemDecisionType.MOVED)),
            concept_rejected=counts[(ReviewItemType.CONCEPT, ItemDecisionType.REJECTED)], concept_pending=counts[(ReviewItemType.CONCEPT, ItemDecisionType.PENDING)],
            blocking_findings=blocking, resolved_findings=resolved, outstanding_findings=outstanding,
            overrides=session.overrides.count(), ready=pending == 0 and outstanding == 0 and self.relationships_valid(session),
        )

    def relationships_valid(self, session):
        accepted_sections = set(session.item_decisions.filter(item_type=ReviewItemType.SECTION).exclude(decision__in=[ItemDecisionType.PENDING, ItemDecisionType.REJECTED]).values_list("proposed_section_id", flat=True))
        concepts = session.item_decisions.filter(item_type=ReviewItemType.CONCEPT).exclude(decision__in=[ItemDecisionType.PENDING, ItemDecisionType.REJECTED]).select_related("proposed_concept", "edit")
        for decision in concepts:
            target = getattr(getattr(decision, "edit", None), "target_section_id", None) or decision.proposed_concept.proposed_section_id
            if target not in accepted_sections:
                return False
        return True

    def outline(self, session):
        by_section = {decision.proposed_section_id: decision for decision in session.item_decisions.filter(item_type=ReviewItemType.SECTION).select_related("proposed_section", "edit")}
        concepts = session.item_decisions.filter(item_type=ReviewItemType.CONCEPT).select_related("proposed_concept", "edit").order_by("proposed_concept__ordering")
        concept_map = {}
        for decision in concepts:
            concept_map.setdefault(decision.proposed_concept.proposed_section_id, []).append(decision)
        result = []
        for section in session.proposal.proposed_sections.select_related("hierarchy_node").order_by("ordering"):
            decision = by_section[section.id]
            result.append({"decision": decision, "section": section, "concepts": concept_map.get(section.id, [])})
        return result


class AcademicReviewService:
    def __init__(self, repository=None, events=None, audit=None):
        self.repository = repository or DjangoAcademicReviewRepository()
        self.events = events or EventPublisher()
        self.audit = audit or AuditService(event_publisher=self.events)
        self.queries = ProposalReviewQueryService()

    @transaction.atomic
    def start(self, proposal, actor):
        ensure_reviewer(actor, proposal)
        if proposal.review_state not in {ProposalReviewState.READY_FOR_REVIEW, ProposalReviewState.UNDER_REVIEW}:
            raise ValidationError("Only a proposal ready for review may be opened.")
        current = self.repository.current_for_proposal(proposal.id)
        if current and current.status not in {ReviewSessionStatus.SUPERSEDED, ReviewSessionStatus.ABANDONED, ReviewSessionStatus.REJECTED, ReviewSessionStatus.REPROCESS_REQUESTED}:
            return current
        session = ProposalReviewSession.objects.create(proposal=proposal, proposal_version=proposal.proposal_version, proposal_checksum=proposal.result_checksum, opened_by=actor)
        session.start(actor); session.save(update_fields=["status", "reviewer", "updated_at"])
        ProposalItemDecision.objects.bulk_create([
            *[ProposalItemDecision(session=session, item_type=ReviewItemType.SECTION, proposed_section=item) for item in proposal.proposed_sections.all()],
            *[ProposalItemDecision(session=session, item_type=ReviewItemType.CONCEPT, proposed_concept=item) for item in proposal.proposed_concepts.all()],
        ])
        if proposal.review_state == ProposalReviewState.READY_FOR_REVIEW:
            proposal.begin_review(); proposal.save(update_fields=["review_state"])
        self._record(session, actor, "academic_review.started", "academic_review.started")
        return session

    @transaction.atomic
    def decide(self, session_id, decision_id, actor, decision, reason=""):
        session = self.repository.get(session_id, for_update=True); ensure_reviewer(actor, session.proposal); self._ensure_editable(session)
        item = session.item_decisions.select_for_update().get(id=decision_id)
        item.decision = decision; item.decided_by = actor; item.reason = reason; item.decided_at = timezone.now(); item.save()
        session.version += 1; session.save(update_fields=["version", "updated_at"])
        self._record(session, actor, "academic_review.item_decided", "academic_review.item_decided", {"decision_id": item.id, "decision": decision})
        return item

    @transaction.atomic
    def edit(self, session_id, decision_id, actor, *, title="", ordering=None, parent_section=None, target_section=None, reason=""):
        session = self.repository.get(session_id, for_update=True); ensure_reviewer(actor, session.proposal); self._ensure_editable(session)
        item = session.item_decisions.select_for_update().select_related("proposed_concept").get(id=decision_id)
        if target_section and not session.item_decisions.filter(item_type=ReviewItemType.SECTION, proposed_section=target_section).exclude(decision__in=[ItemDecisionType.PENDING, ItemDecisionType.REJECTED]).exists():
            raise ValidationError("Concepts may only move to accepted sections.")
        edit, _ = ProposalItemEdit.objects.update_or_create(decision=item, defaults={"title": title, "ordering": ordering, "parent_section": parent_section, "target_section": target_section, "edited_by": actor, "reason": reason})
        item.decision = ItemDecisionType.MOVED if target_section or parent_section else ItemDecisionType.EDITED
        item.decided_by = actor; item.decided_at = timezone.now(); item.reason = reason; item.save()
        session.version += 1; session.save(update_fields=["version", "updated_at"])
        self._record(session, actor, "academic_review.item_edited", "academic_review.item_edited", {"decision_id": item.id})
        return edit

    def preview_bulk(self, session, policy_code):
        if policy_code not in BULK_POLICIES:
            raise ValidationError("Unknown academic review bulk policy.")
        matches = [decision.id for decision in session.item_decisions.filter(decision=ItemDecisionType.PENDING).select_related("proposed_section__hierarchy_node", "proposed_concept__semantic_segment") if self._matches_policy(decision, policy_code)]
        return {"policy_code": policy_code, "affected_count": len(matches), "decision_ids": matches}

    @transaction.atomic
    def apply_bulk(self, session_id, policy_code, actor):
        session = self.repository.get(session_id, for_update=True); ensure_reviewer(actor, session.proposal); self._ensure_editable(session)
        preview = self.preview_bulk(session, policy_code)
        session.item_decisions.filter(id__in=preview["decision_ids"]).update(decision=ItemDecisionType.REJECTED, decided_by=actor, decided_at=timezone.now(), reason=f"Rejected by {policy_code} policy.")
        bulk = ProposalBulkDecision.objects.create(session=session, policy_code=policy_code, policy_version=REVIEW_POLICY_VERSION, affected_count=preview["affected_count"], preview=preview, applied_by=actor)
        session.version += 1; session.save(update_fields=["version", "updated_at"])
        self._record(session, actor, "academic_review.bulk_action", "academic_review.bulk_action", {"bulk_id": bulk.id, **preview})
        return bulk

    @transaction.atomic
    def resolve_finding(self, session_id, validation, actor, resolution_type, *, item_decision=None, note="", override_reason=""):
        session = self.repository.get(session_id, for_update=True); ensure_reviewer(actor, session.proposal); self._ensure_editable(session)
        override = None
        if resolution_type == FindingResolutionType.OVERRIDE:
            ensure_approver(actor, session.proposal)
            if not override_reason.strip(): raise ValidationError("An override reason is required.")
            override = ProposalOverride.objects.create(session=session, validation=validation, overridden_by=actor, reason=override_reason, policy_version=REVIEW_POLICY_VERSION)
            self._record(session, actor, "academic_review.override", "academic_review.override", {"validation_id": validation.id})
        resolution = ProposalFindingResolution.objects.create(session=session, validation=validation, resolution_type=resolution_type, item_decision=item_decision, override=override, resolved_by=actor, note=note)
        session.version += 1; session.save(update_fields=["version", "updated_at"])
        return resolution

    @transaction.atomic
    def submit(self, session_id, actor):
        session = self.repository.get(session_id, for_update=True); ensure_reviewer(actor, session.proposal); self._ensure_current(session)
        if not self.queries.summary(session).ready: raise ValidationError("All required items and blocking findings must be resolved before submission.")
        session.submit(); session.save(update_fields=["status", "submitted_at", "version", "updated_at"])
        self._record(session, actor, "academic_review.submitted", "academic_review.submitted")
        return session

    @transaction.atomic
    def approve(self, session_id, actor):
        raise ValidationError("Approval requires a durable PI-6D.2 readiness snapshot.")

    @transaction.atomic
    def reject(self, session_id, actor, reason):
        session = self.repository.get(session_id, for_update=True); ensure_approver(actor, session.proposal)
        session.reject(); session.save(update_fields=["status", "closed_at", "updated_at"]); RejectProposalService().reject(session.proposal, actor, reason)
        self._record(session, actor, "academic_review.rejected", "academic_review.rejected", {"reason": reason})
        return session

    @transaction.atomic
    def request_reprocessing(self, session_id, actor, reason):
        session = self.repository.get(session_id, for_update=True); ensure_reviewer(actor, session.proposal)
        session.request_reprocessing(); session.save(update_fields=["status", "closed_at", "updated_at"])
        session.proposal.supersede(); session.proposal.save(update_fields=["review_state", "decision", "population_state"])
        job = session.proposal.job
        next_number = job.active_attempt_number + 1
        attempt = ProcessingAttempt.objects.create(job=job, attempt_number=next_number, trigger=AttemptTrigger.FULL_REPROCESS, restart_stage=ProcessingStage.INSPECTING, status=AttemptStatus.PENDING, correlation_id=f"academic-review-reprocess:{session.id}", initiated_by_actor=actor)
        job.status = JobStatus.ACTIVE; job.current_stage = ProcessingStage.QUEUED; job.progress = job.STAGE_PROGRESS[ProcessingStage.QUEUED]
        job.active_attempt_number = next_number; job.failure = {}; job.completed_at = None; job.cancellation_requested = False; job.last_transition_at = timezone.now(); job.transition_version += 1; job.save()
        from apps.content_processing.application.services import LegacyImportProjectionService
        LegacyImportProjectionService().project(job)
        self._record(session, actor, "academic_review.reprocessing_requested", "academic_review.reprocessing_requested", {"reason": reason})
        transaction.on_commit(lambda: process_content_processing_stage_task.delay(str(job.id), str(attempt.id), ProcessingStage.INSPECTING, attempt.correlation_id))
        return session

    def _matches_policy(self, decision, policy_code):
        policy = BULK_POLICIES[policy_code]
        if decision.item_type == ReviewItemType.SECTION:
            node = decision.proposed_section.hierarchy_node
            evidence = decision.proposed_section.evidence or {}
            title = decision.proposed_section.title.strip()
            if policy_code == "reject_page_markers" and re.fullmatch(r"(?:\d+|[ivxlcdm]{1,8})", title, re.I): return True
            if policy_code == "reject_synthetic_navigation" and re.search(r"(?:\.\s*){3,}.*(?:\d+|[ivxlcdm]+)\s*$", title, re.I): return True
            return node.structural_role in policy["roles"] or evidence.get("classification") in policy["types"]
        evidence = decision.proposed_concept.evidence or {}; warnings = decision.proposed_concept.warnings or []; metadata = decision.proposed_concept.semantic_segment.metadata or {}
        return (policy_code == "reject_heading_only_concepts" and bool(metadata.get("heading_only"))) or evidence.get("classification") in policy["types"] or any(item.get("code") in policy["types"] for item in warnings if isinstance(item, dict))

    def _ensure_current(self, session):
        if session.proposal.result_checksum != session.proposal_checksum or session.proposal.proposal_version != session.proposal_version:
            raise ValidationError("The proposal version has changed; this review is stale.")
        newer = session.proposal.job.academic_import_proposals.exclude(id=session.proposal_id).filter(created_at__gt=session.proposal.created_at).exists()
        if newer: raise ValidationError("A newer processing proposal supersedes this review.")

    def _ensure_editable(self, session):
        self._ensure_current(session)
        if session.status != ReviewSessionStatus.IN_PROGRESS: raise ValidationError("Only an in-progress review may be edited.")

    def _record(self, session, actor, event_name, action, metadata=None):
        payload = {"session_id": str(session.id), "proposal_id": str(session.proposal_id), **(metadata or {})}
        self.events.publish(BusinessEvent.create(event_name, payload=payload))
        self.audit.record_action(actor=actor, institution=session.proposal.resource.institution, action=action, target_type="academic_review_session", target_id=str(session.id), target_display=session.proposal.resource.title, metadata=payload)
