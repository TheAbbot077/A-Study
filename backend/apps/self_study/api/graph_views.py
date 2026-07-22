from django.core.exceptions import PermissionDenied as DjangoPermissionDenied, ValidationError as DjangoValidationError
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..application.graph_services import (CurriculumGraphTraversalService, InvalidateCurriculumGraphService,
    CreateCurriculumGraphVersionService, PersistCurriculumGraphSpecificationService, PublishCurriculumGraphService,
    ValidateCurriculumGraphService)
from ..graph_models import CurriculumGraph, CurriculumGraphVersion, CurriculumNode
from .graph_serializers import (GraphFindingSerializer, GraphInvalidateSerializer, GraphNodeSerializer,
    GraphBuildSerializer, GraphPublishSerializer, GraphSerializer, GraphSpecificationSerializer, GraphVersionSerializer)
from .views import problem
from ..application.diagnostic_services import BuildDiagnosticBlueprintService
from ..diagnostic_models import DiagnosticBlueprint
from .diagnostic_serializers import BlueprintSerializer


def _tenant_ids(user):
    return user.institutionmembership_set.filter(is_active=True).values_list("institution_id", flat=True)


class CurriculumGraphViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _graph(self, request, pk):
        try:
            return CurriculumGraph.objects.select_related("intent", "current_version").filter(
                Q(intent__learner=request.user) | Q(tenant_id__in=_tenant_ids(request.user))).get(id=pk)
        except CurriculumGraph.DoesNotExist as exc:
            raise NotFound() from exc

    def retrieve(self, request, pk=None):
        return Response(GraphSerializer(self._graph(request, pk)).data)

    @action(detail=True, methods=["get", "post"], url_path=r"versions/(?P<version_id>[^/.]+)/diagnostic-blueprint")
    def diagnostic_blueprint(self,request,pk=None,version_id=None):
        graph=self._graph(request,pk)
        try:version=graph.versions.get(id=version_id)
        except CurriculumGraphVersion.DoesNotExist as exc:raise NotFound() from exc
        if request.method=="GET":
            try:bp=version.diagnostic_blueprint
            except DiagnosticBlueprint.DoesNotExist: return Response({"status":"NOT_CREATED"})
            return Response({"id":bp.id,"status":bp.status,"minimum_items":bp.minimum_items,"maximum_items":bp.maximum_items,"competency_domain_count":bp.competency_domain_count})
        serializer=BlueprintSerializer(data=request.data);serializer.is_valid(raise_exception=True)
        result=self._command(lambda:BuildDiagnosticBlueprintService().execute(version.id,request.user,**serializer.validated_data))
        return result if isinstance(result,Response) else Response({"id":result[0].id,"status":result[0].status,"replayed":result[1]},status=200 if result[1] else 201)

    @action(detail=True, methods=["post"], url_path="versions")
    def create_version(self, request, pk=None):
        graph=self._graph(request, pk); serializer=GraphBuildSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result=self._command(lambda: CreateCurriculumGraphVersionService().execute(
            graph_id=graph.id, actor=request.user, construction_method=serializer.validated_data["construction_method"]))
        return result if isinstance(result, Response) else Response(GraphVersionSerializer(result).data, status=201)

    @action(detail=True, methods=["get"], url_path=r"versions/(?P<version_id>[^/.]+)")
    def version(self, request, pk=None, version_id=None):
        graph = self._graph(request, pk)
        try: version = graph.versions.get(id=version_id)
        except CurriculumGraphVersion.DoesNotExist as exc: raise NotFound() from exc
        return Response(GraphVersionSerializer(version).data)

    @action(detail=True, methods=["get"], url_path=r"versions/(?P<version_id>[^/.]+)/nodes")
    def nodes(self, request, pk=None, version_id=None):
        graph = self._graph(request, pk)
        nodes = graph.versions.get(id=version_id).nodes.order_by("ordinal", "stable_key")
        return Response(GraphNodeSerializer(nodes, many=True).data)

    @action(detail=True, methods=["get"], url_path=r"versions/(?P<version_id>[^/.]+)/nodes/(?P<node_id>[^/.]+)/prerequisites")
    def prerequisites(self, request, pk=None, version_id=None, node_id=None):
        graph = self._graph(request, pk)
        try:
            version = graph.versions.get(id=version_id); node = version.nodes.get(id=node_id)
        except (CurriculumGraphVersion.DoesNotExist, CurriculumNode.DoesNotExist) as exc: raise NotFound() from exc
        depth = request.query_params.get("maximum_depth", 10)
        try: closure = CurriculumGraphTraversalService().required_closure(version, node, depth)
        except (TypeError, ValueError): return problem(DjangoValidationError("maximum_depth must be an integer from 1 to 25."))
        return Response([{"depth": item["depth"], "predecessor_id": item["predecessor_id"],
                          "requirement": item["requirement"], "node": GraphNodeSerializer(item["node"]).data} for item in closure])

    @action(detail=True, methods=["get"], url_path=r"versions/(?P<version_id>[^/.]+)/validation")
    def validation(self, request, pk=None, version_id=None):
        graph = self._graph(request, pk); version = graph.versions.get(id=version_id)
        run = version.validation_runs.order_by("-created_at").first()
        return Response({"status": run.status if run else "NOT_RUN", "summary": run.summary if run else {},
                         "findings": GraphFindingSerializer(run.findings.order_by("severity", "code"), many=True).data if run else []})

    def _command(self, callback):
        try: return callback()
        except DjangoPermissionDenied as exc: raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc: return problem(exc)

    @action(detail=True, methods=["post"], url_path=r"versions/(?P<version_id>[^/.]+)/specification")
    def specification(self, request, pk=None, version_id=None):
        self._graph(request, pk); serializer=GraphSpecificationSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result=self._command(lambda: PersistCurriculumGraphSpecificationService().execute(graph_version_id=version_id, payload=serializer.validated_data["specification"], actor=request.user))
        return result if isinstance(result, Response) else Response({"id": result[0].id, "replayed": result[1]})

    @action(detail=True, methods=["post"], url_path=r"versions/(?P<version_id>[^/.]+)/validate")
    def validate_graph(self, request, pk=None, version_id=None):
        self._graph(request, pk); result=self._command(lambda: ValidateCurriculumGraphService().execute(version_id))
        return result if isinstance(result, Response) else Response({"id": result.id, "status": result.status, "summary": result.summary})

    @action(detail=True, methods=["post"], url_path=r"versions/(?P<version_id>[^/.]+)/publish")
    def publish(self, request, pk=None, version_id=None):
        self._graph(request, pk); serializer=GraphPublishSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result=self._command(lambda: PublishCurriculumGraphService().execute(graph_version_id=version_id, actor=request.user, expected_fingerprint=serializer.validated_data["expected_fingerprint"]))
        return result if isinstance(result, Response) else Response(GraphVersionSerializer(result).data)

    @action(detail=True, methods=["post"], url_path=r"versions/(?P<version_id>[^/.]+)/invalidate")
    def invalidate(self, request, pk=None, version_id=None):
        self._graph(request, pk); serializer=GraphInvalidateSerializer(data=request.data); serializer.is_valid(raise_exception=True)
        result=self._command(lambda: InvalidateCurriculumGraphService().execute(graph_version_id=version_id, actor=request.user, reason=serializer.validated_data["reason"]))
        return result if isinstance(result, Response) else Response(GraphVersionSerializer(result).data)
