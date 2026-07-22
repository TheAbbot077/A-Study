from django.core.exceptions import PermissionDenied as DjangoPermissionDenied, ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..application.teaching_services import (
    ApproveTeachingPreparationService, CreateTeachingPreparationRunService,
    GetTeachingOrchestrationHandoffService, InvalidateTeachingPreparationService,
    PublishTeachingRetrievalService, RecalculateTeachingPreparationService,
    RejectTeachingPreparationService,
)
from ..teaching_models import TeachingPackResource, TeachingPreparationManifest, TeachingPreparationRun
from .teaching_serializers import (
    CreateTeachingPreparationRunSerializer, DecisionSerializer, ExpectedVersionSerializer,
    InvalidateSerializer, NodeTeachingPackSerializer, TeachingPackResourceSerializer,
    TeachingPreparationManifestSerializer, TeachingPreparationRunSerializer,
    TeachingReadinessEvaluationSerializer, TeachingReadinessFindingSerializer,
    TeachingRetrievalManifestSerializer,
)
from .views import problem


class TeachingPreparationRunViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _query(self, request):
        tenants = request.user.institutionmembership_set.filter(is_active=True).values_list("institution_id", flat=True)
        return TeachingPreparationRun.objects.filter(Q(intent__learner=request.user) | Q(tenant_id__in=tenants)).select_related("manifest").distinct()

    def _get(self, request, pk):
        try:
            return self._query(request).get(id=pk)
        except TeachingPreparationRun.DoesNotExist as exc:
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
        return self._page(request, self._query(request).order_by("-created_at", "id"), TeachingPreparationRunSerializer)

    def create(self, request):
        serializer = CreateTeachingPreparationRunSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: CreateTeachingPreparationRunService().execute(actor=request.user, **serializer.validated_data))
        if isinstance(result, Response):
            return result
        run, created = result
        return Response(TeachingPreparationRunSerializer(run).data, status=status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        return Response(TeachingPreparationRunSerializer(self._get(request, pk)).data)

    @action(detail=True, methods=["get"])
    def manifest(self, request, pk=None):
        run = self._get(request, pk)
        if not hasattr(run, "manifest"):
            return Response({"code": "TEACHING_PREPARATION_NOT_READY"}, status=409)
        return Response(TeachingPreparationManifestSerializer(run.manifest).data)


class TeachingPreparationManifestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _query(self, request):
        tenants = request.user.institutionmembership_set.filter(is_active=True).values_list("institution_id", flat=True)
        return TeachingPreparationManifest.objects.filter(Q(intent__learner=request.user) | Q(tenant_id__in=tenants)).select_related("run", "bridge_plan", "graph_version", "coverage_evaluation").distinct()

    def _get(self, request, pk):
        try:
            return self._query(request).get(id=pk)
        except TeachingPreparationManifest.DoesNotExist as exc:
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
        return self._page(request, self._query(request).order_by("-created_at", "id"), TeachingPreparationManifestSerializer)

    def retrieve(self, request, pk=None):
        return Response(TeachingPreparationManifestSerializer(self._get(request, pk)).data)

    @action(detail=True, methods=["get"], url_path="node-packs")
    def node_packs(self, request, pk=None):
        return self._page(request, self._get(request, pk).node_packs.select_related("graph_node").order_by("topological_layer", "ordinal", "graph_node__stable_key"), NodeTeachingPackSerializer)

    @action(detail=True, methods=["get"], url_path="selected-resources")
    def selected_resources(self, request, pk=None):
        self._get(request, pk)
        return self._page(request, TeachingPackResource.objects.filter(pack__manifest_id=pk).order_by("pack__topological_layer", "pack__ordinal", "rank", "id"), TeachingPackResourceSerializer)

    @action(detail=True, methods=["get"])
    def findings(self, request, pk=None):
        return self._page(request, self._get(request, pk).findings.order_by("-blocking", "severity", "code", "id"), TeachingReadinessFindingSerializer)

    @action(detail=True, methods=["get"], url_path="publication")
    def publication(self, request, pk=None):
        manifest = self._get(request, pk)
        if not hasattr(manifest, "retrieval_manifest"):
            return Response({"code": "TEACHING_RETRIEVAL_NOT_PUBLISHED"}, status=409)
        return Response(TeachingRetrievalManifestSerializer(manifest.retrieval_manifest).data)

    @action(detail=True, methods=["get"], url_path="readiness")
    def readiness(self, request, pk=None):
        evaluation = self._get(request, pk).readiness_evaluations.order_by("-created_at").first()
        if not evaluation:
            return Response({"code": "TEACHING_READINESS_NOT_EVALUATED"}, status=409)
        return Response(TeachingReadinessEvaluationSerializer(evaluation).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: ApproveTeachingPreparationService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingPreparationManifestSerializer(result).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = DecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: RejectTeachingPreparationService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingPreparationManifestSerializer(result).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        serializer = ExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: PublishTeachingRetrievalService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingRetrievalManifestSerializer(result).data, status=202)

    @action(detail=True, methods=["post"])
    def invalidate(self, request, pk=None):
        serializer = InvalidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: InvalidateTeachingPreparationService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(TeachingPreparationManifestSerializer(result).data)

    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        serializer = ExpectedVersionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self._command(lambda: RecalculateTeachingPreparationService().execute(pk, request.user, **serializer.validated_data))
        if isinstance(result, Response):
            return result
        run, _ = result
        return Response(TeachingPreparationRunSerializer(run).data, status=202)

    @action(detail=False, methods=["get"], url_path=r"current-handoff/(?P<intent_id>[^/.]+)")
    def current_handoff(self, request, intent_id=None):
        result = self._command(lambda: GetTeachingOrchestrationHandoffService().execute(intent_id, request.user, request.query_params.get("bridge_plan_id")))
        return result if isinstance(result, Response) else Response(result)
