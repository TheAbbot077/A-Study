from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict, dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.academic_review.application.services import ensure_approver
from apps.academic_review.domain.models import (
    ApprovalDecision, ApprovalProjectionStatus, ApprovalReadinessSnapshot,
    ApprovedConcept, ApprovedProposalProjection, ApprovedSection, ItemDecisionType,
    ReviewItemType, ReviewSessionStatus,
)
from apps.academic_review.infrastructure.persistence import (
    DjangoAcademicReviewRepository, DjangoApprovalDecisionRepository,
    DjangoApprovalReadinessRepository, DjangoApprovedConceptRepository,
    DjangoApprovedProjectionRepository, DjangoApprovedSectionRepository,
)
from apps.audit.services.audit_service import AuditService
from apps.content_processing.domain.proposal import ProposalDecisionType
from apps.core.events import BusinessEvent, EventPublisher


APPROVAL_POLICY_VERSION = "6d2-approval-policy-1"
APPROVED_PROJECTION_VERSION = "6d2-approved-projection-1"
_LEADER = re.compile(r"(?:\.\s*){3,}.*(?:\d+|[ivxlcdm]+)\s*$", re.I)
_PAGE_MARKER = re.compile(r"^(?:page\s+)?(?:\d+|[ivxlcdm]{1,8})$", re.I)
_INELIGIBLE_ROLES = {"front_matter", "navigation", "table_of_contents", "title_page", "copyright", "boilerplate", "probable_noise"}


def canonical_title(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value or "").strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"^(?:\d+(?:\.\d+)*[.)]?\s+)", "", normalized)
    normalized = re.sub(r"(?:\.\s*){3,}\s*(?:\d+|[ivxlcdm]+)\s*$", "", normalized, flags=re.I)
    return normalized.casefold().strip(" .:-")


def stable_checksum(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


@dataclass(frozen=True)
class ApprovalReadinessResult:
    ready: bool
    pending_sections: int
    pending_concepts: int
    accepted_sections: int
    accepted_concepts: int
    rejected_sections: int
    rejected_concepts: int
    blocking_findings: int
    resolved_findings: int
    orphan_concepts: int
    invalid_hierarchy: int
    duplicate_titles: int
    override_count: int
    reasons: tuple[str, ...]


class ApprovalReadinessPolicy:
    version = APPROVAL_POLICY_VERSION

    def evaluate(self, context) -> ApprovalReadinessResult:
        session, decisions = context["session"], context["decisions"]
        sections = [item for item in decisions if item.item_type == ReviewItemType.SECTION]
        concepts = [item for item in decisions if item.item_type == ReviewItemType.CONCEPT]
        accepted_states = {ItemDecisionType.ACCEPTED, ItemDecisionType.EDITED, ItemDecisionType.MOVED}
        accepted_sections = {item.proposed_section_id: item for item in sections if item.decision in accepted_states}
        source_by_node = {str(item.proposed_section.hierarchy_node_id): item.proposed_section_id for item in sections if item.decision in accepted_states}
        resolved_ids = {item.validation_id for item in context["resolutions"]}
        blocking = [item for item in context["validations"] if not item.passed and item.severity == "blocking"]
        orphan_concepts = 0
        section_titles, concept_titles = [], {}
        section_orderings, concept_orderings = [], {}
        invalid_hierarchy = 0
        for item in sections:
            if item.decision not in accepted_states:
                continue
            edit = getattr(item, "edit", None); title = edit.title if edit and edit.title else item.proposed_section.title
            section_titles.append(canonical_title(title))
            section_orderings.append(edit.ordering if edit and edit.ordering else item.proposed_section.ordering)
            parent_id = (edit.parent_section_id if edit and edit.parent_section_id else source_by_node.get(item.proposed_section.parent_reference))
            if parent_id and (parent_id not in accepted_sections or parent_id == item.proposed_section_id): invalid_hierarchy += 1
            if item.proposed_section.hierarchy_node.structural_role in _INELIGIBLE_ROLES: invalid_hierarchy += 1
            if _LEADER.search(title) or _PAGE_MARKER.fullmatch(title.strip()): invalid_hierarchy += 1
        for item in concepts:
            if item.decision not in accepted_states:
                continue
            edit = getattr(item, "edit", None); source = item.proposed_concept
            target = (edit.target_section_id if edit else None) or source.proposed_section_id
            ineligible = target not in accepted_sections
            title = edit.title if edit and edit.title else source.title
            concept_titles.setdefault(target, []).append(canonical_title(title))
            concept_orderings.setdefault(target, []).append(edit.ordering if edit and edit.ordering else source.ordering)
            ineligible = ineligible or bool((source.semantic_segment.metadata or {}).get("heading_only"))
            ineligible = ineligible or bool(_LEADER.search(title) or _PAGE_MARKER.fullmatch(title.strip()))
            if ineligible: orphan_concepts += 1
        duplicate_titles = len(section_titles) - len(set(section_titles))
        duplicate_titles += sum(len(titles) - len(set(titles)) for titles in concept_titles.values())
        invalid_hierarchy += len(section_orderings) - len(set(section_orderings))
        invalid_hierarchy += sum(len(values) - len(set(values)) for values in concept_orderings.values())
        parent_map = {}
        for item in accepted_sections.values():
            edit = getattr(item, "edit", None)
            parent_map[item.proposed_section_id] = edit.parent_section_id if edit and edit.parent_section_id else source_by_node.get(item.proposed_section.parent_reference)
        for source_id in parent_map:
            visited, current = set(), source_id
            while parent_map.get(current):
                if current in visited: invalid_hierarchy += 1; break
                visited.add(current); current = parent_map[current]
        pending_sections = sum(item.decision == ItemDecisionType.PENDING for item in sections)
        pending_concepts = sum(item.decision == ItemDecisionType.PENDING for item in concepts)
        reasons = []
        if session.status != ReviewSessionStatus.READY_FOR_APPROVAL: reasons.append("review_not_ready_for_approval")
        if pending_sections: reasons.append("pending_sections")
        if pending_concepts: reasons.append("pending_concepts")
        if len(blocking) != len([item for item in blocking if item.id in resolved_ids]): reasons.append("unresolved_blocking_findings")
        if orphan_concepts: reasons.append("orphan_or_ineligible_concepts")
        if invalid_hierarchy: reasons.append("invalid_hierarchy")
        if duplicate_titles: reasons.append("duplicate_canonical_titles")
        if session.proposal.result_checksum != session.proposal_checksum or session.proposal.proposal_version != session.proposal_version: reasons.append("proposal_version_mismatch")
        if context["newer_exists"]: reasons.append("newer_proposal_exists")
        if session.proposal.review_state in {"superseded", "archived"}: reasons.append("proposal_superseded")
        return ApprovalReadinessResult(
            ready=not reasons, pending_sections=pending_sections, pending_concepts=pending_concepts,
            accepted_sections=len(accepted_sections), accepted_concepts=sum(item.decision in accepted_states for item in concepts),
            rejected_sections=sum(item.decision == ItemDecisionType.REJECTED for item in sections),
            rejected_concepts=sum(item.decision == ItemDecisionType.REJECTED for item in concepts),
            blocking_findings=len(blocking), resolved_findings=sum(item.id in resolved_ids for item in blocking),
            orphan_concepts=orphan_concepts, invalid_hierarchy=invalid_hierarchy,
            duplicate_titles=duplicate_titles, override_count=sum(item.override_id is not None for item in context["resolutions"]),
            reasons=tuple(reasons),
        )


class EvaluateProposalApprovalReadinessService:
    def __init__(self, reviews=None, snapshots=None, policy=None, events=None, audit=None):
        self.reviews = reviews or DjangoAcademicReviewRepository(); self.snapshots = snapshots or DjangoApprovalReadinessRepository()
        self.policy = policy or ApprovalReadinessPolicy(); self.events = events or EventPublisher(); self.audit = audit or AuditService(event_publisher=self.events)

    def evaluate_context(self, context, actor):
        result = self.policy.evaluate(context); session = context["session"]
        payload = {"proposal_version": session.proposal_version, "proposal_checksum": session.proposal_checksum, "review_session_version": session.version, "policy_version": self.policy.version, **asdict(result)}
        snapshot = ApprovalReadinessSnapshot(session=session, proposal=session.proposal, evaluated_by=actor, checksum=stable_checksum(payload), **payload)
        return result, snapshot

    def execute(self, session_id, actor, expected_session_version=None):
        return self._execute_atomic(session_id, actor, expected_session_version)

    @transaction.atomic
    def _execute_atomic(self, session_id, actor, expected_session_version=None):
        context = self.reviews.approval_context(session_id, for_update=True); ensure_approver(actor, context["session"].proposal)
        if expected_session_version is not None and context["session"].version != expected_session_version: raise ValidationError("The review session version is stale.")
        result, snapshot = self.evaluate_context(context, actor)
        try:
            with transaction.atomic(): self.snapshots.add(snapshot)
        except IntegrityError:
            snapshot = self.snapshots.get_identity(session_id, snapshot.review_session_version, snapshot.checksum)
        event = "academic_review.approval_readiness_evaluated" if result.ready else "academic_review.approval_blocked"
        event_payload = {"session_id": str(session_id), "snapshot_id": str(snapshot.id), "ready": result.ready, "reasons": list(result.reasons)}
        transaction.on_commit(lambda: self.events.publish(BusinessEvent.create(event, payload=event_payload)))
        self.audit.record_action(actor=actor, institution=context["session"].proposal.resource.institution, action=event, target_type="approval_readiness_snapshot", target_id=str(snapshot.id), metadata={"policy_version": self.policy.version, "ready": result.ready, "reasons": list(result.reasons)})
        return snapshot


@dataclass(frozen=True)
class ProjectionPlan:
    sections: tuple[dict, ...]
    concepts: tuple[dict, ...]
    projection_checksum: str
    hierarchy_checksum: str
    concepts_checksum: str
    provenance_checksum: str


class DeterministicApprovedProjectionBuilder:
    def build(self, context) -> ProjectionPlan:
        accepted = {ItemDecisionType.ACCEPTED, ItemDecisionType.EDITED, ItemDecisionType.MOVED}
        decisions = context["decisions"]; section_rows = []
        global_overrides = [str(item.override_id) for item in context["resolutions"] if item.override_id and not item.item_decision_id]
        overrides_by_decision = {}
        for resolution in context["resolutions"]:
            if resolution.override_id and resolution.item_decision_id:
                overrides_by_decision.setdefault(resolution.item_decision_id, []).append(str(resolution.override_id))
        section_decisions = [item for item in decisions if item.item_type == ReviewItemType.SECTION and item.decision in accepted]
        section_decisions.sort(key=lambda item: ((getattr(item, "edit", None).ordering if getattr(item, "edit", None) and getattr(item, "edit", None).ordering else item.proposed_section.ordering), str(item.proposed_section_id)))
        order_by_source = {item.proposed_section_id: index for index, item in enumerate(section_decisions, 1)}
        source_by_node = {str(item.proposed_section.hierarchy_node_id): item.proposed_section_id for item in section_decisions}
        parent_by_source = {}
        for item in section_decisions:
            edit = getattr(item, "edit", None)
            parent_by_source[item.proposed_section_id] = edit.parent_section_id if edit and edit.parent_section_id else source_by_node.get(item.proposed_section.parent_reference)

        def depth_for(source_id):
            depth, current, visited = 1, source_id, set()
            while parent_by_source.get(current):
                if current in visited: raise ValidationError("Approved section hierarchy contains a cycle.")
                visited.add(current); current = parent_by_source[current]; depth += 1
            return depth

        for index, item in enumerate(section_decisions, 1):
            source, edit = item.proposed_section, getattr(item, "edit", None)
            title = edit.title if edit and edit.title else source.title; parent_source_id = parent_by_source[source.id]
            section_rows.append({"source_id": source.id, "decision_id": item.id, "edit_id": edit.id if edit else None, "title": title, "canonical_title": canonical_title(title), "ordinal": index, "parent_source_id": parent_source_id, "parent_ordinal": order_by_source.get(parent_source_id), "depth": depth_for(source.id), "page_range": {"start": source.source_page_start, "end": source.source_page_end}, "evidence_references": context["section_evidence"].get(str(source.id), []), "override_references": global_overrides + overrides_by_decision.get(item.id, [])})
        concept_rows = []
        for item in decisions:
            if item.item_type != ReviewItemType.CONCEPT or item.decision not in accepted: continue
            source, edit = item.proposed_concept, getattr(item, "edit", None); target = (edit.target_section_id if edit else None) or source.proposed_section_id
            if target not in order_by_source: raise ValidationError("Accepted concepts require accepted sections.")
            title = edit.title if edit and edit.title else source.title
            concept_rows.append({"source_id": source.id, "decision_id": item.id, "edit_id": edit.id if edit else None, "section_source_id": target, "section_ordinal": order_by_source[target], "source_ordering": edit.ordering if edit and edit.ordering else source.ordering, "title": title, "canonical_title": canonical_title(title), "page_range": {"start": source.source_page_start, "end": source.source_page_end}, "supporting_text": source.supporting_text, "explanation": source.explanation, "supporting_evidence": context["concept_evidence"].get(str(source.id), []), "override_references": global_overrides + overrides_by_decision.get(item.id, [])})
        concept_rows.sort(key=lambda row: (row["section_ordinal"], row["source_ordering"], str(row["source_id"])))
        per_section = {}
        for row in concept_rows: per_section[row["section_source_id"]] = per_section.get(row["section_source_id"], 0) + 1; row["ordinal"] = per_section[row["section_source_id"]]
        hierarchy = [{key: row[key] for key in ("source_id", "title", "canonical_title", "ordinal", "parent_source_id", "depth")} for row in section_rows]
        concepts = [{key: row[key] for key in ("source_id", "section_source_id", "title", "canonical_title", "ordinal")} for row in concept_rows]
        provenance = [{"source_id": str(row["source_id"]), "decision_id": row["decision_id"], "edit_id": row["edit_id"], "override_references": row["override_references"], "evidence": row["evidence_references"]} for row in section_rows] + [{"source_id": str(row["source_id"]), "decision_id": row["decision_id"], "edit_id": row["edit_id"], "override_references": row["override_references"], "evidence": row["supporting_evidence"]} for row in concept_rows]
        return ProjectionPlan(tuple(section_rows), tuple(concept_rows), stable_checksum({"hierarchy": hierarchy, "concepts": concepts, "provenance": provenance}), stable_checksum(hierarchy), stable_checksum(concepts), stable_checksum(provenance))


class ApproveReviewedProposalService:
    def __init__(self, reviews=None, readiness=None, decisions=None, projections=None, sections=None, concepts=None, builder=None, readiness_evaluator=None, events=None, audit=None):
        self.reviews = reviews or DjangoAcademicReviewRepository(); self.readiness = readiness or DjangoApprovalReadinessRepository(); self.decisions = decisions or DjangoApprovalDecisionRepository()
        self.projections = projections or DjangoApprovedProjectionRepository(); self.sections = sections or DjangoApprovedSectionRepository(); self.concepts = concepts or DjangoApprovedConceptRepository()
        self.builder = builder or DeterministicApprovedProjectionBuilder(); self.readiness_evaluator = readiness_evaluator or EvaluateProposalApprovalReadinessService(reviews=self.reviews)
        self.events = events or EventPublisher(); self.audit = audit or AuditService(event_publisher=self.events)

    def execute(self, session_id, snapshot_id, actor, idempotency_key, expected_session_version=None):
        normalized_key = (idempotency_key or "").strip()
        if not normalized_key: raise ValidationError("An idempotency key is required.")
        existing = self.decisions.get_idempotent(session_id, normalized_key)
        if existing and hasattr(existing, "projection"): return existing.projection
        return self._execute_atomic(session_id, snapshot_id, actor, normalized_key, expected_session_version)

    @transaction.atomic
    def _execute_atomic(self, session_id, snapshot_id, actor, idempotency_key, expected_session_version=None):
        context = self.reviews.approval_context(session_id, for_update=True); session = context["session"]; ensure_approver(actor, session.proposal)
        existing = self.decisions.get_idempotent(session_id, idempotency_key)
        if existing and hasattr(existing, "projection"): return existing.projection
        if expected_session_version is not None and session.version != expected_session_version: raise ValidationError("The review session version is stale.")
        snapshot = self.readiness.get(snapshot_id, for_update=True)
        if snapshot.session_id != session.id or snapshot.review_session_version != session.version or snapshot.proposal_checksum != session.proposal_checksum or snapshot.policy_version != APPROVAL_POLICY_VERSION:
            raise ValidationError("The approval readiness snapshot is stale.")
        current, transient = self.readiness_evaluator.evaluate_context(context, actor)
        if not snapshot.ready or not current.ready or transient.checksum != snapshot.checksum: raise ValidationError("The proposal is not ready for approval or the snapshot is stale.")
        plan = self.builder.build(context)
        approval_version = stable_checksum({"proposal_version": session.proposal_version, "review_session_version": session.version, "policy_version": APPROVAL_POLICY_VERSION, "projection_checksum": plan.projection_checksum})
        existing_projection = self.projections.get_by_approval_version(session.proposal_id, approval_version)
        if existing_projection: return existing_projection
        with_edits = any(item.decision in {ItemDecisionType.EDITED, ItemDecisionType.MOVED} for item in context["decisions"])
        decision_name = "approved_with_edits" if with_edits else "approved"
        decision = self.decisions.add(ApprovalDecision(session=session, proposal=session.proposal, readiness_snapshot=snapshot, decision=decision_name, approval_version=approval_version, idempotency_key=idempotency_key, decided_by=actor))
        resource = session.proposal.resource
        projection = self.projections.add(ApprovedProposalProjection(session=session, proposal=session.proposal, approval_decision=decision, proposal_checksum=session.proposal_checksum, approval_version=approval_version, projection_version=APPROVED_PROJECTION_VERSION, resource=resource, subject=resource.subject, institution=resource.institution or resource.subject.institution, status=ApprovalProjectionStatus.READY_FOR_POPULATION, approved_by=actor, checksum=plan.projection_checksum, hierarchy_checksum=plan.hierarchy_checksum, concepts_checksum=plan.concepts_checksum, provenance_checksum=plan.provenance_checksum))
        section_models = []
        for row in plan.sections:
            model = ApprovedSection(projection=projection, source_id=row["source_id"], title=row["title"], canonical_title=row["canonical_title"], ordering=row["ordinal"], depth=row["depth"], parent_source_id=row["parent_source_id"], page_range=row["page_range"], evidence_references=row["evidence_references"], review_decision_id=row["decision_id"], edit_reference_id=row["edit_id"], override_references=row["override_references"])
            section_models.append(model)
        self.sections.add_many(section_models)
        self.sections.link_parents(projection, {row["source_id"]: row["parent_source_id"] for row in plan.sections if row["parent_source_id"]})
        persisted_sections = self.sections.by_source(projection)
        self.concepts.add_many([ApprovedConcept(projection=projection, source_id=row["source_id"], section=persisted_sections[row["section_source_id"]], title=row["title"], canonical_title=row["canonical_title"], ordering=row["ordinal"], supporting_text=row["supporting_text"], explanation=row["explanation"], page_range=row["page_range"], supporting_evidence=row["supporting_evidence"], review_decision_id=row["decision_id"], edit_reference_id=row["edit_id"], override_references=row["override_references"]) for row in plan.concepts])
        self.reviews.finalize_approval(session, with_edits=with_edits)
        self.reviews.record_proposal_decision(proposal=session.proposal, decision=ProposalDecisionType.APPROVED_WITH_EDITS if with_edits else ProposalDecisionType.APPROVED, decided_by=actor, reason="Approved through PI-6D.2 reviewed projection.", metadata={"approval_decision_id": str(decision.id), "projection_id": str(projection.id), "approval_version": approval_version})
        event = "academic_review.proposal_approved_with_edits" if with_edits else "academic_review.proposal_approved"
        event_payload = {"session_id": str(session.id), "proposal_id": str(session.proposal_id), "projection_id": str(projection.id), "approval_version": approval_version}
        event_names = (event, "academic_review.approved_projection_created", "academic_review.ready_for_population")

        def publish_approval_events():
            for name in event_names: self.events.publish(BusinessEvent.create(name, payload=event_payload))
        transaction.on_commit(publish_approval_events)
        self.audit.record_action(actor=actor, institution=projection.institution, action=event, target_type="approved_proposal_projection", target_id=str(projection.id), metadata={"policy_version": APPROVAL_POLICY_VERSION, "approval_version": approval_version, "projection_checksum": projection.checksum, "override_count": snapshot.override_count, "resolved_findings": snapshot.resolved_findings})
        self.audit.record_action(actor=actor, institution=projection.institution, action="academic_review.approved_projection_created", target_type="approved_proposal_projection", target_id=str(projection.id), metadata={"approval_decision_id": str(decision.id), "hierarchy_checksum": projection.hierarchy_checksum, "concepts_checksum": projection.concepts_checksum, "provenance_checksum": projection.provenance_checksum})
        return projection


class RejectReviewedProposalService:
    def __init__(self, reviews=None, decisions=None, snapshots=None, readiness_evaluator=None, events=None, audit=None):
        self.reviews = reviews or DjangoAcademicReviewRepository(); self.decisions = decisions or DjangoApprovalDecisionRepository()
        self.snapshots = snapshots or DjangoApprovalReadinessRepository(); self.readiness_evaluator = readiness_evaluator or EvaluateProposalApprovalReadinessService(reviews=self.reviews)
        self.events = events or EventPublisher(); self.audit = audit or AuditService(event_publisher=self.events)

    def execute(self, session_id, actor, reason, idempotency_key, expected_session_version=None):
        normalized_reason = (reason or "").strip()
        if not normalized_reason: raise ValidationError("A rejection reason is required.")
        normalized_key = (idempotency_key or "").strip()
        if not normalized_key: raise ValidationError("An idempotency key is required.")
        existing = self.decisions.get_idempotent(session_id, normalized_key)
        if existing: return existing
        return self._execute_atomic(session_id, actor, normalized_reason, normalized_key, expected_session_version)

    @transaction.atomic
    def _execute_atomic(self, session_id, actor, reason, idempotency_key, expected_session_version=None):
        context = self.reviews.approval_context(session_id, for_update=True); session = context["session"]; ensure_approver(actor, session.proposal)
        existing = self.decisions.get_idempotent(session_id, idempotency_key)
        if existing: return existing
        if expected_session_version is not None and session.version != expected_session_version: raise ValidationError("The review session version is stale.")
        _, snapshot = self.readiness_evaluator.evaluate_context(context, actor)
        try:
            with transaction.atomic(): self.snapshots.add(snapshot)
        except IntegrityError:
            snapshot = self.snapshots.get_identity(session_id, snapshot.review_session_version, snapshot.checksum)
        approval_version = stable_checksum({"proposal_version": session.proposal_version, "review_session_version": session.version, "policy_version": APPROVAL_POLICY_VERSION, "decision": "rejected", "reason": reason})
        decision = self.decisions.add(ApprovalDecision(session=session, proposal=session.proposal, readiness_snapshot=snapshot, decision="rejected", approval_version=approval_version, idempotency_key=idempotency_key, reason=reason, decided_by=actor))
        self.reviews.finalize_rejection(session)
        self.reviews.record_proposal_decision(proposal=session.proposal, decision=ProposalDecisionType.REJECTED, decided_by=actor, reason=reason, metadata={"approval_decision_id": str(decision.id)})
        event_payload = {"session_id": str(session.id), "proposal_id": str(session.proposal_id), "decision_id": str(decision.id)}
        transaction.on_commit(lambda: self.events.publish(BusinessEvent.create("academic_review.proposal_rejected", payload=event_payload)))
        self.audit.record_action(actor=actor, institution=session.proposal.resource.institution, action="academic_review.proposal_rejected", target_type="approval_decision", target_id=str(decision.id), metadata={"policy_version": APPROVAL_POLICY_VERSION, "reason": reason, "override_count": snapshot.override_count, "resolved_findings": snapshot.resolved_findings})
        return decision
