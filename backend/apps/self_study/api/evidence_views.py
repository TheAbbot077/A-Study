from django.core.exceptions import PermissionDenied as DP,ValidationError as DV
from django.db.models import Q
from rest_framework import viewsets,status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound,PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from ..application.evidence_services import CreateEvidenceMappingRunService,InvalidateEvidenceMappingRunService,RecalculateCurriculumCoverageService
from ..evidence_models import EvidenceMappingRun,CoverageStatus
from .evidence_serializers import *
from .views import problem
from ..application.services import _has_institutional_authority
class EvidenceMappingRunViewSet(viewsets.ViewSet):
 permission_classes=[IsAuthenticated]
 def _query(self,request):
  tenants=request.user.institutionmembership_set.filter(is_active=True).values_list("institution_id",flat=True)
  return EvidenceMappingRun.objects.filter(Q(intent__learner=request.user)|Q(tenant_id__in=tenants)).distinct()
 def _get(self,request,pk):
  try:return self._query(request).get(id=pk)
  except EvidenceMappingRun.DoesNotExist as exc:raise NotFound() from exc
 def _page(self,request,queryset,serializer):
  paginator=LimitOffsetPagination();paginator.default_limit=100;paginator.max_limit=250;page=paginator.paginate_queryset(queryset,request,view=self);return paginator.get_paginated_response(serializer(page,many=True).data)
 def list(self,request):return self._page(request,self._query(request).order_by("-created_at"),MappingRunSerializer)
 def retrieve(self,request,pk=None):return Response(MappingRunSerializer(self._get(request,pk)).data)
 def _command(self,fn):
  try:return fn()
  except DP as exc:raise PermissionDenied(str(exc)) from exc
  except DV as exc:return problem(exc)
 def _require_detail_authority(self,request,run):
  if not(request.user.is_superuser or _has_institutional_authority(request.user,run.tenant_id)):raise PermissionDenied("MAPPING_ACCESS_DENIED")
 @action(detail=True,methods=["get"])
 def evidence(self,request,pk=None):
  run=self._get(request,pk);self._require_detail_authority(request,run);return self._page(request,run.evidence_units.order_by("ordinal"),EvidenceUnitSerializer)
 @action(detail=True,methods=["get"])
 def candidates(self,request,pk=None):
  run=self._get(request,pk);self._require_detail_authority(request,run);return self._page(request,run.candidates.order_by("evidence_unit__ordinal","rank"),CandidateSerializer)
 @action(detail=True,methods=["get"])
 def mappings(self,request,pk=None):
  run=self._get(request,pk);self._require_detail_authority(request,run);return self._page(request,run.mappings.order_by("evidence_unit__ordinal","graph_node__stable_key"),MappingSerializer)
 @action(detail=True,methods=["get"])
 def coverage(self,request,pk=None):
  evaluation=self._get(request,pk).coverage_evaluations.filter(status=CoverageStatus.COMPLETED).order_by("-created_at").first()
  if not evaluation:return Response({"code":"COVERAGE_NO_CURRENT_EVALUATION"},status=404)
  return Response({"id":evaluation.id,"status":evaluation.status,"evaluation_fingerprint":evaluation.evaluation_fingerprint,"gap_set_fingerprint":evaluation.gap_set_fingerprint,"summary":evaluation.input_summary,"nodes":NodeCoverageSerializer(evaluation.node_results.order_by("graph_node__stable_key"),many=True).data})
 @action(detail=True,methods=["get"])
 def findings(self,request,pk=None):
  evaluation=self._get(request,pk).coverage_evaluations.filter(status=CoverageStatus.COMPLETED).order_by("-created_at").first();return Response(FindingSerializer(evaluation.findings.order_by("severity","code"),many=True).data if evaluation else [])
 @action(detail=True,methods=["get"],url_path="gap-set")
 def gap_set(self,request,pk=None):
  evaluation=self._get(request,pk).coverage_evaluations.filter(status=CoverageStatus.COMPLETED).order_by("-created_at").first()
  if not evaluation:return Response({"code":"COVERAGE_NO_CURRENT_EVALUATION"},status=409)
  return Response({"evaluation_id":evaluation.id,"graph_version_id":evaluation.graph_version_id,"evaluation_fingerprint":evaluation.evaluation_fingerprint,"gap_set_fingerprint":evaluation.gap_set_fingerprint,"gap_node_ids":evaluation.input_summary.get("gap_node_ids",[])})
 @action(detail=True,methods=["post"])
 def invalidate(self,request,pk=None):
  run=self._get(request,pk);result=self._command(lambda:InvalidateEvidenceMappingRunService().execute(run.id,request.user,request.data.get("reason","MAPPING_INVALIDATED")));return result if isinstance(result,Response) else Response(MappingRunSerializer(result).data)
 @action(detail=True,methods=["post"])
 def recalculate(self,request,pk=None):
  run=self._get(request,pk);result=self._command(lambda:RecalculateCurriculumCoverageService().execute(run.id,request.user));return result if isinstance(result,Response) else Response(MappingRunSerializer(result).data,status=202)
