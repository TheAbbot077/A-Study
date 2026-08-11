from django.contrib import admin

from apps.study_lab.domain.models import ArtefactTransformationRequest, LearnerWorkspaceNote, StudyArtefact, StudyArtefactLineage, StudyArtefactTransformationDefinition, StudyToolDefinition, StudyToolManifest, StudyWorkspace, WorkspaceActivity, WorkspaceContext, WorkspacePanelDefinition, WorkspaceResumeState, WorkspaceSnapshot, WorkspaceToolAvailability, WorkspaceToolInvocation, WorkspaceToolSession, WorkspaceToolSessionCommand


@admin.register(StudyWorkspace)
class StudyWorkspaceAdmin(admin.ModelAdmin):
    list_display = ("id", "learner", "tenant", "workspace_type", "status", "last_opened_at", "created_at")
    list_filter = ("workspace_type", "status")
    search_fields = ("id", "learner__email", "title")
    readonly_fields = tuple(field.name for field in StudyWorkspace._meta.fields)


@admin.register(WorkspaceContext)
class WorkspaceContextAdmin(admin.ModelAdmin):
    list_display = ("id", "workspace", "version", "updated_at")
    readonly_fields = tuple(field.name for field in WorkspaceContext._meta.fields)


@admin.register(WorkspaceResumeState)
class WorkspaceResumeStateAdmin(admin.ModelAdmin):
    list_display = ("id", "workspace", "last_panel_key", "last_activity_type", "version")
    readonly_fields = tuple(field.name for field in WorkspaceResumeState._meta.fields)


@admin.register(WorkspacePanelDefinition)
class WorkspacePanelDefinitionAdmin(admin.ModelAdmin):
    list_display = ("panel_key", "display_name", "provider_context", "status", "sort_order")


@admin.register(StudyToolDefinition)
class StudyToolDefinitionAdmin(admin.ModelAdmin):
    list_display = ("tool_key", "display_name", "instrument_family", "provider_context", "status")


@admin.register(StudyToolManifest)
class StudyToolManifestAdmin(admin.ModelAdmin):
    list_display = ("tool_definition", "manifest_version", "status", "supports_resume", "supports_transformation")


@admin.register(WorkspaceToolSession)
class WorkspaceToolSessionAdmin(admin.ModelAdmin):
    list_display = ("workspace", "learner", "tool_definition", "status", "opened_at")
    readonly_fields = tuple(field.name for field in WorkspaceToolSession._meta.fields)


@admin.register(WorkspaceToolSessionCommand)
class WorkspaceToolSessionCommandAdmin(admin.ModelAdmin):
    list_display = ("workspace", "learner", "session", "operation", "status", "created_at")
    readonly_fields = tuple(field.name for field in WorkspaceToolSessionCommand._meta.fields)


@admin.register(WorkspaceToolAvailability)
class WorkspaceToolAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("workspace", "tool_definition", "available", "reason_code", "evaluated_at")
    readonly_fields = tuple(field.name for field in WorkspaceToolAvailability._meta.fields)


@admin.register(WorkspaceToolInvocation)
class WorkspaceToolInvocationAdmin(admin.ModelAdmin):
    list_display = ("workspace", "learner", "tool_definition", "status", "requested_at")
    readonly_fields = tuple(field.name for field in WorkspaceToolInvocation._meta.fields)


@admin.register(WorkspaceSnapshot)
class WorkspaceSnapshotAdmin(admin.ModelAdmin):
    list_display = ("workspace", "snapshot_version", "status", "assembled_at")
    readonly_fields = tuple(field.name for field in WorkspaceSnapshot._meta.fields)


@admin.register(LearnerWorkspaceNote)
class LearnerWorkspaceNoteAdmin(admin.ModelAdmin):
    list_display = ("workspace", "learner", "title", "status", "updated_at")
    readonly_fields = tuple(field.name for field in LearnerWorkspaceNote._meta.fields)


@admin.register(WorkspaceActivity)
class WorkspaceActivityAdmin(admin.ModelAdmin):
    list_display = ("workspace", "learner", "activity_type", "occurred_at")
    readonly_fields = tuple(field.name for field in WorkspaceActivity._meta.fields)


@admin.register(StudyArtefact)
class StudyArtefactAdmin(admin.ModelAdmin):
    list_display = ("workspace", "learner", "artefact_type", "visibility", "lifecycle", "version")
    readonly_fields = tuple(field.name for field in StudyArtefact._meta.fields)


@admin.register(StudyArtefactLineage)
class StudyArtefactLineageAdmin(admin.ModelAdmin):
    list_display = ("workspace", "source_artefact", "target_artefact", "relation_type", "created_at")
    readonly_fields = tuple(field.name for field in StudyArtefactLineage._meta.fields)


@admin.register(StudyArtefactTransformationDefinition)
class StudyArtefactTransformationDefinitionAdmin(admin.ModelAdmin):
    list_display = ("transformation_key", "destination_type", "provider_context", "status", "version")


@admin.register(ArtefactTransformationRequest)
class ArtefactTransformationRequestAdmin(admin.ModelAdmin):
    list_display = ("workspace", "learner", "definition", "status", "requested_at")
    readonly_fields = tuple(field.name for field in ArtefactTransformationRequest._meta.fields)
