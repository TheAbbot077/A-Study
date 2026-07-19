from apps.academic_review.domain.models import (
    ApprovalDecision, ApprovalReadinessSnapshot, ApprovedConcept,
    ApprovedProposalProjection, ApprovedSection, ProposalReviewSession,
)
from apps.content_processing.domain.proposal import ProposalDecision


class DjangoAcademicReviewRepository:
    def get(self, session_id, *, for_update=False):
        query = ProposalReviewSession.objects.select_related("proposal__resource", "reviewer", "opened_by")
        if for_update:
            query = query.select_for_update()
        return query.get(id=session_id)

    def current_for_proposal(self, proposal_id):
        return ProposalReviewSession.objects.filter(proposal_id=proposal_id).order_by("-created_at").first()

    def save(self, session, *, fields=None):
        session.save(update_fields=fields)
        return session

    def approval_context(self, session_id, *, for_update=False):
        query = ProposalReviewSession.objects.select_related("proposal__job", "proposal__resource__subject", "proposal__resource__institution")
        session = (query.select_for_update() if for_update else query).get(id=session_id)
        if for_update:
            type(session.proposal).objects.select_for_update().get(id=session.proposal_id)
        decisions = list(session.item_decisions.select_related(
            "proposed_section__hierarchy_node", "proposed_concept__proposed_section",
            "proposed_concept__semantic_segment", "edit",
        ).order_by("item_type", "id"))
        validations = list(session.proposal.validations.order_by("id"))
        resolutions = list(session.finding_resolutions.select_related("validation", "override").order_by("id"))
        newer_exists = session.proposal.job.academic_import_proposals.exclude(id=session.proposal_id).filter(created_at__gt=session.proposal.created_at).exists()
        section_evidence = {str(item.id): list(item.evidence_records.values_list("id", flat=True)) for item in session.proposal.proposed_sections.all()}
        concept_evidence = {str(item.id): list(item.evidence_records.values_list("id", flat=True)) for item in session.proposal.proposed_concepts.all()}
        return {"session": session, "decisions": decisions, "validations": validations, "resolutions": resolutions, "newer_exists": newer_exists, "section_evidence": section_evidence, "concept_evidence": concept_evidence}

    def finalize_approval(self, session, *, with_edits):
        session.approve(with_edits=with_edits)
        session.save(update_fields=["status", "closed_at", "version", "updated_at"])
        session.proposal.approve(with_edits=with_edits)
        session.proposal.save(update_fields=["review_state", "decision", "population_state"])

    def finalize_rejection(self, session):
        session.reject()
        session.save(update_fields=["status", "closed_at", "version", "updated_at"])
        session.proposal.reject()
        session.proposal.save(update_fields=["review_state", "decision", "population_state"])

    def record_proposal_decision(self, **values):
        return ProposalDecision.objects.create(**values)


class DjangoApprovalReadinessRepository:
    def add(self, snapshot):
        snapshot.save(force_insert=True)
        return snapshot

    def get(self, snapshot_id, *, for_update=False):
        query = ApprovalReadinessSnapshot.objects.select_related("session", "proposal", "evaluated_by")
        return (query.select_for_update() if for_update else query).get(id=snapshot_id)

    def get_identity(self, session_id, review_session_version, checksum):
        return ApprovalReadinessSnapshot.objects.get(session_id=session_id, review_session_version=review_session_version, checksum=checksum)


class DjangoApprovalDecisionRepository:
    def add(self, decision):
        decision.save(force_insert=True)
        return decision

    def get_idempotent(self, session_id, idempotency_key):
        return ApprovalDecision.objects.select_related("projection").filter(session_id=session_id, idempotency_key=idempotency_key).first()


class DjangoApprovedProjectionRepository:
    def add(self, projection):
        projection.save(force_insert=True)
        return projection

    def get(self, projection_id):
        return ApprovedProposalProjection.objects.select_related("proposal__resource__subject", "session", "approval_decision", "resource", "subject", "institution").prefetch_related("sections", "concepts__section").get(id=projection_id)

    def get_for_population(self, projection_id):
        return ApprovedProposalProjection.objects.select_for_update().select_related(
            "proposal__resource__subject", "approval_decision", "resource", "subject", "institution"
        ).prefetch_related("sections", "concepts__section").get(id=projection_id)

    def get_by_approval_version(self, proposal_id, approval_version):
        return ApprovedProposalProjection.objects.filter(proposal_id=proposal_id, approval_version=approval_version).first()


class DjangoApprovedSectionRepository:
    def add_many(self, sections):
        return ApprovedSection.objects.bulk_create(sections)

    def link_parents(self, projection, parent_by_source):
        for source_id, parent_source_id in parent_by_source.items():
            ApprovedSection.objects.filter(projection=projection, source_id=source_id).update(parent_id=ApprovedSection.objects.only("id").get(projection=projection, source_id=parent_source_id).id)

    def by_source(self, projection):
        return {item.source_id: item for item in ApprovedSection.objects.filter(projection=projection)}


class DjangoApprovedConceptRepository:
    def add_many(self, concepts):
        return ApprovedConcept.objects.bulk_create(concepts)
