from __future__ import annotations

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.learning_identity.application.memory_queries import (
    BuildLearnerMentorContext,
    GetLearnerMemorySummary,
    ListLearningIdentityTimeline,
)
from apps.learning_identity.application.memory_services import (
    ContestLearningObservationService,
    SetLearnerPreferenceService,
    WithdrawDeclaredAttributeService,
    WithdrawLearnerPreferenceService,
)
from apps.learning_identity.domain.models import LearnerLearningProfile, LearningIdentityAttribute, LearningIdentityObservation
from .serializers import (
    ContestObservationSerializer,
    MentorContextSerializer,
    SetPreferenceSerializer,
    WithdrawDeclarationSerializer,
    WithdrawPreferenceSerializer,
)


def problem(exc: DjangoValidationError):
    code = getattr(exc, "code", None)
    if not code and hasattr(exc, "error_list") and exc.error_list:
        code = getattr(exc.error_list[0], "code", None)
    code = (code or "LEARNING_IDENTITY_VALIDATION_FAILED").upper()
    messages = getattr(exc, "messages", None) or [str(exc)]
    response_status = status.HTTP_409_CONFLICT if code in {"LEARNING_PROFILE_VERSION_CONFLICT", "IDEMPOTENCY_CONFLICT"} else status.HTTP_422_UNPROCESSABLE_ENTITY
    return Response({"code": code, "detail": messages[0], "blockers": messages}, status=response_status)


class LearningIdentityProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        profiles = LearnerLearningProfile.objects.filter(learner=request.user).exclude(status="ARCHIVED").order_by("-updated_at")
        return Response(
            [
                {
                    "profile_id": str(profile.id),
                    "tenant_id": str(profile.tenant_id),
                    "learner_id": str(profile.learner_id),
                    "status": profile.status,
                    "profile_version": profile.version,
                    "updated_at": profile.updated_at.isoformat(),
                }
                for profile in profiles
            ]
        )

    def retrieve(self, request, pk=None):
        return Response(GetLearnerMemorySummary().execute(profile_id=pk, actor=request.user))

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        limit = min(int(request.query_params.get("limit", "50")), 100)
        return Response(ListLearningIdentityTimeline().execute(profile_id=pk, actor=request.user, limit=limit))

    @action(detail=True, methods=["get"], url_path="mentor-context")
    def mentor_context(self, request, pk=None):
        serializer = MentorContextSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        try:
            return Response(BuildLearnerMentorContext().execute(profile_id=pk, actor=request.user, purpose=serializer.validated_data["purpose"]))
        except DjangoValidationError as exc:
            return problem(exc)

    @action(detail=True, methods=["post"], url_path="preferences")
    def set_preference(self, request, pk=None):
        serializer = SetPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            preference = SetLearnerPreferenceService().execute(profile_id=pk, actor=request.user, **serializer.validated_data)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response({"preference_id": str(preference.id), "preference_key": preference.preference_key, "status": preference.status, "version": preference.version})

    @action(detail=True, methods=["post"], url_path="preferences/withdraw")
    def withdraw_preference(self, request, pk=None):
        serializer = WithdrawPreferenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            preference = WithdrawLearnerPreferenceService().execute(profile_id=pk, actor=request.user, **serializer.validated_data)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response({"preference_id": str(preference.id), "preference_key": preference.preference_key, "status": preference.status})

    @action(detail=True, methods=["post"], url_path="declarations/(?P<attribute_id>[^/.]+)/withdraw")
    def withdraw_declaration(self, request, pk=None, attribute_id=None):
        serializer = WithdrawDeclarationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            LearningIdentityAttribute.objects.get(id=attribute_id, profile_version__profile_id=pk)
            correction = WithdrawDeclaredAttributeService().execute(attribute_id=attribute_id, actor=request.user, **serializer.validated_data)
        except LearningIdentityAttribute.DoesNotExist as exc:
            raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED") from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response({"correction_request_id": str(correction.id), "status": correction.status, "action": correction.action})

    @action(detail=True, methods=["post"], url_path="observations/(?P<observation_id>[^/.]+)/contest")
    def contest_observation(self, request, pk=None, observation_id=None):
        serializer = ContestObservationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            observation = LearningIdentityObservation.objects.get(id=observation_id, profile_id=pk)
            correction = ContestLearningObservationService().execute(observation_id=observation.id, actor=request.user, **serializer.validated_data)
        except LearningIdentityObservation.DoesNotExist as exc:
            raise PermissionDenied("LEARNING_IDENTITY_ACCESS_DENIED") from exc
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response({"correction_request_id": str(correction.id), "status": correction.status, "action": correction.action})
