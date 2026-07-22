from __future__ import annotations

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..application.experience_services import (
    SelfStudyDiagnosticExperienceService,
    SelfStudyPlacementSummaryService,
    SelfStudyPlanExperienceService,
)
from ..application.services import CreateSelfStudyIntentService, UpdateSelfStudyIntentService
from ..application.workspace_services import (
    SelfStudyOnboardingService,
    SelfStudyWorkspaceMaterialService,
    SelfStudyWorkspaceService,
    ensure_workspace_access,
)
from ..workspace_models import SelfStudyWorkspace, SelfStudyWorkspaceMaterial
from .diagnostic_serializers import PublicDiagnosticSerializer
from .serializers import CreateIntentSerializer, SelfStudyIntentSerializer, UpdateIntentSerializer
from .views import problem
from .workspace_serializers import (
    AttachIntentSerializer,
    AttachWorkspaceMaterialSerializer,
    CreateWorkspaceSerializer,
    DiagnosticStartSerializer,
    SelfStudyWorkspaceSerializer,
    UpdateWorkspaceSerializer,
    WorkspaceMaterialSerializer,
    WorkspaceVersionCommandSerializer,
)


class SelfStudyWorkspaceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    workspace_service_class = SelfStudyWorkspaceService
    onboarding_service_class = SelfStudyOnboardingService
    material_service_class = SelfStudyWorkspaceMaterialService
    diagnostic_experience_service_class = SelfStudyDiagnosticExperienceService
    placement_summary_service_class = SelfStudyPlacementSummaryService
    plan_experience_service_class = SelfStudyPlanExperienceService

    def _workspace_service(self):
        return self.workspace_service_class()

    def _onboarding_service(self):
        return self.onboarding_service_class()

    def _material_service(self):
        return self.material_service_class()

    def _diagnostic_experience_service(self):
        return self.diagnostic_experience_service_class()

    def _placement_summary_service(self):
        return self.placement_summary_service_class()

    def _plan_experience_service(self):
        return self.plan_experience_service_class()

    def _workspace(self, request, pk):
        try:
            return self._workspace_service().get_for_actor(workspace_id=pk, actor=request.user)
        except SelfStudyWorkspace.DoesNotExist as exc:
            raise NotFound("WORKSPACE_NOT_FOUND") from exc

    def list(self, request):
        workspaces = self._workspace_service().list_for_actor(actor=request.user).distinct()
        return Response(SelfStudyWorkspaceSerializer(workspaces, many=True).data)

    def retrieve(self, request, pk=None):
        return Response(SelfStudyWorkspaceSerializer(self._workspace(request, pk)).data)

    def create(self, request):
        serializer = CreateWorkspaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        tenant = data.pop("tenant", None)
        try:
            workspace = self._workspace_service().create(
                actor=request.user,
                tenant_id=tenant.id if tenant else None,
                display_name=data["display_name"],
                description=data.get("description", ""),
                idempotency_key=data.get("idempotency_key", ""),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(SelfStudyWorkspaceSerializer(workspace).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, pk=None):
        self._workspace(request, pk)
        serializer = UpdateWorkspaceSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("expected_version")
        try:
            workspace = self._workspace_service().update(
                workspace_id=pk,
                actor=request.user,
                expected_version=expected_version,
                changes=data,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(SelfStudyWorkspaceSerializer(workspace).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        self._workspace(request, pk)
        serializer = WorkspaceVersionCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            workspace = self._workspace_service().archive(
                workspace_id=pk,
                actor=request.user,
                expected_version=serializer.validated_data["expected_version"],
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(SelfStudyWorkspaceSerializer(workspace).data)

    @action(detail=True, methods=["get"])
    def onboarding(self, request, pk=None):
        workspace = self._workspace(request, pk)
        return Response(self._onboarding_service().summarize(workspace=workspace).to_dict())

    @action(detail=True, methods=["get"], url_path="next-action")
    def next_action(self, request, pk=None):
        workspace = self._workspace(request, pk)
        return Response(self._onboarding_service().summarize(workspace=workspace).next_action)

    @action(detail=True, methods=["get", "post", "patch"])
    def intent(self, request, pk=None):
        workspace = self._workspace(request, pk)
        if request.method == "GET":
            return Response(SelfStudyIntentSerializer(workspace.intent).data if workspace.intent_id else {"status": "NOT_CREATED"})
        if request.method == "POST":
            if "intent_id" in request.data:
                serializer = AttachIntentSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                try:
                    workspace = self._workspace_service().attach_intent(
                        workspace_id=workspace.id,
                        actor=request.user,
                        intent_id=serializer.validated_data["intent_id"],
                        expected_version=serializer.validated_data["expected_version"],
                    )
                except DjangoPermissionDenied as exc:
                    raise PermissionDenied(str(exc)) from exc
                except DjangoValidationError as exc:
                    return problem(exc)
                return Response(SelfStudyWorkspaceSerializer(workspace).data)
            serializer = CreateIntentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = dict(serializer.validated_data)
            acknowledged = data.pop("policy_acknowledged")
            data["policy_acknowledged_at"] = timezone.now() if acknowledged else None
            data["learner"] = request.user
            try:
                intent = CreateSelfStudyIntentService().execute(actor=request.user, **data)
                workspace = self._workspace_service().attach_intent(
                    workspace_id=workspace.id,
                    actor=request.user,
                    intent_id=intent.id,
                    expected_version=workspace.version,
                )
            except DjangoPermissionDenied as exc:
                raise PermissionDenied(str(exc)) from exc
            except DjangoValidationError as exc:
                return problem(exc)
            return Response(
                {"workspace": SelfStudyWorkspaceSerializer(workspace).data, "intent": SelfStudyIntentSerializer(intent).data},
                status=status.HTTP_201_CREATED,
            )
        if not workspace.intent_id:
            return Response({"code": "INTENT_REQUIRED", "detail": "No intent is attached to this workspace."}, status=409)
        serializer = UpdateIntentSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        expected_version = data.pop("expected_version")
        if "policy_acknowledged" in data:
            data["policy_acknowledged_at"] = timezone.now() if data.pop("policy_acknowledged") else None
        try:
            intent = UpdateSelfStudyIntentService().execute(
                intent_id=workspace.intent_id,
                actor=request.user,
                expected_version=expected_version,
                changes=data,
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(SelfStudyIntentSerializer(intent).data)

    @action(detail=True, methods=["get", "post"])
    def materials(self, request, pk=None):
        workspace = self._workspace(request, pk)
        material_service = self._material_service()
        if request.method == "GET":
            return Response(WorkspaceMaterialSerializer(material_service.list_materials(workspace=workspace), many=True).data)
        serializer = AttachWorkspaceMaterialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        resource = data["resource"]
        job = data.get("content_processing_job")
        try:
            material = material_service.attach_existing_resource(
                workspace_id=workspace.id,
                actor=request.user,
                resource_id=resource.id,
                content_processing_job_id=job.id if job else None,
                idempotency_key=data.get("idempotency_key", ""),
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(WorkspaceMaterialSerializer(material).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path=r"materials/(?P<resource_id>[^/.]+)")
    def material_detail(self, request, pk=None, resource_id=None):
        workspace = self._workspace(request, pk)
        ensure_workspace_access(request.user, workspace)
        try:
            material = workspace.materials.select_related("resource", "content_processing_job").get(resource_id=resource_id)
        except SelfStudyWorkspaceMaterial.DoesNotExist as exc:
            raise NotFound("WORKSPACE_MATERIAL_NOT_FOUND") from exc
        return Response(WorkspaceMaterialSerializer(material).data)

    @action(detail=True, methods=["get"], url_path="diagnostic/status")
    def diagnostic_status(self, request, pk=None):
        workspace = self._workspace(request, pk)
        diagnostic = workspace.active_diagnostic or (workspace.intent.entry_diagnostics.order_by("-created_at").first() if workspace.intent_id else None)
        return Response(PublicDiagnosticSerializer(diagnostic).data if diagnostic else {"status": "NOT_CREATED"})

    @action(detail=True, methods=["post"], url_path="diagnostic/start")
    def diagnostic_start(self, request, pk=None):
        self._workspace(request, pk)
        serializer = DiagnosticStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            diagnostic, replayed = self._diagnostic_experience_service().start(
                workspace_id=pk,
                actor=request.user,
                purpose_acknowledged=serializer.validated_data["purpose_acknowledged"],
            )
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(PublicDiagnosticSerializer(diagnostic).data, status=status.HTTP_200_OK if replayed else status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="diagnostic/experience")
    def diagnostic_experience(self, request, pk=None):
        self._workspace(request, pk)
        return Response(self._diagnostic_experience_service().experience(workspace_id=pk, actor=request.user).to_dict())

    @action(detail=True, methods=["post"], url_path="diagnostic/resume")
    def diagnostic_resume(self, request, pk=None):
        self._workspace(request, pk)
        try:
            diagnostic = self._diagnostic_experience_service().resume(workspace_id=pk, actor=request.user)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)
        return Response(PublicDiagnosticSerializer(diagnostic).data)

    @action(detail=True, methods=["get"], url_path="diagnostic/summary")
    def diagnostic_summary(self, request, pk=None):
        self._workspace(request, pk)
        try:
            return Response(self._placement_summary_service().execute(workspace_id=pk, actor=request.user).to_dict())
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)

    @action(detail=True, methods=["get"], url_path="plan/experience")
    def plan_experience(self, request, pk=None):
        self._workspace(request, pk)
        return Response(self._plan_experience_service().experience(workspace_id=pk, actor=request.user))

    @action(detail=True, methods=["get"], url_path="plan/nodes")
    def plan_nodes(self, request, pk=None):
        self._workspace(request, pk)
        return Response(self._plan_experience_service().nodes(workspace_id=pk, actor=request.user))

    @action(detail=True, methods=["get"], url_path="plan/findings")
    def plan_findings(self, request, pk=None):
        self._workspace(request, pk)
        return Response(self._plan_experience_service().findings(workspace_id=pk, actor=request.user))

    @action(detail=True, methods=["post"], url_path="plan/start-learning")
    def plan_start_learning(self, request, pk=None):
        self._workspace(request, pk)
        try:
            return Response(self._plan_experience_service().start_learning(workspace_id=pk, actor=request.user), status=status.HTTP_202_ACCEPTED)
        except DjangoPermissionDenied as exc:
            raise PermissionDenied(str(exc)) from exc
        except DjangoValidationError as exc:
            return problem(exc)

    @action(detail=True, methods=["get"], url_path="learning/status")
    def learning_status(self, request, pk=None):
        workspace = self._workspace(request, pk)
        return Response(
            {
                "workspace_id": str(workspace.id),
                "active_bridge_plan_id": str(workspace.active_bridge_plan_id) if workspace.active_bridge_plan_id else "",
                "active_teaching_preparation_id": str(workspace.active_teaching_preparation_id) if workspace.active_teaching_preparation_id else "",
                "active_teaching_session_id": str(workspace.active_teaching_session_id) if workspace.active_teaching_session_id else "",
                "next_action": self._onboarding_service().summarize(workspace=workspace).next_action,
            }
        )
