from __future__ import annotations

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.academic.domain.models import LearningResource
from apps.content_processing.domain.models import ContentProcessingJob, JobStatus
from apps.core.events import BusinessEvent, EventPublisher
from apps.users.domain.models import Institution, InstitutionMembership, InstitutionRole, User

from ..bridge_models import BridgePlanStatus
from ..diagnostic_models import DiagnosticStatus
from ..domain.workspace import SelfStudyNextAction, WorkspaceBlockerCode, build_next_action
from ..evidence_models import CoverageStatus
from ..models import IntentStatus, SelfStudyIntent
from ..orchestration_models import SelfStudyTeachingSessionState
from ..teaching_models import TeachingPreparationManifestStatus
from ..workspace_models import SelfStudyWorkspace, SelfStudyWorkspaceMaterial, SelfStudyWorkspaceStatus, WorkspaceMaterialStatus
from .services import _has_institutional_authority


WORKSPACE_EDITABLE_FIELDS = {"display_name", "description"}


def _publish(events: EventPublisher, name: str, workspace: SelfStudyWorkspace, extra: dict | None = None) -> None:
    payload = {
        "workspace_id": str(workspace.id),
        "tenant_id": str(workspace.tenant_id),
        "learner_id": str(workspace.learner_id),
        "version": workspace.version,
    }
    payload.update(extra or {})
    events.publish(BusinessEvent.create(name, payload=payload))


def _active_membership(actor: User, tenant_id) -> bool:
    if actor.is_superuser:
        return True
    return InstitutionMembership.objects.filter(user=actor, institution_id=tenant_id, is_active=True).exists()


def _default_tenant_for(actor: User) -> Institution:
    memberships = list(
        InstitutionMembership.objects.filter(user=actor, is_active=True).select_related("institution").order_by("created_at")[:2]
    )
    if len(memberships) != 1:
        raise ValidationError("A tenant_id is required for this workspace.", code=WorkspaceBlockerCode.TENANT_SCOPE_REQUIRED.value)
    return memberships[0].institution


def ensure_workspace_access(actor: User, workspace: SelfStudyWorkspace, *, mutate: bool = False) -> None:
    if workspace.status == SelfStudyWorkspaceStatus.ARCHIVED and mutate:
        raise ValidationError("Archived workspaces cannot be modified.", code=WorkspaceBlockerCode.WORKSPACE_ARCHIVED.value)
    if actor.id == workspace.learner_id:
        return
    if _has_institutional_authority(actor, workspace.tenant_id):
        return
    raise PermissionDenied(WorkspaceBlockerCode.WORKSPACE_OWNER_MISMATCH.value)


def project_material_status(resource: LearningResource, job: ContentProcessingJob | None) -> tuple[str, list[str], dict[str, str]]:
    summary = {"resource_status": resource.status}
    blockers: list[str] = []
    if resource.status == LearningResource.Status.ARCHIVED:
        return WorkspaceMaterialStatus.RETIRED, [WorkspaceBlockerCode.MATERIAL_RETIRED.value], summary
    if job is None:
        return WorkspaceMaterialStatus.UPLOADED, [], summary
    summary.update({"processing_status": job.status, "processing_stage": job.current_stage})
    if job.status == JobStatus.ACTIVE:
        return WorkspaceMaterialStatus.PROCESSING, [WorkspaceBlockerCode.MATERIALS_PROCESSING.value], summary
    if job.status == JobStatus.READY_FOR_TEACHING:
        return WorkspaceMaterialStatus.ELIGIBLE, [], summary
    if job.status == JobStatus.READY_FOR_REVIEW:
        return WorkspaceMaterialStatus.PROCESSED, [], summary
    if job.status == JobStatus.CANCELLED:
        return WorkspaceMaterialStatus.INELIGIBLE, [WorkspaceBlockerCode.MATERIAL_PROCESSING_FAILED.value], summary
    if job.status == JobStatus.DELETED:
        return WorkspaceMaterialStatus.RETIRED, [WorkspaceBlockerCode.MATERIAL_RETIRED.value], summary
    if job.status == JobStatus.FAILED:
        failure_code = (job.failure or {}).get("code", "")
        if failure_code == "unsupported_format":
            return WorkspaceMaterialStatus.UNSUPPORTED_FORMAT, [WorkspaceBlockerCode.MATERIAL_UNSUPPORTED_FORMAT.value], summary
        return WorkspaceMaterialStatus.EXTRACTION_FAILED, [WorkspaceBlockerCode.MATERIAL_PROCESSING_FAILED.value], summary
    return WorkspaceMaterialStatus.INELIGIBLE, [WorkspaceBlockerCode.UNEXPECTED_STATE.value], summary


@dataclass(frozen=True)
class WorkspaceSummary:
    workspace: SelfStudyWorkspace
    next_action: dict
    material_counts: dict[str, int]
    blockers: list[str]

    def to_dict(self) -> dict:
        return {
            "workspace_id": str(self.workspace.id),
            "status": self.workspace.status,
            "version": self.workspace.version,
            "next_action": self.next_action,
            "material_counts": self.material_counts,
            "blocker_codes": self.blockers,
        }


class SelfStudyWorkspaceService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    def list_for_actor(self, *, actor: User):
        queryset = SelfStudyWorkspace.objects.select_related("tenant", "learner", "intent").order_by("-updated_at")
        if actor.is_superuser:
            return queryset
        authoritative_tenants = InstitutionMembership.objects.filter(
            user=actor,
            is_active=True,
            role__in=[
                InstitutionRole.ADMINISTRATOR,
                InstitutionRole.INSTITUTION_OWNER,
                InstitutionRole.SYSTEM_ADMINISTRATOR,
            ],
        ).values("institution_id")
        return queryset.filter(learner=actor) | queryset.filter(tenant_id__in=authoritative_tenants)

    def get_for_actor(self, *, workspace_id, actor: User) -> SelfStudyWorkspace:
        workspace = SelfStudyWorkspace.objects.select_related(
            "tenant",
            "learner",
            "intent",
            "curriculum_resolution",
            "published_graph",
            "active_diagnostic",
            "latest_coverage_evaluation",
            "active_bridge_plan",
            "active_teaching_preparation",
            "active_teaching_session",
        ).get(id=workspace_id)
        ensure_workspace_access(actor, workspace)
        return workspace

    @transaction.atomic
    def create(self, *, actor: User, display_name: str, description: str = "", tenant_id=None, idempotency_key: str = ""):
        tenant = Institution.objects.get(id=tenant_id) if tenant_id else _default_tenant_for(actor)
        if not _active_membership(actor, tenant.id):
            raise PermissionDenied(WorkspaceBlockerCode.PERMISSION_DENIED.value)
        if idempotency_key:
            existing = SelfStudyWorkspace.objects.filter(
                learner=actor,
                tenant=tenant,
                idempotency_key=idempotency_key,
            ).first()
            if existing:
                return existing
        workspace = SelfStudyWorkspace(
            learner=actor,
            tenant=tenant,
            display_name=display_name.strip(),
            description=description.strip(),
            idempotency_key=idempotency_key,
        )
        workspace.full_clean()
        workspace.save()
        transaction.on_commit(lambda: _publish(self.events, "self_study.workspace.created", workspace))
        return workspace

    @transaction.atomic
    def update(self, *, workspace_id, actor: User, expected_version: int, changes: dict):
        workspace = SelfStudyWorkspace.objects.select_for_update().get(id=workspace_id)
        ensure_workspace_access(actor, workspace, mutate=True)
        if workspace.version != expected_version:
            raise ValidationError("Workspace version is stale.", code="WORKSPACE_VERSION_CONFLICT")
        unknown = set(changes) - WORKSPACE_EDITABLE_FIELDS
        if unknown:
            raise ValidationError("Workspace field is not editable.", code=WorkspaceBlockerCode.INVALID_STATE_TRANSITION.value)
        for field, value in changes.items():
            setattr(workspace, field, value.strip() if isinstance(value, str) else value)
        workspace.version += 1
        workspace.full_clean()
        workspace.save()
        transaction.on_commit(lambda: _publish(self.events, "self_study.workspace.updated", workspace))
        return workspace

    @transaction.atomic
    def archive(self, *, workspace_id, actor: User, expected_version: int):
        workspace = SelfStudyWorkspace.objects.select_for_update().get(id=workspace_id)
        ensure_workspace_access(actor, workspace, mutate=True)
        if workspace.version != expected_version:
            raise ValidationError("Workspace version is stale.", code="WORKSPACE_VERSION_CONFLICT")
        changed = workspace.archive(when=timezone.now())
        if changed:
            workspace.save(update_fields=["status", "archived_at", "version", "updated_at"])
            transaction.on_commit(lambda: _publish(self.events, "self_study.workspace.archived", workspace))
        return workspace

    @transaction.atomic
    def attach_intent(self, *, workspace_id, actor: User, intent_id, expected_version: int):
        workspace = SelfStudyWorkspace.objects.select_for_update().get(id=workspace_id)
        ensure_workspace_access(actor, workspace, mutate=True)
        if workspace.version != expected_version:
            raise ValidationError("Workspace version is stale.", code="WORKSPACE_VERSION_CONFLICT")
        intent = SelfStudyIntent.objects.get(id=intent_id)
        if intent.learner_id != workspace.learner_id or intent.tenant_id != workspace.tenant_id:
            raise PermissionDenied(WorkspaceBlockerCode.PERMISSION_DENIED.value)
        workspace.intent = intent
        workspace.status = SelfStudyWorkspaceStatus.INTENT_IN_PROGRESS if intent.status == IntentStatus.DRAFT else workspace.status
        workspace.version += 1
        workspace.save(update_fields=["intent", "status", "version", "updated_at"])
        transaction.on_commit(lambda: _publish(self.events, "self_study.workspace.intent_attached", workspace, {"intent_id": str(intent.id)}))
        return workspace


class SelfStudyWorkspaceMaterialService:
    def __init__(self, events: EventPublisher | None = None):
        self.events = events or EventPublisher()

    def list_materials(self, *, workspace: SelfStudyWorkspace):
        return workspace.materials.select_related("resource", "content_processing_job").order_by("created_at", "resource_id")

    @transaction.atomic
    def attach_existing_resource(self, *, workspace_id, actor: User, resource_id, content_processing_job_id=None, idempotency_key: str = ""):
        workspace = SelfStudyWorkspace.objects.select_for_update().get(id=workspace_id)
        ensure_workspace_access(actor, workspace, mutate=True)
        resource = LearningResource.objects.get(id=resource_id)
        if resource.subject.institution_id != workspace.tenant_id:
            raise PermissionDenied(WorkspaceBlockerCode.PERMISSION_DENIED.value)
        job = None
        if content_processing_job_id:
            job = ContentProcessingJob.objects.get(id=content_processing_job_id)
            if job.resource_id != resource.id:
                raise ValidationError("Processing job does not belong to the resource.", code=WorkspaceBlockerCode.INVALID_STATE_TRANSITION.value)
        else:
            job = resource.content_processing_jobs.exclude(status=JobStatus.DELETED).order_by("-created_at").first()
        status, blockers, summary = project_material_status(resource, job)
        if idempotency_key:
            existing = SelfStudyWorkspaceMaterial.objects.filter(workspace=workspace, idempotency_key=idempotency_key).first()
            if existing:
                return self.refresh_material(existing)
        material, created = SelfStudyWorkspaceMaterial.objects.get_or_create(
            workspace=workspace,
            resource=resource,
            defaults={
                "content_processing_job": job,
                "status": status,
                "blocker_codes": blockers,
                "safe_status_summary": summary,
                "idempotency_key": idempotency_key,
                "attached_by": actor,
            },
        )
        if not created:
            material.content_processing_job = job or material.content_processing_job
            material.status = status
            material.blocker_codes = blockers
            material.safe_status_summary = summary
            material.version += 1
            material.save()
        transaction.on_commit(
            lambda: _publish(
                self.events,
                "self_study.workspace.resource_attached",
                workspace,
                {"resource_id": str(resource.id), "material_id": str(material.id)},
            )
        )
        return material

    def refresh_material(self, material: SelfStudyWorkspaceMaterial):
        status, blockers, summary = project_material_status(material.resource, material.content_processing_job)
        material.status = status
        material.blocker_codes = blockers
        material.safe_status_summary = summary
        material.version += 1
        material.save(update_fields=["status", "blocker_codes", "safe_status_summary", "version", "updated_at"])
        return material


class SelfStudyOnboardingService:
    def __init__(self, material_service: SelfStudyWorkspaceMaterialService | None = None):
        self.material_service = material_service or SelfStudyWorkspaceMaterialService()

    def summarize(self, *, workspace: SelfStudyWorkspace) -> WorkspaceSummary:
        materials = list(self.material_service.list_materials(workspace=workspace))
        material_counts: dict[str, int] = {}
        blockers: list[str] = []
        for material in materials:
            material_counts[material.status] = material_counts.get(material.status, 0) + 1
            blockers.extend(code for code in material.blocker_codes if code not in blockers)
        action = self.next_action(workspace=workspace, material_counts=material_counts, blockers=blockers)
        return WorkspaceSummary(workspace=workspace, next_action=action.to_dict(), material_counts=material_counts, blockers=blockers)

    def next_action(self, *, workspace: SelfStudyWorkspace, material_counts: dict[str, int] | None = None, blockers: list[str] | None = None):
        material_counts = material_counts or {}
        blockers = list(blockers or [])
        safe_ids = {"workspace_id": str(workspace.id)}
        summary = {"workspace_status": workspace.status}

        if workspace.status == SelfStudyWorkspaceStatus.ARCHIVED:
            return build_next_action(
                SelfStudyNextAction.CONTACT_SUPPORT,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.WORKSPACE_ARCHIVED.value],
                safe_ids=safe_ids,
                summary=summary,
            )
        if not workspace.intent_id:
            return build_next_action(
                SelfStudyNextAction.COMPLETE_INTENT,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.INTENT_REQUIRED.value],
                safe_ids=safe_ids,
                summary=summary,
            )
        intent = workspace.intent
        safe_ids["intent_id"] = str(intent.id)
        summary["intent_status"] = intent.status
        intent_blockers = intent.readiness_blockers()
        if intent.status == IntentStatus.DRAFT or intent_blockers:
            mapped = [WorkspaceBlockerCode.INTENT_INCOMPLETE.value]
            if "POLICY_ACKNOWLEDGEMENT_REQUIRED" in intent_blockers:
                mapped.append(WorkspaceBlockerCode.RESOURCE_POLICY_ACKNOWLEDGEMENT_REQUIRED.value)
            return build_next_action(
                SelfStudyNextAction.COMPLETE_INTENT,
                workspace_id=str(workspace.id),
                blockers=mapped,
                safe_ids=safe_ids,
                summary=summary,
            )

        if not material_counts:
            return build_next_action(
                SelfStudyNextAction.UPLOAD_MATERIALS,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.MATERIALS_REQUIRED.value],
                safe_ids=safe_ids,
                summary=summary,
            )
        if material_counts.get(WorkspaceMaterialStatus.PROCESSING, 0):
            return build_next_action(
                SelfStudyNextAction.WAIT_FOR_PROCESSING,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.MATERIALS_PROCESSING.value],
                safe_ids=safe_ids,
                summary=summary,
            )
        if blockers:
            return build_next_action(
                SelfStudyNextAction.RESOLVE_MATERIAL_ISSUES,
                workspace_id=str(workspace.id),
                blockers=blockers,
                safe_ids=safe_ids,
                summary=summary,
            )
        eligible_count = material_counts.get(WorkspaceMaterialStatus.ELIGIBLE, 0) + material_counts.get(WorkspaceMaterialStatus.PROCESSED, 0)
        if eligible_count == 0:
            return build_next_action(
                SelfStudyNextAction.RESOLVE_MATERIAL_ISSUES,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.NO_ELIGIBLE_MATERIALS.value],
                safe_ids=safe_ids,
                summary=summary,
            )

        diagnostic = workspace.active_diagnostic or intent.entry_diagnostics.order_by("-created_at").first()
        if diagnostic and diagnostic.status in {DiagnosticStatus.READY, DiagnosticStatus.IN_PROGRESS}:
            safe_ids["diagnostic_id"] = str(diagnostic.id)
            return build_next_action(SelfStudyNextAction.RESUME_DIAGNOSTIC, workspace_id=str(workspace.id), safe_ids=safe_ids, summary=summary)
        if not diagnostic:
            return build_next_action(
                SelfStudyNextAction.START_DIAGNOSTIC,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.DIAGNOSTIC_RESULT_REQUIRED.value],
                safe_ids=safe_ids,
                summary=summary,
            )
        if diagnostic.status in {DiagnosticStatus.SUPERSEDED, DiagnosticStatus.EXPIRED}:
            return build_next_action(
                SelfStudyNextAction.START_DIAGNOSTIC,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.DIAGNOSTIC_INVALIDATED.value],
                safe_ids=safe_ids,
                summary=summary,
            )

        coverage = workspace.latest_coverage_evaluation or getattr(workspace.active_bridge_plan, "coverage_evaluation", None)
        if not coverage:
            return build_next_action(
                SelfStudyNextAction.WAIT_FOR_MAPPING,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.COVERAGE_PENDING.value],
                safe_ids=safe_ids,
                summary=summary,
            )
        if coverage.status != CoverageStatus.COMPLETED:
            return build_next_action(
                SelfStudyNextAction.WAIT_FOR_MAPPING,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.COVERAGE_BLOCKED.value],
                safe_ids=safe_ids,
                summary=summary,
            )

        bridge_plan = workspace.active_bridge_plan or intent.bridge_plans.order_by("-created_at").first()
        if not bridge_plan:
            return build_next_action(
                SelfStudyNextAction.WAIT_FOR_BRIDGE_PLAN,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.BRIDGE_PLAN_PENDING.value],
                safe_ids=safe_ids,
                summary=summary,
            )
        safe_ids["bridge_plan_id"] = str(bridge_plan.id)
        if bridge_plan.status in {BridgePlanStatus.BLOCKED, BridgePlanStatus.STALE, BridgePlanStatus.INVALIDATED}:
            return build_next_action(
                SelfStudyNextAction.WAIT_FOR_BRIDGE_PLAN,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.BRIDGE_PLAN_BLOCKED.value],
                safe_ids=safe_ids,
                summary=summary,
            )
        if bridge_plan.status not in {BridgePlanStatus.APPROVED, BridgePlanStatus.ACTIVE}:
            return build_next_action(SelfStudyNextAction.REVIEW_STUDY_PLAN, workspace_id=str(workspace.id), safe_ids=safe_ids, summary=summary)

        preparation = workspace.active_teaching_preparation or intent.teaching_preparation_manifests.order_by("-created_at").first()
        if not preparation:
            return build_next_action(
                SelfStudyNextAction.WAIT_FOR_TEACHING_PREPARATION,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.TEACHING_PREPARATION_PENDING.value],
                safe_ids=safe_ids,
                summary=summary,
            )
        safe_ids["teaching_preparation_id"] = str(preparation.id)
        if preparation.status not in {TeachingPreparationManifestStatus.READY, TeachingPreparationManifestStatus.PUBLISHED}:
            return build_next_action(
                SelfStudyNextAction.WAIT_FOR_TEACHING_PREPARATION,
                workspace_id=str(workspace.id),
                blockers=[WorkspaceBlockerCode.TEACHING_PREPARATION_BLOCKED.value],
                safe_ids=safe_ids,
                summary=summary,
            )

        session = workspace.active_teaching_session or intent.teaching_sessions.order_by("-created_at").first()
        if session and session.state in {
            SelfStudyTeachingSessionState.ACTIVE,
            SelfStudyTeachingSessionState.AWAITING_LEARNER,
            SelfStudyTeachingSessionState.AWAITING_EVIDENCE,
            SelfStudyTeachingSessionState.PAUSED,
        }:
            safe_ids["teaching_session_id"] = str(session.id)
            return build_next_action(SelfStudyNextAction.RESUME_LEARNING, workspace_id=str(workspace.id), safe_ids=safe_ids, summary=summary)
        return build_next_action(SelfStudyNextAction.START_LEARNING, workspace_id=str(workspace.id), safe_ids=safe_ids, summary=summary)
