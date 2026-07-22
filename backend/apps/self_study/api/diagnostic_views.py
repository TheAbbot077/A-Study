from django.core.exceptions import PermissionDenied as DP,ValidationError as DV
from django.db.models import Q
from rest_framework import viewsets,status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound,PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from ..application.diagnostic_services import BuildDiagnosticBlueprintService,CreateEntryDiagnosticService,DiagnosticControlService,DiagnosticDeliveryService,FinalizeDiagnosticPlacementService,PublishDiagnosticBlueprintService,RegisterDiagnosticItemService,SubmitDiagnosticResponseService
from ..diagnostic_models import DiagnosticBlueprint,DiagnosticItemStatus,EntryDiagnostic
from .diagnostic_serializers import *
from .views import problem

class EntryDiagnosticViewSet(viewsets.ViewSet):
    permission_classes=[IsAuthenticated]
    def _get(self,request,pk):
        tenant_ids=request.user.institutionmembership_set.filter(is_active=True).values_list("institution_id",flat=True)
        try:return EntryDiagnostic.objects.select_related("intent","policy_snapshot","blueprint").filter(Q(learner=request.user)|Q(tenant_id__in=tenant_ids)).get(id=pk)
        except EntryDiagnostic.DoesNotExist as exc:raise NotFound() from exc
    def _call(self,fn):
        try:return fn()
        except DP as exc:raise PermissionDenied(str(exc)) from exc
        except DV as exc:return problem(exc)
    def retrieve(self,request,pk=None):return Response(PublicDiagnosticSerializer(self._get(request,pk)).data)
    @action(detail=True,methods=["post"])
    def start(self,request,pk=None):
        d=self._get(request,pk);r=self._call(lambda:DiagnosticDeliveryService().start(d.id,request.user));return r if isinstance(r,Response) else Response(PublicDiagnosticSerializer(r).data)
    @action(detail=True,methods=["get"],url_path="current-item")
    def current_item(self,request,pk=None):
        d=self._get(request,pk);r=self._call(lambda:DiagnosticDeliveryService().current_item(d.id,request.user));return r if isinstance(r,Response) else Response(PublicPresentationSerializer(r).data if r else {"item":None})
    @action(detail=True,methods=["post"])
    def responses(self,request,pk=None):
        d=self._get(request,pk);s=SubmitDiagnosticResponseSerializer(data=request.data);s.is_valid(raise_exception=True);r=self._call(lambda:SubmitDiagnosticResponseService().execute(diagnostic_id=d.id,actor=request.user,presentation_id=s.validated_data["presentation_id"],response_payload=s.validated_data["response"],idempotency_key=s.validated_data["idempotency_key"]));return r if isinstance(r,Response) else Response({"accepted":True,"replayed":r[1]},status=status.HTTP_200_OK if r[1] else status.HTTP_201_CREATED)
    @action(detail=True,methods=["post"])
    def complete(self,request,pk=None):
        d=self._get(request,pk);r=self._call(lambda:FinalizeDiagnosticPlacementService().execute(d.id));return r if isinstance(r,Response) else Response(PublicDiagnosticSerializer(EntryDiagnostic.objects.get(id=d.id)).data)
    @action(detail=True,methods=["post"])
    def cancel(self,request,pk=None):
        d=self._get(request,pk);r=self._call(lambda:DiagnosticControlService().cancel(d,request.user));return r if isinstance(r,Response) else Response(PublicDiagnosticSerializer(r).data)
    @action(detail=True,methods=["post"])
    def challenge(self,request,pk=None):
        d=self._get(request,pk);s=ChallengeSerializer(data=request.data);s.is_valid(raise_exception=True);r=self._call(lambda:DiagnosticControlService().challenge(d,request.user,s.validated_data["reason"]));return r if isinstance(r,Response) else Response({"id":r.id,"status":r.status},status=201)
    @action(detail=True,methods=["post"])
    def retake(self,request,pk=None):
        d=self._get(request,pk);s=CreateDiagnosticSerializer(data=request.data);s.is_valid(raise_exception=True);r=self._call(lambda:DiagnosticControlService().retake(d,request.user,s.validated_data["purpose_acknowledged"]));return r if isinstance(r,Response) else Response(PublicDiagnosticSerializer(r[0]).data,status=200 if r[1] else 201)
    @action(detail=True,methods=["post"])
    def checkpoint(self,request,pk=None):
        d=self._get(request,pk);r=self._call(lambda:DiagnosticControlService().checkpoint(d,request.user));return r if isinstance(r,Response) else Response({"id":r.id,"status":r.status},status=201)

class DiagnosticBlueprintViewSet(viewsets.ViewSet):
    permission_classes=[IsAuthenticated]
    def _call(self,fn):
        try:return fn()
        except DP as exc:raise PermissionDenied(str(exc)) from exc
        except DV as exc:return problem(exc)
    @action(detail=True,methods=["post"])
    def items(self,request,pk=None):
        s=DiagnosticItemRegistrationSerializer(data=request.data);s.is_valid(raise_exception=True);data=dict(s.validated_data);nodes=data.pop("graph_node_ids");r=self._call(lambda:RegisterDiagnosticItemService().execute(blueprint_id=pk,actor=request.user,graph_node_ids=nodes,status=DiagnosticItemStatus.ACTIVE,**data));return r if isinstance(r,Response) else Response({"id":r.id,"status":r.status},status=201)
    @action(detail=True,methods=["post"])
    def publish(self,request,pk=None):
        r=self._call(lambda:PublishDiagnosticBlueprintService().execute(pk,request.user));return r if isinstance(r,Response) else Response({"id":r.id,"status":r.status})
