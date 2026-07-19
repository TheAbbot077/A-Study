from django.core.exceptions import ValidationError as DjangoValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academic_review.api.serializers import (
    ApprovalReadinessSnapshotSerializer, ApproveReviewedProposalSerializer,
    ApprovedProposalProjectionSerializer, BulkActionSerializer, DecisionActionSerializer,
    EditActionSerializer, EvaluateReadinessSerializer, FindingResolutionSerializer,
    ProposalItemDecisionSerializer, ProposalReviewSessionSerializer, ReasonSerializer,
    RejectReviewedProposalSerializer, PopulateApprovedProjectionSerializer,
    AcademicPopulationRunSerializer,
)
from apps.academic_review.application import AcademicReviewService, ProposalReviewQueryService
from apps.academic_review.application.approval_services import (
    ApproveReviewedProposalService, EvaluateProposalApprovalReadinessService,
    RejectReviewedProposalService,
)
from apps.academic_review.application.services import ensure_reviewer
from apps.academic_review.application.population_services import (
    EvaluatePopulationReadinessService, PopulateApprovedProjectionService,
)
from apps.academic_review.domain.models import AcademicPopulationRun, ApprovedProposalProjection, ProposalItemDecision, ProposalReviewSession
from apps.academic_review.infrastructure.persistence import DjangoApprovedProjectionRepository
from apps.content_processing.domain.proposal import AcademicImportProposal, ProposalValidation, ProposedSection


class ReviewPagination(LimitOffsetPagination):
    default_limit = 500
    max_limit = 500


class ProposalReviewSessionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProposalReviewSessionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ReviewPagination

    def get_queryset(self):
        query = ProposalReviewSession.objects.select_related("proposal__resource__subject", "reviewer", "opened_by").order_by("-created_at")
        if self.request.user.is_superuser: return query
        institution_ids = self.request.user.institutionmembership_set.filter(is_active=True, role__in=["reviewer", "administrator", "institution_owner", "system_administrator"]).values_list("institution_id", flat=True)
        return query.filter(proposal__resource__institution_id__in=institution_ids)

    @action(detail=False, methods=["post"], url_path=r"proposals/(?P<proposal_id>[^/.]+)/start")
    def start_review(self, request, proposal_id=None):
        proposal = get_object_or_404(AcademicImportProposal.objects.select_related("resource__subject"), id=proposal_id)
        return Response(self.get_serializer(AcademicReviewService().start(proposal, request.user)).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="outline")
    def outline(self, request, pk=None):
        session = self.get_object(); ensure_reviewer(request.user, session.proposal)
        item_type = request.query_params.get("item_type"); decision = request.query_params.get("decision"); search = request.query_params.get("search", "").strip()
        query = session.item_decisions.select_related("proposed_section", "proposed_concept", "edit").order_by("item_type", "id")
        if item_type: query = query.filter(item_type=item_type)
        if decision: query = query.filter(decision=decision)
        if search: query = query.filter(proposed_section__title__icontains=search) | query.filter(proposed_concept__title__icontains=search)
        page = self.paginate_queryset(query)
        return self.get_paginated_response(ProposalItemDecisionSerializer(page, many=True).data)

    @action(detail=True, methods=["get"], url_path=r"items/(?P<decision_id>[^/.]+)/evidence")
    def evidence(self, request, pk=None, decision_id=None):
        session = self.get_object(); ensure_reviewer(request.user, session.proposal)
        item = get_object_or_404(session.item_decisions, id=decision_id)
        evidence = session.proposal.evidence_records.filter(proposed_section_id=item.proposed_section_id, proposed_concept_id=item.proposed_concept_id).select_related("hierarchy_node", "semantic_segment", "extracted_block")
        return Response([{"id": row.id, "page_start": row.source_page_start, "page_end": row.source_page_end, "evidence_strength": row.evidence_strength, "confidence": row.confidence, "hierarchy": row.hierarchy_node.title, "semantic_segment_id": str(row.semantic_segment_id) if row.semantic_segment_id else None, "block_id": str(row.extracted_block_id) if row.extracted_block_id else None, "supporting_text": row.extracted_block.text if row.extracted_block_id else ""} for row in evidence])

    @action(detail=True, methods=["post"], url_path=r"items/(?P<decision_id>[^/.]+)/decide")
    def decide(self, request, pk=None, decision_id=None):
        serializer = DecisionActionSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        item = AcademicReviewService().decide(pk, decision_id, request.user, **serializer.validated_data)
        return Response(ProposalItemDecisionSerializer(item).data)

    @action(detail=True, methods=["post"], url_path=r"items/(?P<decision_id>[^/.]+)/edit")
    def edit(self, request, pk=None, decision_id=None):
        serializer = EditActionSerializer(data=request.data); serializer.is_valid(raise_exception=True); data = serializer.validated_data
        parent_id = data.pop("parent_section_id", None); target_id = data.pop("target_section_id", None)
        parent = get_object_or_404(ProposedSection, id=parent_id) if parent_id else None
        target = get_object_or_404(ProposedSection, id=target_id) if target_id else None
        AcademicReviewService().edit(pk, decision_id, request.user, parent_section=parent, target_section=target, **data)
        return Response(ProposalItemDecisionSerializer(ProposalItemDecision.objects.get(id=decision_id)).data)

    @action(detail=True, methods=["post"], url_path="bulk")
    def bulk(self, request, pk=None):
        serializer = BulkActionSerializer(data=request.data); serializer.is_valid(raise_exception=True); session = self.get_object(); ensure_reviewer(request.user, session.proposal)
        if serializer.validated_data["preview_only"]: return Response(AcademicReviewService().preview_bulk(session, serializer.validated_data["policy_code"]))
        result = AcademicReviewService().apply_bulk(pk, serializer.validated_data["policy_code"], request.user)
        return Response({"id": result.id, "affected_count": result.affected_count})

    @action(detail=True, methods=["post"], url_path="resolve-finding")
    def resolve_finding(self, request, pk=None):
        serializer = FindingResolutionSerializer(data=request.data); serializer.is_valid(raise_exception=True); data = serializer.validated_data
        validation = get_object_or_404(ProposalValidation, id=data.pop("validation_id"), proposal=self.get_object().proposal)
        item_id = data.pop("item_decision_id", None); item = get_object_or_404(ProposalItemDecision, id=item_id, session_id=pk) if item_id else None
        resolution = AcademicReviewService().resolve_finding(pk, validation, request.user, item_decision=item, **data)
        return Response({"id": resolution.id}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None): return Response(self.get_serializer(AcademicReviewService().submit(pk, request.user)).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        serializer = ApproveReviewedProposalSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        projection = ApproveReviewedProposalService().execute(pk, serializer.validated_data["readiness_snapshot_id"], request.user, serializer.validated_data["idempotency_key"], serializer.validated_data["expected_session_version"])
        return Response({"projection_id": str(projection.id), "status": projection.status, "approval_version": projection.approval_version})

    @action(detail=True, methods=["post"], url_path="evaluate-readiness")
    def evaluate_readiness(self, request, pk=None):
        serializer = EvaluateReadinessSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        snapshot = EvaluateProposalApprovalReadinessService().execute(pk, request.user, serializer.validated_data["expected_session_version"])
        return Response(ApprovalReadinessSnapshotSerializer(snapshot).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = RejectReviewedProposalSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        decision = RejectReviewedProposalService().execute(pk, request.user, serializer.validated_data["reason"], serializer.validated_data["idempotency_key"], serializer.validated_data["expected_session_version"])
        return Response({"decision_id": str(decision.id), "decision": decision.decision})

    @action(detail=True, methods=["post"], url_path="request-reprocessing")
    def request_reprocessing(self, request, pk=None):
        serializer = ReasonSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        return Response(self.get_serializer(AcademicReviewService().request_reprocessing(pk, request.user, serializer.validated_data["reason"])).data)

    @action(detail=True, methods=["get"])
    def findings(self, request, pk=None):
        session = self.get_object(); ensure_reviewer(request.user, session.proposal)
        resolved = set(session.finding_resolutions.values_list("validation_id", flat=True))
        return Response([{"id": finding.id, "code": finding.code, "severity": finding.severity, "passed": finding.passed, "message": finding.public_message, "resolved": finding.id in resolved} for finding in session.proposal.validations.order_by("id")])

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        session = self.get_object(); ensure_reviewer(request.user, session.proposal)
        events = [{"type": "item_decision", "id": item.id, "item_type": item.item_type, "decision": item.decision, "actor_id": str(item.decided_by_id) if item.decided_by_id else None, "at": item.decided_at} for item in session.item_decisions.exclude(decision="pending").order_by("decided_at")]
        events += [{"type": "bulk_action", "id": item.id, "policy_code": item.policy_code, "affected_count": item.affected_count, "actor_id": str(item.applied_by_id), "at": item.created_at} for item in session.bulk_decisions.order_by("created_at")]
        events += [{"type": "override", "id": item.id, "validation_id": item.validation_id, "reason": item.reason, "actor_id": str(item.overridden_by_id), "at": item.created_at} for item in session.overrides.order_by("created_at")]
        return Response(sorted(events, key=lambda item: item["at"] or session.created_at))


class ApprovedProposalProjectionViewSet(viewsets.ViewSet):
    serializer_class = ApprovedProposalProjectionSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def retrieve(self, request, pk=None):
        try: projection = DjangoApprovedProjectionRepository().get(pk)
        except ApprovedProposalProjection.DoesNotExist as exc: raise Http404 from exc
        ensure_reviewer(request.user, projection.proposal)
        return Response(ApprovedProposalProjectionSerializer(projection).data)

    @action(detail=True, methods=["get"], url_path="population-readiness")
    def population_readiness(self, request, pk=None):
        try:
            result = EvaluatePopulationReadinessService().execute(pk, request.user)
        except ApprovedProposalProjection.DoesNotExist as exc:
            raise Http404 from exc
        return Response({
            "approved_projection_id": result.approved_projection_id,
            "status": result.status, "ready": result.ready,
            "expected_section_count": result.expected_section_count,
            "expected_concept_count": result.expected_concept_count,
            "existing_population_run_id": result.existing_population_run_id,
            "blockers": [{"code": item.code, "message": item.message} for item in result.blockers],
        })

    @action(detail=True, methods=["post"], url_path="populate")
    def populate(self, request, pk=None):
        serializer = PopulateApprovedProjectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = PopulateApprovedProjectionService().execute(pk, request.user, **serializer.validated_data)
        except ApprovedProposalProjection.DoesNotExist as exc:
            raise Http404 from exc
        except DjangoValidationError as exc:
            code = getattr(exc, "code", None) or "ACADEMIC_POPULATION_FAILED"
            normalized = str(code).upper()
            response_status = status.HTTP_422_UNPROCESSABLE_ENTITY if normalized in {
                "PROJECTION_INTEGRITY_FAILED", "ACADEMIC_VALIDATION_FAILED",
            } else status.HTTP_409_CONFLICT
            return Response({"code": normalized, "detail": "Academic population could not be completed."}, status=response_status)
        payload = {
            "population_run_id": result.population_run_id,
            "approved_projection_id": result.approved_projection_id,
            "status": result.status, "resource_id": result.resource_id,
            "created_sections": result.created_sections, "matched_sections": result.matched_sections,
            "created_concepts": result.created_concepts, "matched_concepts": result.matched_concepts,
            "failed_items": result.failed_items, "populated_at": result.populated_at,
        }
        return Response(payload, status=status.HTTP_200_OK if result.replayed else status.HTTP_201_CREATED)


class AcademicPopulationRunViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AcademicPopulationRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        query = AcademicPopulationRun.objects.select_related("approved_projection__proposal").prefetch_related("section_mappings", "concept_mappings")
        if self.request.user.is_superuser:
            return query
        institutions = self.request.user.institutionmembership_set.filter(
            is_active=True, role__in=["reviewer", "administrator", "institution_owner", "system_administrator"]
        ).values_list("institution_id", flat=True)
        return query.filter(approved_projection__institution_id__in=institutions)

    @action(detail=True, methods=["get"], url_path="retrieval-readiness")
    def retrieval_readiness(self, request, pk=None):
        from apps.retrieval.application.synchronization_services import EvaluateRetrievalSynchronizationReadinessService

        population_run = self.get_object()
        result = EvaluateRetrievalSynchronizationReadinessService().evaluate(str(population_run.id))
        return Response({
            "academic_population_run_id": result.population_run_id,
            "resource_id": result.resource_id,
            "ready": result.ready,
            "source_fingerprint": result.source_fingerprint,
            "expected_section_count": result.expected_section_count,
            "expected_concept_count": result.expected_concept_count,
            "existing_synchronization_run_id": result.existing_synchronization_run_id,
            "active_generation_id": result.active_generation_id,
            "blockers": list(result.blockers),
            "warnings": list(result.warnings),
        })

    @action(detail=True, methods=["post"], url_path="synchronize-retrieval")
    def synchronize_retrieval(self, request, pk=None):
        from apps.retrieval.api.serializers import RetrievalSynchronizationRunSerializer
        from apps.retrieval.application.synchronization_services import SynchronizeApprovedAcademicRetrievalService

        population_run = self.get_object()
        source_fingerprint = request.data.get("expected_source_fingerprint", "")
        idempotency_key = request.data.get("idempotency_key", "")
        if not source_fingerprint:
            raise ValidationError({"expected_source_fingerprint": "This field is required."})
        try:
            run, replayed = SynchronizeApprovedAcademicRetrievalService().execute(
                population_run_id=population_run.id, expected_source_fingerprint=source_fingerprint,
                idempotency_key=idempotency_key, actor=request.user, reason=request.data.get("reason", ""),
            )
        except DjangoValidationError as exc:
            detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or [str(exc)]
            conflict_codes = {"SOURCE_VERSION_CONFLICT", "SYNCHRONIZATION_CONFLICT"}
            response_status = status.HTTP_409_CONFLICT if any(code in str(detail) for code in conflict_codes) else status.HTTP_422_UNPROCESSABLE_ENTITY
            return Response({"errors": detail}, status=response_status)
        return Response(
            RetrievalSynchronizationRunSerializer(run).data,
            status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED,
        )
