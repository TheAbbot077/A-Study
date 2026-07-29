from __future__ import annotations

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..application.commands import ExecuteLearningJourneyActionCommand
from ..application.orchestration import SelfStudyJourneyOrchestrator
from ..application.progression_services import CompetencyProgressSnapshotService
from ..application.queries import GetLearningJourneyService, ListLearnerJourneysService
from ..application.services import CreateLearningJourneyService, LearningJourneyLifecycleService, SynchronizeLearningJourneyService
from ..domain.models import LearningJourney
from .serializers import (
    CreateInstitutionalJourneySerializer,
    CreateSelfStudyJourneySerializer,
    ExecuteLearningJourneyActionSerializer,
    JourneyVersionCommandSerializer,
)


def problem(exc: DjangoValidationError, response_status=status.HTTP_400_BAD_REQUEST):
    messages = exc.messages if hasattr(exc, "messages") else [str(exc)]
    code = getattr(exc, "code", "") or "VALIDATION_ERROR"
    if hasattr(exc, "error_list") and exc.error_list:
        code = exc.error_list[0].code or code
    return Response({"code": code, "detail": messages[0], "blockers": messages}, status=response_status)


class LearningJourneyViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    create_service_class = CreateLearningJourneyService
    get_service_class = GetLearningJourneyService
    list_service_class = ListLearnerJourneysService
    sync_service_class = SynchronizeLearningJourneyService
    lifecycle_service_class = LearningJourneyLifecycleService
    orchestrator_class = SelfStudyJourneyOrchestrator
    progress_snapshot_service_class = CompetencyProgressSnapshotService

    def _create_service(self):
        return self.create_service_class()

    def _get_service(self):
        return self.get_service_class()

    def _list_service(self):
        return self.list_service_class()

    def _sync_service(self):
        return self.sync_service_class()

    def _lifecycle_service(self):
        return self.lifecycle_service_class()

    def _orchestrator(self):
        return self.orchestrator_class()

    def _progress_snapshot_service(self):
        return self.progress_snapshot_service_class()

    def list(self, request):
        return Response(self._list_service().execute(actor=request.user))

    def retrieve(self, request, pk=None):
        try:
            return Response(self._get_service().execute(journey_id=pk, actor=request.user))
        except LearningJourney.DoesNotExist as exc:
            raise NotFound("LEARNING_JOURNEY_NOT_FOUND") from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

    @action(detail=False, methods=["post"], url_path="self-study")
    def self_study(self, request):
        serializer = CreateSelfStudyJourneySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            journey = self._create_service().for_self_study_workspace(
                workspace_id=serializer.validated_data["workspace_id"],
                actor=request.user,
            )
            return Response(self._get_service().execute(journey_id=journey.id, actor=request.user), status=status.HTTP_201_CREATED)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)

    @action(detail=False, methods=["post"], url_path="institutional")
    def institutional(self, request):
        serializer = CreateInstitutionalJourneySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            journey = self._create_service().for_institutional_membership(
                learner_id=serializer.validated_data["learner_id"],
                institution_id=serializer.validated_data["institution_id"],
                actor=request.user,
                subject_id=serializer.validated_data.get("subject_id"),
                curriculum_reference_id=serializer.validated_data.get("curriculum_reference_id"),
                programme_label=serializer.validated_data.get("programme_label", ""),
                course_label=serializer.validated_data.get("course_label", ""),
                required_competency_ids=serializer.validated_data.get("required_competency_ids", []),
                delivery_objectives=serializer.validated_data.get("delivery_objectives", {}),
            )
            return Response(self._get_service().execute(journey_id=journey.id, actor=request.user), status=status.HTTP_201_CREATED)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)

    @action(detail=True, methods=["post"])
    def synchronize(self, request, pk=None):
        try:
            journey = self._sync_service().execute(journey_id=pk, actor=request.user)
            return Response(self._get_service().execute(journey_id=journey.id, actor=request.user))
        except LearningJourney.DoesNotExist as exc:
            raise NotFound("LEARNING_JOURNEY_NOT_FOUND") from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        return self._lifecycle(request, pk=pk, command="pause")

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        return self._lifecycle(request, pk=pk, command="resume")

    @action(detail=True, methods=["post"])
    def withdraw(self, request, pk=None):
        return self._lifecycle(request, pk=pk, command="withdraw")

    @action(detail=True, methods=["post"], url_path=r"actions/(?P<action_code>[^/.]+)")
    def execute_action(self, request, pk=None, action_code=None):
        serializer = ExecuteLearningJourneyActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            command = ExecuteLearningJourneyActionCommand(
                journey_id=str(pk),
                action_code=str(action_code or "").upper().replace("-", "_"),
                actor_id=str(request.user.id),
                idempotency_key=serializer.validated_data.get("idempotency_key", ""),
                payload=serializer.validated_data.get("payload", {}),
                request_context={"path": request.path, "method": request.method},
            )
            result = self._orchestrator().execute(command=command, actor=request.user)
            response_status = status.HTTP_200_OK
            if result["receipt"]["status"] == "REJECTED":
                response_status = status.HTTP_409_CONFLICT
            if result["receipt"]["status"] == "FAILED":
                response_status = status.HTTP_400_BAD_REQUEST
            return Response(result, status=response_status)
        except LearningJourney.DoesNotExist as exc:
            raise NotFound("LEARNING_JOURNEY_NOT_FOUND") from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)

    @action(detail=True, methods=["get"], url_path="competencies")
    def competencies(self, request, pk=None):
        try:
            return Response(self._progress_snapshot_service().execute(journey_id=pk, actor=request.user))
        except LearningJourney.DoesNotExist as exc:
            raise NotFound("LEARNING_JOURNEY_NOT_FOUND") from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

    @action(detail=True, methods=["get"], url_path="progress")
    def progress(self, request, pk=None):
        try:
            return Response(self._progress_snapshot_service().journey_progress(journey_id=pk, actor=request.user))
        except LearningJourney.DoesNotExist as exc:
            raise NotFound("LEARNING_JOURNEY_NOT_FOUND") from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

    @action(detail=True, methods=["get"], url_path="snapshot")
    def snapshot(self, request, pk=None):
        try:
            snapshot_service = self._progress_snapshot_service()
            return Response(
                {
                    "journey": self._get_service().execute(journey_id=pk, actor=request.user),
                    "competencies": snapshot_service.execute(journey_id=pk, actor=request.user),
                    "progress": snapshot_service.journey_progress(journey_id=pk, actor=request.user),
                }
            )
        except LearningJourney.DoesNotExist as exc:
            raise NotFound("LEARNING_JOURNEY_NOT_FOUND") from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc

    def _lifecycle(self, request, *, pk, command: str):
        serializer = JourneyVersionCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        expected_version = serializer.validated_data.get("expected_version")
        try:
            method = getattr(self._lifecycle_service(), command)
            journey = method(journey_id=pk, actor=request.user, expected_version=expected_version)
            return Response(self._get_service().execute(journey_id=journey.id, actor=request.user))
        except LearningJourney.DoesNotExist as exc:
            raise NotFound("LEARNING_JOURNEY_NOT_FOUND") from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
