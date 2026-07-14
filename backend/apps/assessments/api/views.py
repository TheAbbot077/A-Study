from __future__ import annotations

from typing import Any

from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.academic.domain.models import ContentConcept
from apps.assessments.api.serializers import (
    MasteryCheckSnapshotSerializer,
    StartMasteryCheckSerializer,
    SubmitAssessmentAnswerSerializer,
)
from apps.assessments.domain.models import (
    Assessment,
    AssessmentDeliverySession,
    AssessmentItem,
    AssessmentItemBankLink,
    AssessmentResponse,
    AssessmentResult,
    AssessmentState,
    ItemOption,
    MasteryProfile,
)
from apps.assessments.services import (
    AssessmentDeliveryService,
    AssessmentEvaluationService,
    AssessmentService,
    EvidenceIntegrationService,
    MasteryService,
)
from apps.learning.services import ConceptBrowserService
from apps.remediation.application import RemediationPlanningService
from apps.remediation.domain.models import RemediationPlan, RemediationPlanStatus
from apps.users.domain.models import InstitutionMembership


class MasteryCheckViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        concept_id = request.query_params.get("content_concept")
        if not concept_id:
            raise ValidationError({"content_concept": "This query parameter is required."})
        concept = self._get_accessible_concept(request.user, concept_id)
        snapshot = self._snapshot(request.user, concept)
        return Response(MasteryCheckSnapshotSerializer(snapshot).data)

    @action(detail=False, methods=["post"], url_path="start")
    def start(self, request):
        serializer = StartMasteryCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        concept = self._get_accessible_concept(request.user, serializer.validated_data["content_concept"])
        assessment = self._get_assessment(concept)
        if assessment is None:
            raise ValidationError({"content_concept": "No assessment is available for this concept."})

        self._materialize_items_from_bank_links(assessment)

        delivery_service = AssessmentDeliveryService()
        delivery_session = self._latest_open_delivery_session(request.user, assessment)
        if delivery_session is None:
            delivery_session = delivery_service.create_delivery_session(assessment=assessment, learner=request.user)
        delivery_session = delivery_service.start_delivery_session(delivery_session)
        snapshot = self._snapshot(request.user, concept, delivery_session=delivery_session)
        return Response(MasteryCheckSnapshotSerializer(snapshot).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="submit-answer")
    def submit_answer(self, request, pk=None):
        delivery_session = self._get_delivery_session(request.user, pk)
        serializer = SubmitAssessmentAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        item = get_object_or_404(AssessmentItem, id=serializer.validated_data["item_id"], assessment=delivery_session.assessment)
        existing_response = AssessmentResponse.objects.filter(
            attempt=delivery_session.assessment_attempt,
            item=item,
        ).first()
        if existing_response is not None:
            existing_response.response_data = serializer.validated_data["response_data"]
            existing_response.metadata = {"source": "mastery_check_api"}
            existing_response.save()
        else:
            AssessmentDeliveryService().submit_response(
                delivery_session=delivery_session,
                item=item,
                response_payload=serializer.validated_data["response_data"],
                metadata={"source": "mastery_check_api"},
            )

        current_item = AssessmentDeliveryService().get_current_item(delivery_session)
        if current_item and getattr(current_item.item, "id", None) == item.id:
            AssessmentDeliveryService().move_to_next_item(delivery_session)

        concept = delivery_session.assessment.content_concept
        snapshot = self._snapshot(request.user, concept, delivery_session=delivery_session)
        return Response(MasteryCheckSnapshotSerializer(snapshot).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="complete")
    def complete(self, request, pk=None):
        delivery_session = self._get_delivery_session(request.user, pk)
        if delivery_session.assessment_attempt is None:
            raise ValidationError({"detail": "Delivery session is not linked to an assessment attempt."})

        delivery_service = AssessmentDeliveryService()
        evaluation_service = AssessmentEvaluationService()
        evidence_integration_service = EvidenceIntegrationService()
        mastery_service = MasteryService()

        delivery_service.submit_delivery_session(delivery_session)
        result = evaluation_service.evaluate_attempt(delivery_session.assessment_attempt)
        AssessmentService().complete_attempt(delivery_session.assessment_attempt)
        delivery_service.complete_delivery_session(delivery_session)

        integration_summary = evidence_integration_service.integrate_completed_attempt(delivery_session.assessment_attempt)
        mastery_service.evaluate_mastery(request.user, delivery_session.assessment.content_concept)
        remediation_plan = self._ensure_remediation_plan(
            request.user,
            delivery_session.assessment.content_concept,
            integration_summary.integrated_evidence,
            result,
        )

        snapshot = self._snapshot(
            request.user,
            delivery_session.assessment.content_concept,
            delivery_session=delivery_session,
            remediation_plan=remediation_plan,
        )
        return Response(MasteryCheckSnapshotSerializer(snapshot).data, status=status.HTTP_200_OK)

    def _snapshot(
        self,
        learner,
        concept: ContentConcept,
        delivery_session: AssessmentDeliverySession | None = None,
        remediation_plan: RemediationPlan | None = None,
    ) -> dict[str, Any]:
        assessment = self._get_assessment(concept)
        if assessment:
            self._materialize_items_from_bank_links(assessment)
        delivery_session = delivery_session or (self._latest_delivery_session(learner, assessment) if assessment else None)
        questions = self._questions_for_delivery_session(delivery_session) if delivery_session else []
        result = self._result_for_delivery_session(delivery_session)
        mastery_profile = MasteryProfile.objects.filter(learner=learner, content_concept=concept).first()
        evidence = list(concept.learning_evidence.filter(learner=learner).order_by("-created_at")[:5])
        remediation_plan = remediation_plan or self._latest_remediation_plan(learner, concept)
        next_available = self._next_available_concept(concept, learner)
        current_item_id = None
        if delivery_session:
            current_item = next(
                (
                    item
                    for item in AssessmentDeliveryService().list_delivery_items(delivery_session)
                    if item.sequence_number == delivery_session.current_sequence_number
                ),
                None,
            )
            current_item_id = str(getattr(getattr(current_item, "item", None), "id", "")) or None

        return {
            "content_concept_id": str(concept.id),
            "assessment": assessment,
            "delivery_session": delivery_session,
            "questions": questions,
            "current_question_id": current_item_id,
            "result": result,
            "mastery_profile": mastery_profile,
            "evidence": evidence,
            "remediation_plan": self._serialize_remediation_plan(remediation_plan),
            "next_available_concept_id": str(next_available.id) if next_available else None,
            "next_available_concept_title": getattr(next_available, "title", None),
            "can_start": assessment is not None and delivery_session is None,
            "can_submit": delivery_session is not None and delivery_session.status != "completed" and result is None,
            "is_complete": result is not None,
        }

    def _get_accessible_concept(self, learner, concept_id) -> ContentConcept:
        institution_ids = list(
            InstitutionMembership.objects.filter(user=learner, is_active=True).values_list("institution_id", flat=True)
        )
        concept = (
            ContentConcept.objects.filter(
                id=concept_id,
                content_section__learning_resource__subject__institution_id__in=institution_ids,
            )
            .select_related("content_section", "content_section__learning_resource")
            .first()
        )
        if concept is None:
            raise ValidationError({"content_concept": "Concept not found or unavailable."})
        return concept

    def _get_assessment(self, concept: ContentConcept) -> Assessment | None:
        return Assessment.objects.filter(content_concept=concept).order_by("-created_at").first()

    def _latest_open_delivery_session(self, learner, assessment: Assessment) -> AssessmentDeliverySession | None:
        return (
            AssessmentDeliverySession.objects.filter(
                learner=learner,
                assessment=assessment,
                status__in=["created", "active", "paused", "submitted"],
            )
            .order_by("-created_at")
            .first()
        )

    def _latest_delivery_session(self, learner, assessment: Assessment | None) -> AssessmentDeliverySession | None:
        if assessment is None:
            return None
        return AssessmentDeliverySession.objects.filter(learner=learner, assessment=assessment).order_by("-created_at").first()

    def _get_delivery_session(self, learner, delivery_session_id) -> AssessmentDeliverySession:
        return get_object_or_404(AssessmentDeliverySession, id=delivery_session_id, learner=learner)

    def _questions_for_delivery_session(self, delivery_session: AssessmentDeliverySession) -> list[dict[str, Any]]:
        responses = {}
        if delivery_session.assessment_attempt_id:
            responses = {
                response.item_id: response
                for response in AssessmentResponse.objects.filter(attempt=delivery_session.assessment_attempt).select_related("item")
            }
        questions = []
        for item in AssessmentItem.objects.filter(assessment=delivery_session.assessment).order_by("sequence_number"):
            response = responses.get(item.id)
            questions.append(
                {
                    "id": str(item.id),
                    "sequence_number": item.sequence_number,
                    "item_type": item.item_type,
                    "prompt": item.prompt,
                    "options": self._options_for_item(item),
                    "response_data": response.response_data if response else None,
                    "submitted": response is not None,
                    "source_type": "assessment_item",
                }
            )
        return questions

    def _options_for_item(self, item: AssessmentItem) -> list[dict[str, str]]:
        metadata_options = item.metadata.get("options", []) if item.metadata else []
        if metadata_options:
            return [
                {
                    "id": str(option.get("id") or option.get("label") or index),
                    "label": str(option.get("label", "")),
                    "content": str(option.get("content", "")),
                }
                for index, option in enumerate(metadata_options, start=1)
            ]
        if item.item_type == "true_false":
            return [
                {"id": "true", "label": "True", "content": "True"},
                {"id": "false", "label": "False", "content": "False"},
            ]
        return []

    def _result_for_delivery_session(self, delivery_session: AssessmentDeliverySession | None) -> AssessmentResult | None:
        if delivery_session is None or delivery_session.assessment_attempt_id is None:
            return None
        return AssessmentResult.objects.filter(attempt=delivery_session.assessment_attempt).first()

    def _latest_remediation_plan(self, learner, concept: ContentConcept) -> RemediationPlan | None:
        return RemediationPlan.objects.filter(learner=learner, content_concept=concept).order_by("-created_at").first()

    def _ensure_remediation_plan(self, learner, concept: ContentConcept, evidence, result: AssessmentResult | None) -> RemediationPlan | None:
        existing = RemediationPlan.objects.filter(
            learner=learner,
            content_concept=concept,
            status__in=[
                RemediationPlanStatus.PENDING,
                RemediationPlanStatus.ACTIVE,
                RemediationPlanStatus.ESCALATED,
            ],
        ).order_by("-created_at").first()
        if existing:
            return existing

        profile = MasteryProfile.objects.filter(learner=learner, content_concept=concept).first()
        if profile and profile.current_decision == "mastered":
            return None

        candidate = next(
            (
                item
                for item in evidence
                if item.evidence_type in {"misconception", "partial_understanding", "other"}
            ),
            None,
        )
        if candidate is None and result is not None and result.passed is False and evidence:
            candidate = evidence[-1]
        if candidate is None:
            return None
        return RemediationPlanningService().plan_from_evidence(candidate)

    def _serialize_remediation_plan(self, plan: RemediationPlan | None) -> dict[str, Any] | None:
        if plan is None:
            return None
        return {
            "id": str(plan.id),
            "status": plan.status,
            "rationale": plan.rationale,
            "started_at": plan.started_at,
            "completed_at": plan.completed_at,
            "recommendations": [
                {
                    "id": str(recommendation.id),
                    "recommendation_type": recommendation.recommendation_type,
                    "title": recommendation.title,
                    "rationale": recommendation.rationale,
                    "priority": recommendation.priority,
                }
                for recommendation in plan.recommendations.all().order_by("priority", "created_at")
            ],
            "activities": [
                {
                    "id": str(activity.id),
                    "activity_type": activity.activity_type,
                    "title": activity.title,
                    "instructions": activity.instructions,
                    "status": activity.status,
                }
                for activity in plan.activities.all().order_by("created_at")
            ],
        }

    def _next_available_concept(self, concept: ContentConcept, learner):
        learning_resource = concept.content_section.learning_resource
        ordered_concepts = list(
            ContentConcept.objects.filter(content_section__learning_resource=learning_resource)
            .select_related("content_section")
            .order_by("content_section__sequence_number", "sequence_number")
        )
        states = {
            state.concept_id: state
            for state in ConceptBrowserService().list_resource_concept_states(learner, learning_resource)
        }
        passed_current = False
        for candidate in ordered_concepts:
            if str(candidate.id) == str(concept.id):
                passed_current = True
                continue
            if passed_current and states.get(str(candidate.id)) and states[str(candidate.id)].can_start_or_resume:
                return candidate
        return None

    def _materialize_items_from_bank_links(self, assessment: Assessment) -> None:
        if AssessmentItem.objects.filter(assessment=assessment).exists():
            return
        for link in AssessmentItemBankLink.objects.filter(assessment=assessment).select_related("item_bank_entry").order_by("sequence_number"):
            item_bank_entry = link.item_bank_entry
            options = list(ItemOption.objects.filter(item_bank_entry=item_bank_entry).order_by("sequence_number"))
            metadata = dict(item_bank_entry.metadata or {})
            if options and "options" not in metadata:
                metadata["options"] = [
                    {"id": str(option.id), "label": option.label, "content": option.content}
                    for option in options
                ]
            if options and "answer_key" not in metadata:
                correct_option = next((option for option in options if option.is_correct), None)
                if correct_option is not None:
                    metadata["answer_key"] = correct_option.label
            AssessmentItem.objects.create(
                assessment=assessment,
                item_type=item_bank_entry.item_type,
                prompt=item_bank_entry.prompt,
                sequence_number=link.sequence_number,
                metadata=metadata,
            )
