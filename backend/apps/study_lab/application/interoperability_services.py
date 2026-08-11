from __future__ import annotations

import hashlib

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.study_lab.domain.enums import (
    ArtefactTransformationRequestStatus,
    InstrumentFamily,
    StudyArtefactCompatibilityStatus,
    StudyArtefactLifecycle,
    StudyArtefactLineageRelation,
    StudyArtefactOrigin,
    StudyArtefactType,
    StudyArtefactVisibility,
    ProviderContext,
    StudyToolManifestStatus,
    StudyScaffoldGenerationStatus,
    StudyScaffoldGenerationType,
    ToolAvailabilityReasonCode,
    ToolStatus,
    ToolInvocationLifecycleStatus,
    WorkspaceToolSessionStatus,
)
from apps.study_lab.domain.exceptions import (
    ArtefactAccessDeniedError,
    ArtefactArchivedError,
    ArtefactNotFoundError,
    ArtefactVersionConflictError,
    AssemblyProviderFailureError,
    IdempotencyConflictError,
    ToolNotFoundError,
    ToolProviderUnavailableError,
    ToolProviderTerminalFailureError,
    ToolProviderTransientFailureError,
    ToolSessionAccessDeniedError,
    ToolSessionAbandonedError,
    ToolSessionAlreadyCompletedError,
    ToolSessionAlreadyOpenError,
    ToolSessionFailedError,
    ToolSessionInvalidTransitionError,
    ToolSessionNotFoundError,
    ToolSessionNotResumableError,
    ToolUnavailableError,
    ScaffoldGenerationNotFoundError,
    ScaffoldGenerationProviderUnavailableError,
    TransformationRequestNotFoundError,
    WorkspaceAccessDeniedError,
    WorkspaceArchivedError,
    WorkspaceNotFoundError,
    WorkspaceTenantMismatchError,
)
from apps.study_lab.domain.models import (
    ArtefactTransformationRequest,
    LearnerWorkspaceNote,
    StudyArtefact,
    StudyArtefactLineage,
    StudyArtefactTransformationDefinition,
    StudyToolDefinition,
    StudyToolManifest,
    StudyWorkspace,
    StudyScaffoldGenerationRequest,
    WorkspaceToolSessionCommand,
    WorkspaceToolAvailability,
    WorkspaceToolInvocation,
    WorkspaceToolSession,
)
from apps.study_lab.infrastructure.scaffold_adapters import ScaffoldGenerationProviderRegistry


def _get_workspace(workspace_id, learner_id):
    workspace = StudyWorkspace.objects.filter(pk=workspace_id).first()
    if workspace is None:
        raise WorkspaceNotFoundError(workspace_id)
    if workspace.learner_id != learner_id:
        raise WorkspaceAccessDeniedError()
    return workspace


def _get_session(workspace_id, learner_id, session_id):
    workspace = _get_workspace(workspace_id, learner_id)
    session = WorkspaceToolSession.objects.select_for_update().filter(pk=session_id, workspace=workspace, learner_id=learner_id).first()
    if session is None:
        raise ToolSessionNotFoundError(session_id)
    return workspace, session


def _get_or_create_command(session, workspace, learner_id, operation, idempotency_key):
    if not idempotency_key:
        raise IdempotencyConflictError()
    existing = WorkspaceToolSessionCommand.objects.select_for_update().filter(
        session=session,
        operation=operation,
        idempotency_key=idempotency_key,
    ).first()
    if existing is not None:
        return existing, False
    return WorkspaceToolSessionCommand.objects.create(
        session=session,
        workspace=workspace,
        learner_id=learner_id,
        operation=operation,
        idempotency_key=idempotency_key,
        status=ToolInvocationLifecycleStatus.REQUESTED,
    ), True


class RegisterStudyToolService:
    @staticmethod
    @transaction.atomic
    def execute(*, tool_key, display_name, description="", provider_context, instrument_family=InstrumentFamily.GENERAL_THINKING, supported_workspace_types=None, required_capabilities=None, semantic_version="1.0", supported_artefact_inputs=None, supported_artefact_outputs=None, supported_schema_versions=None, supports_resume=False, supports_transformation=False, supports_transform=None, supports_import=False, supports_export=False, requires_runtime=False, runtime_provider="", offline_capable=True, input_artefact_types=None, output_artefact_types=None):
        if supports_transform is None:
            supports_transform = supports_transformation
        tool, _ = StudyToolDefinition.objects.update_or_create(
            tool_key=tool_key,
            defaults={
                "display_name": display_name,
                "description": description,
                "category": "ORGANIZATION",
                "provider_context": provider_context,
                "instrument_family": instrument_family,
                "required_capability": ",".join(required_capabilities or []),
                "supported_workspace_types": supported_workspace_types or [],
                "input_artefact_types": input_artefact_types or supported_artefact_inputs or [],
                "output_artefact_types": output_artefact_types or supported_artefact_outputs or [],
                "schema_versions": supported_schema_versions or [semantic_version],
                "policy_key": tool_key.lower(),
                "status": ToolStatus.ACTIVE,
                "version": 1,
                "supports_transform": supports_transform,
                "supports_import": supports_import,
                "supports_export": supports_export,
                "requires_runtime": requires_runtime,
                "runtime_provider": runtime_provider,
                "offline_capable": offline_capable,
            },
        )
        manifest, _ = StudyToolManifest.objects.update_or_create(
            tool_definition=tool,
            defaults={
                "manifest_version": semantic_version,
                "supported_artefact_inputs": supported_artefact_inputs or [],
                "supported_artefact_outputs": supported_artefact_outputs or [],
                "supported_schema_versions": supported_schema_versions or [semantic_version],
                "supports_resume": supports_resume,
                "supports_transformation": supports_transformation,
                "supports_import": supports_import,
                "supports_export": supports_export,
                "status": StudyToolManifestStatus.ACTIVE,
                "version": 1,
            },
        )
        return tool, manifest


class ResolveToolAvailabilityService:
    @staticmethod
    def execute(workspace_id, learner_id, tool_key):
        workspace = _get_workspace(workspace_id, learner_id)
        tool = StudyToolDefinition.objects.filter(tool_key=tool_key).first()
        if tool is None:
            raise ToolNotFoundError(tool_key)
        if tool.status != ToolStatus.ACTIVE:
            return {"tool_key": tool_key, "available": False, "reason_code": ToolAvailabilityReasonCode.PROVIDER_UNAVAILABLE, "reason_detail": "Tool is not active"}
        if workspace.is_archived:
            return {"tool_key": tool_key, "available": False, "reason_code": ToolAvailabilityReasonCode.WORKSPACE_ARCHIVED, "reason_detail": "Workspace is archived"}
        if workspace.is_suspended:
            return {"tool_key": tool_key, "available": False, "reason_code": ToolAvailabilityReasonCode.WORKSPACE_SUSPENDED, "reason_detail": "Workspace is suspended"}
        adapter = _provider_adapter(tool.provider_context)
        if adapter is None:
            return {"tool_key": tool_key, "available": False, "reason_code": ToolAvailabilityReasonCode.PROVIDER_UNAVAILABLE, "reason_detail": "No provider adapter"}
        reason_code, reason_detail = adapter.evaluate_availability(workspace, tool)
        return {"tool_key": tool_key, "available": reason_code == ToolAvailabilityReasonCode.AVAILABLE, "reason_code": reason_code, "reason_detail": reason_detail}


class ResolveArtefactCompatibilityService:
    @staticmethod
    def execute(workspace_id, learner_id, *, artefact_type, schema_version, provider_context=None, artefact_id=None):
        workspace = _get_workspace(workspace_id, learner_id)
        if workspace.is_archived:
            return {"status": StudyArtefactCompatibilityStatus.ARTEFACT_ARCHIVED, "reason": "Workspace archived"}
        if artefact_id:
            artefact = _get_artefact(workspace_id, learner_id, artefact_id)
            if artefact.lifecycle == StudyArtefactLifecycle.ARCHIVED:
                return {"status": StudyArtefactCompatibilityStatus.ARTEFACT_ARCHIVED, "reason": "Artefact archived"}
            if artefact.visibility == StudyArtefactVisibility.EXPLICIT_RECIPIENTS and artefact.learner_id != learner_id:
                return {"status": StudyArtefactCompatibilityStatus.ACCESS_DENIED, "reason": "Artefact sharing restricted"}
        if artefact_type not in StudyArtefactType.values:
            return {"status": StudyArtefactCompatibilityStatus.UNSUPPORTED_TYPE, "reason": "Unsupported artefact type"}
        if schema_version not in {"1", 1, "1.0", "1.0.0"}:
            return {"status": StudyArtefactCompatibilityStatus.UNSUPPORTED_SCHEMA, "reason": "Unsupported schema"}
        if provider_context and _provider_adapter(provider_context) is None:
            return {"status": StudyArtefactCompatibilityStatus.PROVIDER_UNAVAILABLE, "reason": "Provider unavailable"}
        return {"status": StudyArtefactCompatibilityStatus.COMPATIBLE, "reason": "Compatible"}


class CreateStudyArtefactService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, *, artefact_type, title="", summary="", provider_context=None, provider_reference="", visibility=StudyArtefactVisibility.PRIVATE, schema_version="1", creation_source=StudyArtefactOrigin.NATIVE, native_payload=None):
        workspace = _get_workspace(workspace_id, learner_id)
        artefact = StudyArtefact.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            tenant_id=workspace.tenant_id,
            artefact_type=artefact_type,
            provider_context=provider_context,
            provider_reference=provider_reference,
            title=title,
            summary=summary,
            visibility=visibility,
            lifecycle=StudyArtefactLifecycle.ACTIVE,
            schema_version=str(schema_version),
            creation_source=creation_source,
            native_payload=native_payload or {},
        )
        _publish_event("StudyArtefactCreated", workspace.id, learner_id, artefact.id)
        return artefact


class CreateReferencedArtefactService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, **kwargs):
        kwargs.setdefault("creation_source", StudyArtefactOrigin.REFERENCED)
        return CreateStudyArtefactService.execute(workspace_id, learner_id, **kwargs)


class ArchiveStudyArtefactService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, artefact_id):
        artefact = _get_artefact(workspace_id, learner_id, artefact_id)
        if artefact.creation_source == StudyArtefactOrigin.REFERENCED:
            raise ArtefactArchivedError()
        artefact.archive()
        artefact.save()
        _publish_event("StudyArtefactArchived", workspace_id, learner_id, artefact.id)
        return artefact


class VersionStudyArtefactService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, artefact_id, *, version, title=None, summary=None, native_payload=None):
        artefact = _get_artefact(workspace_id, learner_id, artefact_id)
        if artefact.version != version:
            raise ArtefactVersionConflictError()
        if artefact.lifecycle == StudyArtefactLifecycle.ARCHIVED:
            raise ArtefactArchivedError()
        if artefact.creation_source == StudyArtefactOrigin.REFERENCED:
            raise ArtefactArchivedError()
        previous_version = artefact.version
        artefact.supersede()
        if title is not None:
            artefact.title = title
        if summary is not None:
            artefact.summary = summary
        if native_payload is not None:
            artefact.native_payload = native_payload
        artefact.lifecycle = StudyArtefactLifecycle.ACTIVE
        artefact.save()
        BuildArtefactLineageService.execute(
            workspace_id,
            learner_id,
            artefact_id,
            artefact.id,
            StudyArtefactLineageRelation.SUPERSEDES,
            provider_context=artefact.provider_context,
            provider_reference=str(previous_version),
        )
        _publish_event("StudyArtefactVersioned", workspace_id, learner_id, artefact.id)
        return artefact


class BuildArtefactLineageService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, source_artefact_id, target_artefact_id, relation_type, provider_context=None, provider_reference=""):
        workspace = _get_workspace(workspace_id, learner_id)
        source = _get_artefact(workspace_id, learner_id, source_artefact_id)
        target = _get_artefact(workspace_id, learner_id, target_artefact_id)
        lineage = StudyArtefactLineage.objects.create(
            workspace=workspace,
            source_artefact=source,
            target_artefact=target,
            relation_type=relation_type,
            provider_context=provider_context,
            provider_reference=provider_reference,
        )
        return lineage


class RequestTransformationService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, *, source_artefact_id, transformation_key, idempotency_key=""):
        workspace = _get_workspace(workspace_id, learner_id)
        source = _get_artefact(workspace_id, learner_id, source_artefact_id)
        definition = StudyArtefactTransformationDefinition.objects.filter(transformation_key=transformation_key).first()
        if definition is None:
            raise TransformationRequestNotFoundError(transformation_key)
        if idempotency_key:
            existing = ArtefactTransformationRequest.objects.filter(workspace=workspace, learner_id=learner_id, idempotency_key=idempotency_key).first()
            if existing:
                return existing
        request = ArtefactTransformationRequest.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            definition=definition,
            source_artefact=source,
            status=ArtefactTransformationRequestStatus.REQUESTED,
            idempotency_key=idempotency_key,
        )
        request.status = ArtefactTransformationRequestStatus.VALIDATING
        request.validating_at = timezone.now()
        request.save()
        request.status = ArtefactTransformationRequestStatus.READY
        request.ready_at = timezone.now()
        request.save()
        _publish_event("StudyTransformationRequested", workspace.id, learner_id, request.id)
        return request


class CompleteTransformationService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, request_id, *, output_artefact_id=None):
        request = _get_transformation_request(workspace_id, learner_id, request_id)
        if request.status not in {ArtefactTransformationRequestStatus.READY, ArtefactTransformationRequestStatus.PROCESSING}:
            return request
        request.status = ArtefactTransformationRequestStatus.PROCESSING
        request.processing_at = request.processing_at or timezone.now()
        request.status = ArtefactTransformationRequestStatus.COMPLETED
        request.completed_at = timezone.now()
        if output_artefact_id:
            request.output_artefact = _get_artefact(workspace_id, learner_id, output_artefact_id)
        request.save()
        _publish_event("StudyTransformationCompleted", workspace_id, learner_id, request.id)
        return request


class FailTransformationService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, request_id, *, failure_reason=""):
        request = _get_transformation_request(workspace_id, learner_id, request_id)
        request.status = ArtefactTransformationRequestStatus.FAILED
        request.failure_reason = failure_reason[:280]
        request.failed_at = timezone.now()
        request.save()
        _publish_event("StudyTransformationFailed", workspace_id, learner_id, request.id)
        return request


class RequestStudyScaffoldGenerationService:
    @staticmethod
    @transaction.atomic
    def execute(
        workspace_id,
        learner_id,
        *,
        generation_type,
        requested_artefact_type,
        source_artefact_ids=None,
        title="",
        summary="",
        idempotency_key="",
        policy_version="1",
        native_payload=None,
        provider_context=ProviderContext.STUDY_LAB,
    ):
        workspace = _get_workspace(workspace_id, learner_id)
        source_artefacts = []
        for artefact_id in source_artefact_ids or []:
            source_artefacts.append(_get_artefact(workspace_id, learner_id, artefact_id))
        if generation_type not in StudyScaffoldGenerationType.values:
            raise ScaffoldGenerationNotFoundError(generation_type)
        if requested_artefact_type not in StudyArtefactType.values:
            raise ScaffoldGenerationNotFoundError(requested_artefact_type)
        provider = ScaffoldGenerationProviderRegistry.get_provider(provider_context)
        available, reason_code, reason_detail = provider.evaluate_availability(workspace, generation_type, source_artefacts)
        if not available:
            raise ScaffoldGenerationProviderUnavailableError(reason_detail)
        if idempotency_key:
            existing = StudyScaffoldGenerationRequest.objects.filter(
                workspace=workspace,
                learner_id=learner_id,
                generation_type=generation_type,
                idempotency_key=idempotency_key,
            ).first()
            if existing is not None:
                return existing
        request = StudyScaffoldGenerationRequest.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            generation_type=generation_type,
            requested_artefact_type=requested_artefact_type,
            provider_context=provider_context,
            policy_version=policy_version,
            idempotency_key=idempotency_key or "",
            request_checksum=hashlib.sha256("|".join([str(workspace.id), str(learner_id), generation_type, requested_artefact_type, policy_version, ",".join(str(item.id) for item in source_artefacts)]).encode("utf-8")).hexdigest(),
        )
        request.source_artefacts.set(source_artefacts)
        request.mark_validating()
        request.save()
        request.mark_ready()
        request.save()
        _publish_event("StudyScaffoldGenerationRequested", workspace.id, learner_id, request.id, generation_type=generation_type)
        return request


class CompleteStudyScaffoldGenerationService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, request_id):
        request = StudyScaffoldGenerationRequest.objects.select_for_update().filter(pk=request_id, workspace_id=workspace_id, learner_id=learner_id).first()
        if request is None:
            raise ScaffoldGenerationNotFoundError(request_id)
        if request.status == StudyScaffoldGenerationStatus.COMPLETED:
            return request
        if request.status in {StudyScaffoldGenerationStatus.CANCELLED, StudyScaffoldGenerationStatus.FAILED}:
            return request
        provider = ScaffoldGenerationProviderRegistry.get_provider(request.provider_context)
        available, reason_code, reason_detail = provider.evaluate_availability(request.workspace, request.generation_type, list(request.source_artefacts.all()))
        if not available:
            request.mark_failed(reason_code, reason_detail)
            request.save()
            _publish_event("StudyScaffoldGenerationFailed", workspace_id, learner_id, request.id, generation_type=request.generation_type, reason_code=reason_code)
            return request
        request.mark_processing()
        request.save()
        generated = provider.generate(
            request.workspace,
            learner_id,
            request.generation_type,
            list(request.source_artefacts.all()),
            requested_artefact_type=request.requested_artefact_type,
            title="",
            summary="",
            native_payload={},
            policy_version=request.policy_version,
            idempotency_key=request.idempotency_key,
            request=request,
        )
        request.provider_reference = generated.get("provider_reference", "")[:128]
        artefact = CreateStudyArtefactService.execute(
            workspace_id,
            learner_id,
            artefact_type=request.requested_artefact_type,
            title=generated.get("title", ""),
            summary=generated.get("summary", ""),
            provider_context=request.provider_context,
            provider_reference=generated.get("provider_reference", ""),
            visibility=StudyArtefactVisibility.PRIVATE,
            schema_version=generated.get("schema_version", "1"),
            creation_source=StudyArtefactOrigin.GENERATED,
            native_payload=generated.get("native_payload") or {},
        )
        request.result_artefact = artefact
        request.mark_completed()
        request.save()
        for source in request.source_artefacts.all():
            BuildArtefactLineageService.execute(
                workspace_id,
                learner_id,
                source.id,
                artefact.id,
                StudyArtefactLineageRelation.DERIVED_FROM,
                provider_context=request.provider_context,
                provider_reference=request.provider_reference,
            )
        _publish_event("StudyScaffoldGenerationCompleted", workspace_id, learner_id, request.id, generation_type=request.generation_type, artefact_id=artefact.id)
        return request


class CancelStudyScaffoldGenerationService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, request_id):
        request = StudyScaffoldGenerationRequest.objects.select_for_update().filter(pk=request_id, workspace_id=workspace_id, learner_id=learner_id).first()
        if request is None:
            raise ScaffoldGenerationNotFoundError(request_id)
        if request.status in {StudyScaffoldGenerationStatus.COMPLETED, StudyScaffoldGenerationStatus.CANCELLED}:
            return request
        request.mark_cancelled("CANCELLED_BY_LEARNER")
        request.save()
        _publish_event("StudyScaffoldGenerationCancelled", workspace_id, learner_id, request.id, generation_type=request.generation_type)
        return request


class LaunchWorkspaceToolService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, tool_key, *, input_artefact_ids=None, idempotency_key=""):
        workspace = _get_workspace(workspace_id, learner_id)
        tool = StudyToolDefinition.objects.filter(tool_key=tool_key).first()
        if tool is None:
            raise ToolNotFoundError(tool_key)
        availability = ResolveToolAvailabilityService.execute(workspace_id, learner_id, tool_key)
        adapter = _provider_adapter(tool.provider_context)
        if adapter is None:
            raise ToolProviderUnavailableError(tool.provider_context)
        if availability["reason_code"] == ToolAvailabilityReasonCode.PROVIDER_UNAVAILABLE:
            raise ToolProviderUnavailableError(tool.provider_context)
        if not availability["available"]:
            raise ToolUnavailableError(availability["reason_code"], availability["reason_detail"])
        existing = None
        if idempotency_key:
            existing = WorkspaceToolInvocation.objects.filter(workspace=workspace, learner_id=learner_id, tool_definition=tool, idempotency_key=idempotency_key).first()
        if existing:
            session = WorkspaceToolSession.objects.filter(workspace=workspace, learner_id=learner_id, tool_definition=tool).order_by("-opened_at").first()
            if session is not None:
                return session, existing
            return None, existing
        session = WorkspaceToolSession.objects.create(workspace=workspace, learner_id=learner_id, tool_definition=tool, provider_context=tool.provider_context, status=WorkspaceToolSessionStatus.OPEN)
        invocation = WorkspaceToolInvocation.objects.create(workspace=workspace, learner_id=learner_id, tool_definition=tool, provider_context=tool.provider_context, idempotency_key=idempotency_key or "", status=ToolInvocationLifecycleStatus.REQUESTED)
        provider_reference = adapter.launch(workspace, tool, learner_id, input_artefact_ids=input_artefact_ids or [], session=session)
        session.provider_reference = provider_reference or ""
        session.open()
        session.save()
        invocation.provider_reference = provider_reference or ""
        invocation.mark_validated()
        invocation.mark_dispatched()
        invocation.mark_running()
        invocation.mark_completed()
        invocation.save()
        _publish_event("StudyToolSessionOpened", workspace.id, learner_id, session.id, tool_key=tool_key)
        return session, invocation


class ResumeWorkspaceToolService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, session_id, *, idempotency_key="", resume_reference=""):
        workspace, session = _get_session(workspace_id, learner_id, session_id)
        if session.status == WorkspaceToolSessionStatus.COMPLETED:
            raise ToolSessionAlreadyCompletedError()
        if session.status == WorkspaceToolSessionStatus.FAILED:
            raise ToolSessionFailedError()
        if session.status == WorkspaceToolSessionStatus.ABANDONED:
            raise ToolSessionAbandonedError()
        command, created = _get_or_create_command(session, workspace, learner_id, "RESUME", idempotency_key or f"resume:{session.id}")
        if not created:
            return session
        adapter = _provider_adapter(session.provider_context)
        if adapter is None:
            raise ToolProviderUnavailableError(session.provider_context)
        if session.status == WorkspaceToolSessionStatus.OPEN:
            command.status = ToolInvocationLifecycleStatus.COMPLETED
            command.completed_at = timezone.now()
            command.save()
            return session
        if session.status != WorkspaceToolSessionStatus.SUSPENDED:
            raise ToolSessionNotResumableError()
        transitioned = session.open()
        session.resume_reference = resume_reference or session.resume_reference
        provider_reference = adapter.resume(workspace, session, learner_id)
        session.provider_reference = provider_reference or session.provider_reference
        session.save()
        command.status = ToolInvocationLifecycleStatus.COMPLETED
        command.provider_reference = provider_reference or ""
        command.completed_at = timezone.now()
        command.save()
        if transitioned or session.status == WorkspaceToolSessionStatus.OPEN:
            _publish_event("StudyToolSessionResumed", workspace.id, learner_id, session.id)
        return session


class SuspendWorkspaceToolSessionService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, session_id, *, idempotency_key=""):
        workspace, session = _get_session(workspace_id, learner_id, session_id)
        if session.status == WorkspaceToolSessionStatus.COMPLETED:
            raise ToolSessionAlreadyCompletedError()
        if session.status == WorkspaceToolSessionStatus.FAILED:
            raise ToolSessionFailedError()
        if session.status == WorkspaceToolSessionStatus.ABANDONED:
            raise ToolSessionAbandonedError()
        command, created = _get_or_create_command(session, workspace, learner_id, "SUSPEND", idempotency_key or f"suspend:{session.id}")
        if not created:
            return session
        if session.status == WorkspaceToolSessionStatus.OPEN:
            session.suspend()
            session.save()
        command.status = ToolInvocationLifecycleStatus.COMPLETED
        command.completed_at = timezone.now()
        command.save()
        _publish_event("StudyToolSessionSuspended", workspace.id, learner_id, session.id)
        return session


class CompleteWorkspaceToolSessionService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, session_id, *, idempotency_key=""):
        workspace, session = _get_session(workspace_id, learner_id, session_id)
        if session.status == WorkspaceToolSessionStatus.COMPLETED:
            raise ToolSessionAlreadyCompletedError()
        if session.status == WorkspaceToolSessionStatus.FAILED:
            raise ToolSessionFailedError()
        if session.status == WorkspaceToolSessionStatus.ABANDONED:
            raise ToolSessionAbandonedError()
        command, created = _get_or_create_command(session, workspace, learner_id, "COMPLETE", idempotency_key or f"complete:{session.id}")
        if not created:
            return session
        session.complete()
        session.save()
        command.status = ToolInvocationLifecycleStatus.COMPLETED
        command.completed_at = timezone.now()
        command.save()
        _publish_event("StudyToolSessionCompleted", workspace.id, learner_id, session.id)
        return session


class FailWorkspaceToolSessionService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, session_id, *, failure_kind="TERMINAL_SESSION_FAILURE", failure_code="", idempotency_key=""):
        workspace, session = _get_session(workspace_id, learner_id, session_id)
        if session.status == WorkspaceToolSessionStatus.COMPLETED:
            raise ToolSessionAlreadyCompletedError()
        if session.status == WorkspaceToolSessionStatus.ABANDONED:
            raise ToolSessionAbandonedError()
        command, created = _get_or_create_command(session, workspace, learner_id, "FAIL", idempotency_key or f"fail:{session.id}:{failure_kind}")
        if not created:
            return session
        session.fail()
        session.save()
        command.status = ToolInvocationLifecycleStatus.FAILED
        command.failure_code = failure_code[:64]
        command.reason_code = failure_kind[:64]
        command.completed_at = timezone.now()
        command.save()
        _publish_event("StudyToolSessionFailed", workspace.id, learner_id, session.id)
        return session


class AbandonWorkspaceToolSessionService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, session_id, *, reason_code="", idempotency_key=""):
        workspace, session = _get_session(workspace_id, learner_id, session_id)
        if session.status == WorkspaceToolSessionStatus.COMPLETED:
            raise ToolSessionAlreadyCompletedError()
        if session.status == WorkspaceToolSessionStatus.FAILED:
            raise ToolSessionFailedError()
        command, created = _get_or_create_command(session, workspace, learner_id, "ABANDON", idempotency_key or f"abandon:{session.id}")
        if not created:
            return session
        session.abandon()
        session.save()
        command.status = ToolInvocationLifecycleStatus.COMPLETED
        command.reason_code = reason_code[:64]
        command.completed_at = timezone.now()
        command.save()
        _publish_event("StudyToolSessionAbandoned", workspace.id, learner_id, session.id)
        return session


class ImportProviderArtefactService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, *, provider_context, provider_reference, artefact_type, title="", summary=""):
        workspace = _get_workspace(workspace_id, learner_id)
        adapter = _provider_adapter(provider_context)
        if adapter is None:
            raise ToolProviderUnavailableError(provider_context)
        projection = adapter.import_artefact(workspace, learner_id, provider_reference)
        artefact = StudyArtefact.objects.create(
            workspace=workspace,
            learner_id=learner_id,
            tenant_id=workspace.tenant_id,
            artefact_type=artefact_type,
            provider_context=provider_context,
            provider_reference=provider_reference,
            title=title or projection.get("title", ""),
            summary=summary or projection.get("summary", ""),
            visibility=StudyArtefactVisibility.PRIVATE,
            lifecycle=StudyArtefactLifecycle.ACTIVE,
            schema_version=str(projection.get("schema_version", "1")),
            creation_source=StudyArtefactOrigin.IMPORTED,
            native_payload=projection.get("metadata", {}),
        )
        _publish_event("StudyArtefactImported", workspace.id, learner_id, artefact.id)
        return artefact


class ExportProviderArtefactService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, artefact_id, *, provider_context):
        artefact = _get_artefact(workspace_id, learner_id, artefact_id)
        adapter = _provider_adapter(provider_context)
        if adapter is None:
            raise ToolProviderUnavailableError(provider_context)
        reference = adapter.export_artefact(artefact.workspace, artefact, learner_id)
        lineage = BuildArtefactLineageService.execute(workspace_id, learner_id, artefact.id, artefact.id, StudyArtefactLineageRelation.EXPORTED_TO, provider_context=provider_context, provider_reference=reference)
        _publish_event("StudyArtefactExported", workspace_id, learner_id, artefact.id)
        return {"provider_reference": reference, "lineage_id": str(lineage.id)}


class ShareStudyArtefactService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, artefact_id, *, visibility, recipients=None):
        artefact = _get_artefact(workspace_id, learner_id, artefact_id)
        if visibility == StudyArtefactVisibility.EXPLICIT_RECIPIENTS and not recipients:
            raise ArtefactAccessDeniedError()
        artefact.visibility = visibility
        artefact.version += 1
        artefact.save()
        if recipients:
            BuildArtefactLineageService.execute(workspace_id, learner_id, artefact.id, artefact.id, StudyArtefactLineageRelation.SHARED_WITH, provider_reference=",".join(map(str, recipients)))
        _publish_event("StudyArtefactShared", workspace_id, learner_id, artefact.id)
        return artefact


class RevokeSharingService:
    @staticmethod
    @transaction.atomic
    def execute(workspace_id, learner_id, artefact_id):
        artefact = _get_artefact(workspace_id, learner_id, artefact_id)
        artefact.visibility = StudyArtefactVisibility.PRIVATE
        artefact.version += 1
        artefact.save()
        return artefact


class ListWorkspaceArtefactsQuery:
    @staticmethod
    def execute(workspace_id, learner_id):
        workspace = _get_workspace(workspace_id, learner_id)
        return StudyArtefact.objects.filter(workspace=workspace, learner_id=learner_id).order_by("-updated_at")


class GetArtefactQuery:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id):
        return _get_artefact(workspace_id, learner_id, artefact_id)


class GetArtefactLineageQuery:
    @staticmethod
    def execute(workspace_id, learner_id, artefact_id):
        artefact = _get_artefact(workspace_id, learner_id, artefact_id)
        return StudyArtefactLineage.objects.filter(workspace=artefact.workspace).filter(Q(source_artefact=artefact) | Q(target_artefact=artefact)).order_by("created_at")


class GetTransformationRequestQuery:
    @staticmethod
    def execute(workspace_id, learner_id, request_id):
        return _get_transformation_request(workspace_id, learner_id, request_id)


def _get_artefact(workspace_id, learner_id, artefact_id):
    workspace = _get_workspace(workspace_id, learner_id)
    artefact = StudyArtefact.objects.filter(pk=artefact_id, workspace=workspace, learner_id=learner_id).first()
    if artefact is None:
        raise ArtefactNotFoundError(artefact_id)
    return artefact


def _get_transformation_request(workspace_id, learner_id, request_id):
    workspace = _get_workspace(workspace_id, learner_id)
    request = ArtefactTransformationRequest.objects.filter(pk=request_id, workspace=workspace, learner_id=learner_id).first()
    if request is None:
        raise TransformationRequestNotFoundError(request_id)
    return request


def _provider_adapter(provider_context):
    from apps.study_lab.infrastructure.adapters import ProviderAdapterRegistry

    return ProviderAdapterRegistry.get_adapter(provider_context)


def _publish_event(event_name, workspace_id, learner_id, reference_id, *, tool_key="", generation_type="", artefact_id=None, reason_code=""):
    try:
        from apps.study_lab.domain import events
        from apps.notifications.domain.events import publish_event

        mapping = {
            "StudyArtefactCreated": events.StudyArtefactCreated,
            "StudyArtefactVersioned": events.StudyArtefactVersioned,
            "StudyArtefactArchived": events.StudyArtefactArchived,
            "StudyArtefactImported": events.StudyArtefactImported,
            "StudyArtefactExported": events.StudyArtefactExported,
            "StudyArtefactShared": events.StudyArtefactShared,
            "StudyToolSessionOpened": events.StudyToolSessionOpened,
            "StudyToolSessionSuspended": events.StudyToolSessionSuspended,
            "StudyToolSessionResumed": events.StudyToolSessionResumed,
            "StudyToolSessionCompleted": events.StudyToolSessionCompleted,
            "StudyToolSessionFailed": events.StudyToolSessionFailed,
            "StudyToolSessionAbandoned": events.StudyToolSessionAbandoned,
            "StudyTransformationRequested": events.StudyTransformationRequested,
            "StudyTransformationCompleted": events.StudyTransformationCompleted,
            "StudyTransformationFailed": events.StudyTransformationFailed,
            "StudyScaffoldGenerationRequested": events.StudyScaffoldGenerationRequested,
            "StudyScaffoldGenerationStarted": events.StudyScaffoldGenerationStarted,
            "StudyScaffoldGenerationCompleted": events.StudyScaffoldGenerationCompleted,
            "StudyScaffoldGenerationFailed": events.StudyScaffoldGenerationFailed,
            "StudyScaffoldGenerationCancelled": events.StudyScaffoldGenerationCancelled,
        }
        event_cls = mapping.get(event_name)
        if event_cls is None:
            return
        if event_name == "StudyToolSessionOpened":
            event = event_cls(workspace_id, learner_id, session_id=reference_id, tool_key=tool_key)
        elif event_name in {"StudyToolSessionSuspended", "StudyToolSessionResumed", "StudyToolSessionCompleted", "StudyToolSessionFailed", "StudyToolSessionAbandoned"}:
            event = event_cls(workspace_id, learner_id, session_id=reference_id)
        elif event_name in {"StudyTransformationRequested", "StudyTransformationCompleted", "StudyTransformationFailed"}:
            event = event_cls(workspace_id, learner_id, request_id=reference_id)
        elif event_name in {"StudyScaffoldGenerationRequested", "StudyScaffoldGenerationStarted", "StudyScaffoldGenerationCompleted", "StudyScaffoldGenerationFailed", "StudyScaffoldGenerationCancelled"}:
            if event_name == "StudyScaffoldGenerationCompleted":
                event = event_cls(workspace_id, learner_id, request_id=reference_id, generation_type=generation_type, artefact_id=artefact_id)
            elif event_name == "StudyScaffoldGenerationFailed":
                event = event_cls(workspace_id, learner_id, request_id=reference_id, generation_type=generation_type, reason_code=reason_code)
            else:
                event = event_cls(workspace_id, learner_id, request_id=reference_id, generation_type=generation_type)
        else:
            event = event_cls(workspace_id, learner_id, artefact_id=reference_id)
        publish_event(event.event_type, event.payload())
    except Exception:
        pass
