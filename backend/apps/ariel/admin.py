from django.contrib import admin

from apps.ariel.domain.models import (
    ArielConstitution,
    ArielCorrectionRecord,
    ArielIdentity,
    ArielKnowledgeUnit,
    ArielMemoryRecord,
    ArielMisconception,
    ArielRelationship,
    ArielReinforcementRecord,
    ArielTeachBackInteraction,
    ArielTeachingSession,
    ArielTeachingTurn,
    ArielUserCapability,
)


@admin.register(ArielConstitution)
class ArielConstitutionAdmin(admin.ModelAdmin):
    list_display = ["version", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["version"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(ArielIdentity)
class ArielIdentityAdmin(admin.ModelAdmin):
    list_display = ["display_name", "learner", "status", "constitution", "version", "created_at"]
    list_filter = ["status", "institution"]
    search_fields = ["display_name", "learner__email"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]


@admin.register(ArielRelationship)
class ArielRelationshipAdmin(admin.ModelAdmin):
    list_display = ["identity", "learner", "consent_state", "institutional_visibility", "status"]
    list_filter = ["consent_state", "institutional_visibility", "status"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]


@admin.register(ArielTeachingSession)
class ArielTeachingSessionAdmin(admin.ModelAdmin):
    list_display = ["id", "identity", "learner", "status", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]


@admin.register(ArielTeachingTurn)
class ArielTeachingTurnAdmin(admin.ModelAdmin):
    list_display = ["session", "actor", "sequence_number", "disposition", "created_at"]
    list_filter = ["actor", "disposition"]
    readonly_fields = ["id", "created_at"]


@admin.register(ArielTeachBackInteraction)
class ArielTeachBackInteractionAdmin(admin.ModelAdmin):
    list_display = ["teaching_session", "interaction_type", "status", "intensity", "created_at"]
    list_filter = ["interaction_type", "status", "intensity", "input_provenance"]
    readonly_fields = ["id", "created_at", "updated_at", "version", "presented_at", "responded_at", "resolved_at", "skipped_at", "cancelled_at", "expires_at"]


@admin.register(ArielKnowledgeUnit)
class ArielKnowledgeUnitAdmin(admin.ModelAdmin):
    list_display = ["id", "identity", "memory_state", "provenance", "confidence", "created_at"]
    list_filter = ["memory_state", "provenance"]
    readonly_fields = ["id", "created_at", "updated_at", "version"]


@admin.register(ArielMemoryRecord)
class ArielMemoryRecordAdmin(admin.ModelAdmin):
    list_display = ["identity", "knowledge_unit", "previous_state", "new_state", "created_at"]
    list_filter = ["new_state"]
    readonly_fields = ["id", "created_at"]


@admin.register(ArielMisconception)
class ArielMisconceptionAdmin(admin.ModelAdmin):
    list_display = ["identity", "knowledge_unit", "current_state", "created_at"]
    list_filter = ["current_state"]
    readonly_fields = ["id", "created_at", "updated_at"]


@admin.register(ArielCorrectionRecord)
class ArielCorrectionRecordAdmin(admin.ModelAdmin):
    list_display = ["identity", "superseded_knowledge", "replacement_knowledge", "created_at"]
    readonly_fields = ["id", "created_at"]


@admin.register(ArielReinforcementRecord)
class ArielReinforcementRecordAdmin(admin.ModelAdmin):
    list_display = ["knowledge_unit", "previous_state", "new_state", "created_at"]
    readonly_fields = ["id", "created_at"]


@admin.register(ArielUserCapability)
class ArielUserCapabilityAdmin(admin.ModelAdmin):
    list_display = ["user", "identity", "capability_code", "granted_at", "is_active"]
    list_filter = ["capability_code"]
    readonly_fields = ["id", "granted_at"]
