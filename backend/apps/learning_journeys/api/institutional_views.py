from __future__ import annotations

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..application.institutional_services import (
    InstitutionalCompletionService,
    InstitutionalInterventionService,
    InstitutionalJourneyVisibilityPolicy,
)
from ..application.operational import LearningJourneyOperationalViewService
from ..application.progression_services import CompetencyProgressSnapshotService
from ..domain.models import InstitutionalInterventionRecommendation, InstitutionalLearningAssignment, LearningJourney


def intervention_payload(recommendation: InstitutionalInterventionRecommendation) -> dict:
    return {
        "id": str(recommendation.id),
        "journey_id": str(recommendation.journey_id),
        "reason": recommendation.reason,
        "severity": recommendation.severity,
        "recommended_action": recommendation.recommended_action,
        "status": recommendation.status,
        "created_at": recommendation.created_at.isoformat(),
        "resolved_at": recommendation.resolved_at.isoformat() if recommendation.resolved_at else None,
    }


class InstitutionalLearningJourneyViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    visibility_policy_class = InstitutionalJourneyVisibilityPolicy
    get_service_class = LearningJourneyOperationalViewService
    progress_service_class = CompetencyProgressSnapshotService
    completion_service_class = InstitutionalCompletionService
    intervention_service_class = InstitutionalInterventionService

    def _visibility(self):
        return self.visibility_policy_class()

    def _assignment_queryset(self):
        return InstitutionalLearningAssignment.objects.select_related("journey", "institution", "learner", "subject", "curriculum_reference")

    def list(self, request):
        assignments = [assignment for assignment in self._assignment_queryset().order_by("-updated_at") if self._visibility().can_view_assignment(actor=request.user, assignment=assignment)]
        return Response([self._assignment_payload(assignment) for assignment in assignments])

    def retrieve(self, request, pk=None):
        assignment = self._assignment_for_journey(pk=pk, actor=request.user)
        return Response(self._assignment_payload(assignment, include_journey=True, actor=request.user))

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        assignment = self._assignment_for_journey(pk=pk, actor=request.user)
        return Response(self.progress_service_class().journey_progress(journey_id=assignment.journey_id, actor=request.user))

    @action(detail=True, methods=["get"])
    def interventions(self, request, pk=None):
        assignment = self._assignment_for_journey(pk=pk, actor=request.user)
        rows = assignment.interventions.order_by("-created_at")
        return Response([intervention_payload(row) for row in rows])

    @action(detail=True, methods=["post"], url_path="evaluate-completion")
    def evaluate_completion(self, request, pk=None):
        assignment = self._assignment_for_journey(pk=pk, actor=request.user)
        try:
            return Response(self.completion_service_class().evaluate(journey_id=assignment.journey_id, actor=request.user))
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

    def _assignment_for_journey(self, *, pk, actor):
        try:
            assignment = self._assignment_queryset().get(journey_id=pk)
        except InstitutionalLearningAssignment.DoesNotExist as exc:
            raise NotFound("INSTITUTIONAL_LEARNING_JOURNEY_NOT_FOUND") from exc
        if not self._visibility().can_view_assignment(actor=actor, assignment=assignment):
            raise PermissionDenied("INSTITUTIONAL_LEARNING_JOURNEY_PERMISSION_DENIED")
        return assignment

    def _assignment_payload(self, assignment: InstitutionalLearningAssignment, *, include_journey: bool = False, actor=None) -> dict:
        payload = {
            "journey_id": str(assignment.journey_id),
            "assignment_id": str(assignment.id),
            "learner_id": str(assignment.learner_id),
            "institution": {"id": str(assignment.institution_id), "name": assignment.institution.name},
            "assignment_state": assignment.assignment_state,
            "completion_state": assignment.completion_state,
            "programme": assignment.programme_label,
            "course": assignment.course_label,
            "subject": {"id": str(assignment.subject_id), "name": assignment.subject.name} if assignment.subject_id else None,
            "curriculum": {"id": str(assignment.curriculum_reference_id), "title": assignment.curriculum_reference.title}
            if assignment.curriculum_reference_id
            else None,
        }
        if include_journey and actor:
            payload["journey"] = self.get_service_class().execute(journey_id=assignment.journey_id, actor=actor)
        return self._visibility().filter_institutional_payload(payload)
