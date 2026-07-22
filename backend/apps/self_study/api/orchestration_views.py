from django.core.exceptions import PermissionDenied as DjangoPermissionDenied, ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..application.orchestration_services import (
    CompleteTeachingNodeService, CreateTeachingSessionService, GenerateTeachingTurnService,
    GetCurrentTeachingContextService, GetTeachingSessionHandoffService,
    InvalidateTeachingSessionService, PauseTeachingSessionService,
    RecordLearnerTurnService, RequestEvidenceEvaluationService,
    ResumeTeachingSessionService, RevisitTeachingNodeService,
    StartTeachingSessionService, AdvanceTeachingSessionService,
)
from ..orchestration_models import SelfStudyTeachingSession, TeachingTurn, TeachingTurnCitation
from .orchestration_serializers import (
    CreateTeachingSessionSerializer, ExpectedVersionSerializer, InvalidateSerializer,
    LearnerTurnSerializer, PauseSerializer, RevisitNodeSerializer,
    TeachingContextSnapshotSerializer, TeachingSessionFindingSerializer,
    TeachingSessionNodeSerializer, TeachingSessionSerializer, TeachingTransitionSerializer,
    TeachingTurnCitationSerializer, TeachingTurnSerializer,
)
from .views import problem


class TeachingSessionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _query(self, request):
        tenants = request.user.institutionmembership_set.filter(is_active=True).values_list("institution_id", flat=True)
        return SelfStudyTeachingSession.objects.filter(Q(learner=request.user) | Q(tenant_id__in=tenants)).select_related("current_session_node", "intent", "bridge_plan", "preparation_manifest").distinct()

    def _get(self, request, pk):
        try:
            return self._query(request).get(id=pk)
        except SelfStudyTeachingSession.DoesNotExist as exc:
            raise NotFound() from exc

    def _page(self, request, queryset, serializer):
        paginator = LimitOffsetPagination()
        paginator.default_limit = 100
        paginator.max_limit = 250
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(serializer(page, many=True).data)

    def _command(self, callback):
        try:
            return callback()
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)

    def list(self, request):
        return self._page(request, self._query(request).order_by("-created_at", "id"), TeachingSessionSerializer)

    def create(self, request):
        serializer = CreateTeachingSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: CreateTeachingSessionService().execute(actor=request.user, **serializer.validated_data))
        if isinstance(result, Response):
            return result
        session, created = result
        return Response(TeachingSessionSerializer(session).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        return Response(TeachingSessionSerializer(self._get(request, pk)).data)

    @action(detail=True, methods=["get"], url_path="current-node")
    def current_node(self, request, pk=None):
        session = self._get(request, pk)
        if not session.current_session_node_id:
            return Response({"code": "TEACHING_NODE_NOT_CURRENT"}, status=409)
        return Response(TeachingSessionNodeSerializer(session.current_session_node).data)

    @action(detail=True, methods=["get"])
    def nodes(self, request, pk=None):
        return self._page(request, self._get(request, pk).nodes.select_related("graph_node").order_by("topological_layer", "plan_ordinal", "graph_node__stable_key"), TeachingSessionNodeSerializer)

    @action(detail=True, methods=["get"])
    def turns(self, request, pk=None):
        return self._page(request, self._get(request, pk).turns.order_by("sequence_number"), TeachingTurnSerializer)

    @action(detail=True, methods=["get"])
    def citations(self, request, pk=None):
        self._get(request, pk)
        return self._page(request, TeachingTurnCitation.objects.filter(turn__session_id=pk).order_by("turn__sequence_number", "id"), TeachingTurnCitationSerializer)

    @action(detail=True, methods=["get"])
    def findings(self, request, pk=None):
        return self._page(request, self._get(request, pk).findings.order_by("-blocking", "severity", "code", "id"), TeachingSessionFindingSerializer)

    @action(detail=True, methods=["get"])
    def context(self, request, pk=None):
        session = self._get(request, pk)
        snapshot = session.context_snapshots.order_by("-created_at").first()
        if not snapshot:
            return Response(GetCurrentTeachingContextService().execute(pk, request.user))
        return Response(TeachingContextSnapshotSerializer(snapshot).data)

    @action(detail=True, methods=["get"])
    def transitions(self, request, pk=None):
        return self._page(request, self._get(request, pk).transitions.order_by("created_at"), TeachingTransitionSerializer)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        serializer = ExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: StartTeachingSessionService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingSessionSerializer(result).data, status=202)

    @action(detail=True, methods=["post"], url_path="next-turn")
    def next_turn(self, request, pk=None):
        result = self._command(lambda: GenerateTeachingTurnService().execute(pk))
        return result if isinstance(result, Response) else Response(TeachingTurnSerializer(result).data, status=202)

    @action(detail=True, methods=["post"], url_path="learner-turn")
    def learner_turn(self, request, pk=None):
        serializer = LearnerTurnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: RecordLearnerTurnService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingTurnSerializer(result).data, status=201)

    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        serializer = PauseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: PauseTeachingSessionService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingSessionSerializer(result).data)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        serializer = ExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: ResumeTeachingSessionService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingSessionSerializer(result).data, status=202)

    @action(detail=True, methods=["post"])
    def revisit(self, request, pk=None):
        serializer = RevisitNodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: RevisitTeachingNodeService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingSessionSerializer(result).data)

    @action(detail=True, methods=["post"], url_path="request-evaluation")
    def request_evaluation(self, request, pk=None):
        serializer = ExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: RequestEvidenceEvaluationService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingSessionSerializer(result).data)

    @action(detail=True, methods=["post"], url_path="complete-node")
    def complete_node(self, request, pk=None):
        serializer = ExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: CompleteTeachingNodeService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingSessionSerializer(result).data)

    @action(detail=True, methods=["post"])
    def advance(self, request, pk=None):
        serializer = ExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: AdvanceTeachingSessionService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingSessionSerializer(result).data, status=202)

    @action(detail=True, methods=["post"])
    def invalidate(self, request, pk=None):
        serializer = InvalidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: InvalidateTeachingSessionService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingSessionSerializer(result).data)

    @action(detail=True, methods=["get"])
    def handoff(self, request, pk=None):
        result = self._command(lambda: GetTeachingSessionHandoffService().execute(pk, request.user))
        return result if isinstance(result, Response) else Response(result)
