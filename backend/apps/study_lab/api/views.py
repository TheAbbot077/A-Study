from rest_framework import status
from rest_framework.exceptions import APIException, NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.study_lab.api.serializers import (
    ArtefactTransformationRequestSerializer,
    StudyArtefactCreateSerializer,
    LearnerWorkspaceNoteCreateSerializer,
    LearnerWorkspaceNoteSerializer,
    LearnerWorkspaceNoteUpdateSerializer,
    StudyArtefactLineageSerializer,
    StudyArtefactSerializer,
    StudyToolDefinitionSerializer,
    StudyToolManifestSerializer,
    StudyScaffoldGenerationRequestSerializer,
    WorkspaceToolSessionSerializer,
    StudyWorkspaceCreateSerializer,
    StudyWorkspaceSerializer,
)
from apps.study_lab.application.instruments.services import ConvertUnitService, EvaluateCalculationService, GenerateGraphDataService
from apps.study_lab.application.services import (
    ArchiveLearnerWorkspaceNoteService,
    ArchiveStudyWorkspaceService,
    AssembleStudyWorkspaceService,
    ActivateStudyWorkspaceService,
    CompleteStudyWorkspaceService,
    CreateLearnerWorkspaceNoteService,
    CreateStudyWorkspaceService,
    ListLearnerStudyWorkspacesQuery,
    ListLearnerWorkspaceActivityQuery,
    ListLearnerWorkspaceNotesQuery,
    ListWorkspacePanelsQuery,
    ListWorkspaceToolsQuery,
    DeleteLearnerWorkspaceNoteService,
    PauseStudyWorkspaceService,
    ResolveWorkspaceResumePointService,
    ResumeStudyWorkspaceService,
    RetrieveLearnerStudyWorkspaceQuery,
    RetrieveWorkspaceSnapshotQuery,
    SetWorkspaceContextService,
    UpdateLearnerWorkspaceNoteService,
)
from apps.study_lab.application.interoperability_services import (
    ArchiveStudyArtefactService,
    BuildArtefactLineageService,
    CompleteTransformationService,
    CancelStudyScaffoldGenerationService,
    CreateReferencedArtefactService,
    CreateStudyArtefactService,
    ExportProviderArtefactService,
    FailTransformationService,
    GetArtefactLineageQuery,
    GetArtefactQuery,
    GetTransformationRequestQuery,
    ImportProviderArtefactService,
    LaunchWorkspaceToolService,
    ListWorkspaceArtefactsQuery,
    RegisterStudyToolService,
    ResolveArtefactCompatibilityService,
    ResolveToolAvailabilityService,
    RequestTransformationService,
    RequestStudyScaffoldGenerationService,
    RevokeSharingService,
    ResumeWorkspaceToolService,
    ShareStudyArtefactService,
    VersionStudyArtefactService,
)
from apps.study_lab.domain.enums import StudyArtefactVisibility
from apps.study_lab.domain.models import StudyScaffoldGenerationRequest, StudyToolDefinition, StudyToolManifest
from apps.study_lab.domain.exceptions import NoteAccessDeniedError, NoteNotFoundError, NoteVersionConflictError, StudyLabError, WorkspaceAccessDeniedError, WorkspaceNotFoundError
from apps.study_lab.domain.exceptions import (
    ArtefactAccessDeniedError,
    ArtefactArchivedError,
    ArtefactNotFoundError,
    IdempotencyConflictError,
    ToolNotFoundError,
    ToolProviderUnavailableError,
    ToolSessionAlreadyCompletedError,
    ToolSessionAccessDeniedError,
    ToolSessionAbandonedError,
    ToolSessionFailedError,
    ToolSessionInvalidTransitionError,
    ToolSessionNotFoundError,
    ToolSessionNotResumableError,
    ToolUnavailableError,
    ScaffoldGenerationNotFoundError,
    ScaffoldGenerationProviderUnavailableError,
)
from apps.study_lab.domain.instruments.schemas import InstrumentSchemaError


class StudyLabConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Version conflict"
    default_code = "NOTE_VERSION_CONFLICT"


class StudyLabUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Provider unavailable"
    default_code = "PROVIDER_UNAVAILABLE"


def _translate_study_lab_error(exc):
    if isinstance(exc, (WorkspaceNotFoundError, NoteNotFoundError)):
        return NotFound(detail={"code": exc.code, "detail": str(exc)})
    if isinstance(exc, (WorkspaceAccessDeniedError, NoteAccessDeniedError)):
        return PermissionDenied(detail={"code": exc.code, "detail": str(exc)})
    if isinstance(exc, NoteVersionConflictError):
        return StudyLabConflict(detail={"code": exc.code, "detail": str(exc)})
    if isinstance(exc, ToolProviderUnavailableError):
        return StudyLabUnavailable(detail={"code": "PROVIDER_UNAVAILABLE", "detail": str(exc)})
    if isinstance(exc, ScaffoldGenerationProviderUnavailableError):
        return StudyLabUnavailable(detail={"code": exc.code, "detail": str(exc)})
    if isinstance(exc, (ToolUnavailableError, ToolNotFoundError, ToolSessionNotFoundError, ToolSessionNotResumableError, ToolSessionAccessDeniedError, ToolSessionInvalidTransitionError, ArtefactNotFoundError, ArtefactAccessDeniedError, ArtefactArchivedError, ToolSessionAlreadyCompletedError, ToolSessionFailedError, ToolSessionAbandonedError)):
        return ValidationError(detail={"code": exc.code, "detail": str(exc)})
    if isinstance(exc, ScaffoldGenerationNotFoundError):
        return NotFound(detail={"code": exc.code, "detail": str(exc)})
    if isinstance(exc, IdempotencyConflictError):
        return ValidationError(detail={"code": exc.code, "detail": str(exc)})
    if isinstance(exc, InstrumentSchemaError):
        return ValidationError(detail={"code": exc.code, "detail": str(exc)})
    return exc


class StudyWorkspaceListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        items = ListLearnerStudyWorkspacesQuery.execute(request.user.id)
        return Response(StudyWorkspaceSerializer(items, many=True).data)

    def post(self, request):
        serializer = StudyWorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        workspace = CreateStudyWorkspaceService.execute(
            learner_id=request.user.id,
            workspace_type=serializer.validated_data["workspace_type"],
            title=serializer.validated_data["title"],
            tenant_id=serializer.validated_data.get("tenant"),
        )
        return Response(StudyWorkspaceSerializer(workspace).data, status=status.HTTP_201_CREATED)


class StudyWorkspaceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        workspace = RetrieveLearnerStudyWorkspaceQuery.execute(workspace_id, request.user.id)
        return Response(StudyWorkspaceSerializer(workspace).data)


class StudyWorkspaceActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id, action):
        mapping = {
            "activate": lambda: ActivateStudyWorkspaceService.execute(workspace_id, request.user.id),
            "pause": lambda: PauseStudyWorkspaceService.execute(workspace_id, request.user.id),
            "resume": lambda: ResumeStudyWorkspaceService.execute(workspace_id, request.user.id),
            "complete": lambda: CompleteStudyWorkspaceService.execute(workspace_id, request.user.id),
            "archive": lambda: ArchiveStudyWorkspaceService.execute(workspace_id, request.user.id),
        }
        if action not in mapping:
            return Response({"detail": "Unsupported action."}, status=status.HTTP_400_BAD_REQUEST)
        workspace = mapping[action]()
        return Response(StudyWorkspaceSerializer(workspace).data)


class StudyWorkspaceContextView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id):
        context = SetWorkspaceContextService.execute(workspace_id, request.user.id, **request.data)
        return Response({"id": str(context.id), "version": context.version})


class StudyWorkspaceResumeStateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        return Response(ResolveWorkspaceResumePointService.execute(workspace_id, request.user.id))


class StudyWorkspaceAssemblyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        return Response(AssembleStudyWorkspaceService.execute(workspace_id, request.user.id))


class StudyWorkspaceSnapshotView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        snapshot = RetrieveWorkspaceSnapshotQuery.execute(workspace_id, request.user.id)
        return Response({"id": str(snapshot.id), "version": snapshot.snapshot_version, "status": snapshot.status})


class StudyWorkspacePanelsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        return Response(ListWorkspacePanelsQuery.execute(workspace_id, request.user.id))


class StudyWorkspaceToolsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        return Response(ListWorkspaceToolsQuery.execute(workspace_id, request.user.id))


class StudyWorkspaceToolLaunchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id, tool_key):
        try:
            session, invocation = LaunchWorkspaceToolService.execute(workspace_id, request.user.id, tool_key, input_artefact_ids=request.data.get("input_artefact_ids"), idempotency_key=request.data.get("idempotency_key", ""))
            return Response({"session": WorkspaceToolSessionSerializer(session).data, "invocation_id": str(invocation.id)})
        except StudyLabError as exc:
            raise _translate_study_lab_error(exc)


class StudyWorkspaceToolResumeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id, tool_key):
        try:
            session = WorkspaceToolSessionSerializer(ResumeWorkspaceToolService.execute(workspace_id, request.user.id, request.data.get("session_id"))).data
            return Response(session)
        except StudyLabError as exc:
            raise _translate_study_lab_error(exc)


class StudyWorkspaceNotesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        notes = ListLearnerWorkspaceNotesQuery.execute(workspace_id, request.user.id)
        return Response(LearnerWorkspaceNoteSerializer(notes, many=True).data)

    def post(self, request, workspace_id):
        serializer = LearnerWorkspaceNoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = CreateLearnerWorkspaceNoteService.execute(workspace_id, request.user.id, **serializer.validated_data)
        return Response(LearnerWorkspaceNoteSerializer(note).data, status=status.HTTP_201_CREATED)


class StudyWorkspaceNoteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id, note_id):
        try:
            note = ListLearnerWorkspaceNotesQuery.execute(workspace_id, request.user.id, include_deleted=True).filter(pk=note_id).first()
            if note is None:
                return Response({"code": "NOTE_NOT_FOUND", "detail": "Note not found."}, status=status.HTTP_404_NOT_FOUND)
            return Response(LearnerWorkspaceNoteSerializer(note).data)
        except StudyLabError as exc:
            raise _translate_study_lab_error(exc)

    def patch(self, request, workspace_id, note_id):
        try:
            serializer = LearnerWorkspaceNoteUpdateSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            note = UpdateLearnerWorkspaceNoteService.execute(
                workspace_id,
                request.user.id,
                note_id,
                title=serializer.validated_data.get("title"),
                content=serializer.validated_data.get("content"),
                version=serializer.validated_data.get("version"),
            )
            return Response(LearnerWorkspaceNoteSerializer(note).data)
        except StudyLabError as exc:
            raise _translate_study_lab_error(exc)

    def delete(self, request, workspace_id, note_id):
        try:
            note = DeleteLearnerWorkspaceNoteService.execute(workspace_id, request.user.id, note_id)
            return Response(LearnerWorkspaceNoteSerializer(note).data)
        except StudyLabError as exc:
            raise _translate_study_lab_error(exc)


class StudyWorkspaceActivityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        activity = ListLearnerWorkspaceActivityQuery.execute(workspace_id, request.user.id)
        return Response([{"id": str(item.id), "activity_type": item.activity_type, "occurred_at": item.occurred_at} for item in activity])


class StudyToolListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tools = StudyToolDefinition.objects.select_related("manifest").order_by("tool_key")
        payload = []
        for tool in tools:
            row = StudyToolDefinitionSerializer(tool).data
            row["manifest"] = StudyToolManifestSerializer(tool.manifest).data if hasattr(tool, "manifest") else None
            payload.append(row)
        return Response(payload)


class StudyInstrumentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tools = StudyToolDefinition.objects.select_related("manifest").order_by("tool_key")
        return Response([StudyToolDefinitionSerializer(tool).data for tool in tools])


class StudyInstrumentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tool_key):
        tool = StudyToolDefinition.objects.filter(tool_key=tool_key).select_related("manifest").first()
        if tool is None:
            return Response({"detail": "Instrument not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = StudyToolDefinitionSerializer(tool).data
        payload["manifest"] = StudyToolManifestSerializer(tool.manifest).data if hasattr(tool, "manifest") else None
        return Response(payload)


class StudyInstrumentAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tool_key):
        tool = StudyToolDefinition.objects.filter(tool_key=tool_key).first()
        if tool is None:
            return Response({"detail": "Instrument not found."}, status=status.HTTP_404_NOT_FOUND)
        availability = ResolveToolAvailabilityService.execute(request.query_params.get("workspace_id"), request.user.id, tool_key) if request.query_params.get("workspace_id") else {"available": False, "reason_code": "WORKSPACE_NOT_ACTIVE", "reason_detail": "workspace_id required"}
        return Response(availability)


class StudyInstrumentCalculateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = EvaluateCalculationService.execute(
            request.data.get("expression", ""),
            precision=int(request.data.get("precision", 12)),
            variables=request.data.get("variables") or None,
        )
        return Response(result)


class StudyInstrumentConvertUnitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = ConvertUnitService.execute(
            request.data.get("category", ""),
            request.data.get("value"),
            request.data.get("source_unit", ""),
            request.data.get("target_unit", ""),
        )
        return Response(result)


class StudyInstrumentGraphView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        result = GenerateGraphDataService.execute(
            request.data.get("expressions") or [],
            x_min=float(request.data.get("x_min", -10)),
            x_max=float(request.data.get("x_max", 10)),
            sample_density=int(request.data.get("sample_density", 25)),
        )
        return Response(result)


class StudyToolDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tool_key):
        tool = StudyToolDefinition.objects.filter(tool_key=tool_key).select_related("manifest").first()
        if tool is None:
            return Response({"detail": "Tool not found."}, status=status.HTTP_404_NOT_FOUND)
        payload = StudyToolDefinitionSerializer(tool).data
        payload["manifest"] = StudyToolManifestSerializer(tool.manifest).data if hasattr(tool, "manifest") else None
        return Response(payload)


class StudyWorkspaceArtefactListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id):
        artefacts = ListWorkspaceArtefactsQuery.execute(workspace_id, request.user.id)
        return Response(StudyArtefactSerializer(artefacts, many=True).data)

    def post(self, request, workspace_id):
        artefact = CreateStudyArtefactService.execute(
            workspace_id,
            request.user.id,
            artefact_type=request.data.get("artefact_type"),
            title=request.data.get("title", ""),
            summary=request.data.get("summary", ""),
            provider_context=request.data.get("provider_context"),
            provider_reference=request.data.get("provider_reference", ""),
            visibility=request.data.get("visibility", StudyArtefactVisibility.PRIVATE),
            schema_version=request.data.get("schema_version", "1"),
            creation_source=request.data.get("creation_source", "NATIVE"),
            native_payload=request.data.get("native_payload") or {},
        )
        return Response(StudyArtefactSerializer(artefact).data, status=status.HTTP_201_CREATED)


class StudyWorkspaceArtefactDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id, artefact_id):
        artefact = GetArtefactQuery.execute(workspace_id, request.user.id, artefact_id)
        return Response(StudyArtefactSerializer(artefact).data)

    def patch(self, request, workspace_id, artefact_id):
        artefact = VersionStudyArtefactService.execute(workspace_id, request.user.id, artefact_id, **request.data)
        return Response(StudyArtefactSerializer(artefact).data)

    def delete(self, request, workspace_id, artefact_id):
        artefact = ArchiveStudyArtefactService.execute(workspace_id, request.user.id, artefact_id)
        return Response(StudyArtefactSerializer(artefact).data)


class StudyWorkspaceArtefactLineageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id, artefact_id):
        lineage = GetArtefactLineageQuery.execute(workspace_id, request.user.id, artefact_id)
        return Response(StudyArtefactLineageSerializer(lineage, many=True).data)


class StudyWorkspaceArtefactCompatibleToolsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id, artefact_id):
        artefact = GetArtefactQuery.execute(workspace_id, request.user.id, artefact_id)
        return Response([ResolveArtefactCompatibilityService.execute(workspace_id, request.user.id, artefact_type=artefact.artefact_type, schema_version=artefact.schema_version, provider_context=artefact.provider_context)])


class StudyWorkspaceTransformationRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id):
        request_obj = RequestTransformationService.execute(workspace_id, request.user.id, **request.data)
        return Response(ArtefactTransformationRequestSerializer(request_obj).data, status=status.HTTP_201_CREATED)


class StudyWorkspaceTransformationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id, request_id):
        request_obj = GetTransformationRequestQuery.execute(workspace_id, request.user.id, request_id)
        return Response(ArtefactTransformationRequestSerializer(request_obj).data)


class StudyWorkspaceScaffoldGenerationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id):
        request_obj = RequestStudyScaffoldGenerationService.execute(
            workspace_id,
            request.user.id,
            generation_type=request.data.get("generation_type"),
            requested_artefact_type=request.data.get("requested_artefact_type"),
            source_artefact_ids=request.data.get("source_artefact_ids") or [],
            title=request.data.get("title", ""),
            summary=request.data.get("summary", ""),
            idempotency_key=request.data.get("idempotency_key", ""),
            policy_version=request.data.get("policy_version", "1"),
            native_payload=request.data.get("native_payload") or {},
            provider_context=request.data.get("provider_context", "STUDY_LAB"),
        )
        return Response(StudyScaffoldGenerationRequestSerializer(request_obj).data, status=status.HTTP_201_CREATED)


class StudyWorkspaceScaffoldGenerationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, workspace_id, request_id):
        request_obj = StudyScaffoldGenerationRequest.objects.filter(pk=request_id, workspace_id=workspace_id, learner_id=request.user.id).first()
        if request_obj is None:
            return Response({"code": "SCAFFOLD_GENERATION_NOT_FOUND", "detail": "Scaffold generation request not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(StudyScaffoldGenerationRequestSerializer(request_obj).data)

    def post(self, request, workspace_id, request_id):
        action = request.data.get("action")
        if action == "cancel":
            request_obj = CancelStudyScaffoldGenerationService.execute(workspace_id, request.user.id, request_id)
            return Response(StudyScaffoldGenerationRequestSerializer(request_obj).data)
        return Response({"detail": "Unsupported action."}, status=status.HTTP_400_BAD_REQUEST)


class StudyWorkspaceArtefactImportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id):
        artefact = ImportProviderArtefactService.execute(workspace_id, request.user.id, **request.data)
        return Response(StudyArtefactSerializer(artefact).data, status=status.HTTP_201_CREATED)


class StudyWorkspaceArtefactExportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id, artefact_id):
        return Response(ExportProviderArtefactService.execute(workspace_id, request.user.id, artefact_id, provider_context=request.data.get("provider_context")))


class StudyWorkspaceArtefactShareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id, artefact_id):
        artefact = ShareStudyArtefactService.execute(workspace_id, request.user.id, artefact_id, visibility=request.data.get("visibility", StudyArtefactVisibility.PRIVATE), recipients=request.data.get("recipients"))
        return Response(StudyArtefactSerializer(artefact).data)


class StudyWorkspaceArtefactRevokeShareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, workspace_id, artefact_id):
        artefact = RevokeSharingService.execute(workspace_id, request.user.id, artefact_id)
        return Response(StudyArtefactSerializer(artefact).data)
