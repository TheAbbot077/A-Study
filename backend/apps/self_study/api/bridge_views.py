from django.core.exceptions import PermissionDenied as DjangoPermissionDenied, ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..application.bridge_services import (
    ActivateBridgePlanService, ApproveBridgePlanService, CreateBridgePlanningRunService,
    GetBridgePlanHandoffService, InvalidateBridgePlanService, RecalculateBridgePlanService,
    RejectBridgePlanService,
)
from ..application.services import _has_institutional_authority
from ..bridge_models import BridgePlan, BridgePlanningRun
from .bridge_serializers import *
from .views import problem


class BridgePlanningRunViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _query(self, request):
        tenants = request.user.institutionmembership_set.filter(is_active=True).values_list("institution_id", flat=True)
        return BridgePlanningRun.objects.filter(Q(intent__learner=request.user) | Q(tenant_id__in=tenants)).select_related("plan").distinct()

    def _get(self, request, pk):
        try: return self._query(request).get(id=pk)
        except BridgePlanningRun.DoesNotExist as exc: raise NotFound() from exc

    def _page(self, request, queryset, serializer):
        paginator = LimitOffsetPagination(); paginator.default_limit = 100; paginator.max_limit = 250
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(serializer(page, many=True).data)

    def _command(self, callback):
        try: return callback()
        except DjangoPermissionDenied as exc: raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc: return problem(exc)

    def list(self, request):
        return self._page(request, self._query(request).order_by("-created_at", "id"), BridgePlanningRunSerializer)

    def create(self, request):
        serializer = CreateBridgePlanningRunSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result = self._command(lambda: CreateBridgePlanningRunService().execute(actor=request.user, **serializer.validated_data))
        if isinstance(result, Response): return result
        run, created = result
        return Response(BridgePlanningRunSerializer(run).data, status=status.HTTP_202_ACCEPTED if created else status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        return Response(BridgePlanningRunSerializer(self._get(request, pk)).data)

    @action(detail=True, methods=["get"])
    def plan(self, request, pk=None):
        run = self._get(request, pk)
        if not hasattr(run, "plan"): return Response({"code": "BRIDGE_PLAN_NOT_READY"}, status=409)
        return Response(BridgePlanSerializer(run.plan).data)


class BridgePlanViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _query(self, request):
        tenants = request.user.institutionmembership_set.filter(is_active=True).values_list("institution_id", flat=True)
        return BridgePlan.objects.filter(Q(intent__learner=request.user) | Q(tenant_id__in=tenants)).select_related("run__graph_version__graph", "run__diagnostic_profile", "run__coverage_evaluation").distinct()

    def _get(self, request, pk):
        try: return self._query(request).select_related("run", "graph_version").get(id=pk)
        except BridgePlan.DoesNotExist as exc: raise NotFound() from exc

    def _command(self, callback):
        try: return callback()
        except DjangoPermissionDenied as exc: raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc: return problem(exc)

    def _page(self, request, queryset, serializer):
        paginator = LimitOffsetPagination(); paginator.default_limit = 100; paginator.max_limit = 250
        page = paginator.paginate_queryset(queryset, request, view=self)
        return paginator.get_paginated_response(serializer(page, many=True).data)

    def list(self, request): return self._page(request, self._query(request).order_by("-generated_at", "id"), BridgePlanSerializer)
    def retrieve(self, request, pk=None): return Response(BridgePlanSerializer(self._get(request, pk)).data)

    @action(detail=True, methods=["get"])
    def nodes(self, request, pk=None):
        return self._page(request, self._get(request, pk).nodes.select_related("graph_node").order_by("topological_layer", "ordinal", "graph_node__stable_key"), BridgePlanNodeSerializer)

    @action(detail=True, methods=["get"])
    def dependencies(self, request, pk=None):
        return self._page(request, self._get(request, pk).dependencies.select_related("predecessor_node", "successor_node").order_by("predecessor_node__topological_layer", "graph_edge__ordinal", "graph_edge_id"), BridgePlanDependencySerializer)

    @action(detail=True, methods=["get"])
    def findings(self, request, pk=None):
        return self._page(request, self._get(request, pk).findings.order_by("-blocking", "severity", "code", "id"), BridgePlanFindingSerializer)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        serializer = DecisionSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result = self._command(lambda: ApproveBridgePlanService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(BridgePlanSerializer(result).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        serializer = DecisionSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result = self._command(lambda: RejectBridgePlanService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(BridgePlanSerializer(result).data)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        serializer = ActivateSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result = self._command(lambda: ActivateBridgePlanService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(BridgePlanSerializer(result).data)

    @action(detail=True, methods=["post"])
    def invalidate(self, request, pk=None):
        serializer = InvalidateSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result = self._command(lambda: InvalidateBridgePlanService().execute(pk, request.user, **serializer.validated_data))
        return result if isinstance(result, Response) else Response(BridgePlanSerializer(result).data)

    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        serializer = ActivateSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result = self._command(lambda: RecalculateBridgePlanService().execute(pk, request.user, **serializer.validated_data))
        if isinstance(result, Response): return result
        run, _ = result; return Response(BridgePlanningRunSerializer(run).data, status=202)

    @action(detail=False, methods=["get"], url_path=r"current-handoff/(?P<intent_id>[^/.]+)")
    def current_handoff(self, request, intent_id=None):
        result = self._command(lambda: GetBridgePlanHandoffService().execute(intent_id, request.user, request.query_params.get("target_set_fingerprint")))
        return result if isinstance(result, Response) else Response(result)
