from __future__ import annotations

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..application.queries import GetLearningJourneyService, ListLearnerJourneysService
from ..application.services import CreateLearningJourneyService, LearningJourneyLifecycleService, SynchronizeLearningJourneyService
from ..domain.models import LearningJourney
from .serializers import CreateInstitutionalJourneySerializer, CreateSelfStudyJourneySerializer, JourneyVersionCommandSerializer


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
