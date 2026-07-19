from dataclasses import asdict

from rest_framework import serializers

from apps.academic_review.application import ProposalReviewQueryService
from apps.academic_review.domain.models import (
    AcademicPopulationRun, ApprovalReadinessSnapshot, ApprovedConcept, ApprovedProposalProjection,
    ApprovedSection, ProposalItemDecision, ProposalReviewSession,
)


class ProposalItemDecisionSerializer(serializers.ModelSerializer):
    item_id = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    confidence = serializers.SerializerMethodField()
    edit = serializers.SerializerMethodField()

    class Meta:
        model = ProposalItemDecision
        fields = ["id", "item_type", "item_id", "title", "confidence", "decision", "reason", "decided_at", "edit"]

    def get_item_id(self, obj): return str(obj.item_id)
    def get_title(self, obj): return obj.proposed_section.title if obj.proposed_section_id else obj.proposed_concept.title
    def get_confidence(self, obj): return obj.proposed_section.confidence if obj.proposed_section_id else obj.proposed_concept.confidence
    def get_edit(self, obj):
        edit = getattr(obj, "edit", None)
        return None if edit is None else {"title": edit.title, "ordering": edit.ordering, "parent_section_id": str(edit.parent_section_id) if edit.parent_section_id else None, "target_section_id": str(edit.target_section_id) if edit.target_section_id else None}


class ProposalReviewSessionSerializer(serializers.ModelSerializer):
    proposal = serializers.UUIDField(source="proposal_id", read_only=True)
    resource = serializers.SerializerMethodField()
    confidence = serializers.FloatField(source="proposal.confidence", read_only=True)
    reviewer_id = serializers.UUIDField(read_only=True, allow_null=True)
    summary = serializers.SerializerMethodField()
    approved_projection_id = serializers.SerializerMethodField()

    class Meta:
        model = ProposalReviewSession
        fields = ["id", "proposal", "resource", "proposal_version", "version", "status", "confidence", "reviewer_id", "approved_projection_id", "summary", "submitted_at", "closed_at", "created_at", "updated_at"]

    def get_resource(self, obj):
        resource = obj.proposal.resource
        return {"id": str(resource.id), "title": resource.title, "source_label": resource.source_label}

    def get_summary(self, obj): return asdict(ProposalReviewQueryService().summary(obj))
    def get_approved_projection_id(self, obj):
        projection = getattr(obj, "approved_projection", None)
        return str(projection.id) if projection else None


class DecisionActionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accepted", "rejected"])
    reason = serializers.CharField(required=False, allow_blank=True)


class EditActionSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    ordering = serializers.IntegerField(required=False, min_value=1)
    parent_section_id = serializers.UUIDField(required=False, allow_null=True)
    target_section_id = serializers.UUIDField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class BulkActionSerializer(serializers.Serializer):
    policy_code = serializers.ChoiceField(choices=["reject_toc", "reject_front_matter", "reject_page_markers", "reject_heading_only_concepts", "reject_synthetic_navigation"])
    preview_only = serializers.BooleanField(default=True)


class FindingResolutionSerializer(serializers.Serializer):
    validation_id = serializers.IntegerField()
    resolution_type = serializers.ChoiceField(choices=["rejection", "edit", "move", "override"])
    item_decision_id = serializers.IntegerField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)
    override_reason = serializers.CharField(required=False, allow_blank=True)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField()


class EvaluateReadinessSerializer(serializers.Serializer):
    expected_session_version = serializers.IntegerField(min_value=1)


class ApproveReviewedProposalSerializer(serializers.Serializer):
    readiness_snapshot_id = serializers.UUIDField()
    expected_session_version = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.CharField(max_length=128)


class RejectReviewedProposalSerializer(serializers.Serializer):
    reason = serializers.CharField()
    expected_session_version = serializers.IntegerField(min_value=1)
    idempotency_key = serializers.CharField(max_length=128)


class ApprovalReadinessSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalReadinessSnapshot
        fields = ["id", "proposal_version", "review_session_version", "ready", "pending_sections", "pending_concepts", "accepted_sections", "accepted_concepts", "rejected_sections", "rejected_concepts", "blocking_findings", "resolved_findings", "orphan_concepts", "invalid_hierarchy", "duplicate_titles", "override_count", "policy_version", "reasons", "checksum", "evaluated_at"]


class ApprovedSectionProjectionSerializer(serializers.ModelSerializer):
    source_proposed_section = serializers.UUIDField(source="source_id", read_only=True)
    final_title = serializers.CharField(source="title", read_only=True)
    ordinal = serializers.IntegerField(source="ordering", read_only=True)
    parent_id = serializers.IntegerField(read_only=True, allow_null=True)
    review_decision_id = serializers.IntegerField(read_only=True, allow_null=True)
    edit_reference_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = ApprovedSection
        fields = ["id", "source_proposed_section", "final_title", "canonical_title", "parent_id", "ordinal", "depth", "page_range", "evidence_references", "review_decision_id", "edit_reference_id", "override_references"]


class ApprovedConceptProjectionSerializer(serializers.ModelSerializer):
    source_proposed_concept = serializers.UUIDField(source="source_id", read_only=True)
    approved_section_id = serializers.IntegerField(source="section_id", read_only=True)
    final_title = serializers.CharField(source="title", read_only=True)
    ordinal = serializers.IntegerField(source="ordering", read_only=True)
    review_decision_id = serializers.IntegerField(read_only=True, allow_null=True)
    edit_reference_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = ApprovedConcept
        fields = ["id", "source_proposed_concept", "approved_section_id", "final_title", "canonical_title", "ordinal", "page_range", "supporting_evidence", "review_decision_id", "edit_reference_id", "override_references"]


class ApprovedProposalProjectionSerializer(serializers.ModelSerializer):
    proposal_id = serializers.UUIDField(read_only=True)
    session_id = serializers.UUIDField(read_only=True, allow_null=True)
    approval_decision_id = serializers.UUIDField(read_only=True, allow_null=True)
    resource_id = serializers.UUIDField(read_only=True, allow_null=True)
    subject_id = serializers.UUIDField(read_only=True, allow_null=True)
    institution_id = serializers.UUIDField(read_only=True, allow_null=True)
    sections = ApprovedSectionProjectionSerializer(many=True, read_only=True)
    concepts = ApprovedConceptProjectionSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovedProposalProjection
        fields = ["id", "proposal_id", "session_id", "approval_decision_id", "approval_version", "projection_version", "resource_id", "subject_id", "institution_id", "status", "checksum", "hierarchy_checksum", "concepts_checksum", "provenance_checksum", "created_at", "sections", "concepts"]


class PopulateApprovedProjectionSerializer(serializers.Serializer):
    expected_fingerprint = serializers.CharField(max_length=128)
    idempotency_key = serializers.CharField(max_length=128)


class AcademicPopulationRunSerializer(serializers.ModelSerializer):
    approved_projection_id = serializers.UUIDField(read_only=True)
    approval_decision_id = serializers.UUIDField(read_only=True)
    resource_id = serializers.UUIDField(read_only=True)
    subject_id = serializers.UUIDField(read_only=True)
    requested_by_id = serializers.UUIDField(read_only=True)
    section_mappings = serializers.SerializerMethodField()
    concept_mappings = serializers.SerializerMethodField()

    class Meta:
        model = AcademicPopulationRun
        fields = [
            "id", "approved_projection_id", "approval_decision_id", "resource_id",
            "subject_id", "requested_by_id", "status", "projection_fingerprint",
            "created_section_count", "matched_section_count", "created_concept_count",
            "matched_concept_count", "failure_code", "failure_message", "started_at",
            "completed_at", "failed_at", "created_at", "section_mappings", "concept_mappings",
        ]

    def get_section_mappings(self, obj):
        return [{"approved_section_id": row.approved_section_id, "academic_section_id": row.academic_section_id, "outcome": row.outcome, "sequence_number": row.sequence_number} for row in obj.section_mappings.all()]

    def get_concept_mappings(self, obj):
        return [{"approved_concept_id": row.approved_concept_id, "academic_concept_id": row.academic_concept_id, "academic_section_id": row.academic_section_id, "outcome": row.outcome, "sequence_number": row.sequence_number} for row in obj.concept_mappings.all()]
