from django.contrib import admin

from apps.content_intelligence.models import (
    ContentExtractionResult,
    ContentImportJob,
    ContentValidationFinding,
    ParsedConceptCandidate,
    ParsedDocument,
    ParsedSection,
    ParserPipelineRun,
)


class ContentIntelligenceModelAdmin(admin.ModelAdmin):
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContentImportJob)
class ContentImportJobAdmin(ContentIntelligenceModelAdmin):
    list_display = (
        "learning_resource",
        "format_type",
        "status",
        "failure_reason",
        "ocr_requested",
        "ocr_used",
        "retry_count",
        "created_at",
    )
    list_filter = ("status", "format_type", "ocr_requested", "ocr_used", "created_at")
    search_fields = ("learning_resource__title", "stored_file__original_filename", "error_message")
    ordering = ("-created_at",)
    list_select_related = ("learning_resource", "stored_file", "requested_by")
    readonly_fields = ("id", "created_at", "updated_at", "started_at", "completed_at", "metadata")

    def failure_reason(self, obj):
        return (obj.metadata or {}).get("failure", {}).get("failure_reason") or obj.error_message

    def retry_count(self, obj):
        return int((obj.metadata or {}).get("retry_count", 0) or 0)


@admin.register(ParsedDocument)
class ParsedDocumentAdmin(ContentIntelligenceModelAdmin):
    list_display = ("import_job", "format_type", "extraction_method", "page_count", "created_at")
    list_filter = ("format_type", "extraction_method", "created_at")
    search_fields = ("title", "import_job__learning_resource__title")
    ordering = ("-created_at",)
    list_select_related = ("import_job",)
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(ParsedSection)
class ParsedSectionAdmin(ContentIntelligenceModelAdmin):
    list_display = ("heading", "section_origin", "section_classification", "parsed_document", "sequence_number", "section_type", "confidence")
    list_filter = ("section_type", "created_at")
    search_fields = ("heading", "parsed_document__import_job__learning_resource__title")
    ordering = ("sequence_number",)
    list_select_related = ("parsed_document",)
    readonly_fields = ("id", "created_at", "updated_at")

    def section_classification(self, obj):
        return (obj.metadata or {}).get("section_classification", obj.section_type)

    def section_origin(self, obj):
        return (obj.metadata or {}).get("section_origin", "unknown")


@admin.register(ParsedConceptCandidate)
class ParsedConceptCandidateAdmin(ContentIntelligenceModelAdmin):
    list_display = ("title", "normalized_title", "decision", "parsed_section", "sequence_number", "confidence", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "parsed_section__heading", "parsed_section__parsed_document__import_job__learning_resource__title")
    ordering = ("sequence_number",)
    list_select_related = ("parsed_section",)
    readonly_fields = ("id", "created_at", "updated_at", "metadata")

    def normalized_title(self, obj):
        return (obj.metadata or {}).get("normalized_title", obj.title)

    def decision(self, obj):
        return (obj.metadata or {}).get("decision", "unknown")


@admin.register(ContentExtractionResult)
class ContentExtractionResultAdmin(ContentIntelligenceModelAdmin):
    list_display = (
        "import_job",
        "extraction_method",
        "sufficient_text",
        "ocr_used",
        "char_count",
        "meaningful_character_count",
        "created_at",
    )
    list_filter = ("sufficient_text", "ocr_requested", "ocr_used", "created_at")
    search_fields = ("import_job__learning_resource__title", "extraction_method")
    ordering = ("-created_at",)
    list_select_related = ("import_job",)
    readonly_fields = ("id", "created_at", "updated_at", "metadata")

    def meaningful_character_count(self, obj):
        return (obj.metadata or {}).get("meaningful_character_count")


@admin.register(ContentValidationFinding)
class ContentValidationFindingAdmin(ContentIntelligenceModelAdmin):
    list_display = ("import_job", "severity", "finding_type", "created_at")
    list_filter = ("severity", "finding_type", "created_at")
    search_fields = ("import_job__learning_resource__title", "message")
    ordering = ("-created_at",)
    list_select_related = ("import_job",)
    readonly_fields = ("id", "created_at")


@admin.register(ParserPipelineRun)
class ParserPipelineRunAdmin(ContentIntelligenceModelAdmin):
    list_display = ("import_job", "status", "current_stage", "started_at", "completed_at")
    list_filter = ("status", "current_stage", "created_at")
    search_fields = ("import_job__learning_resource__title", "current_stage")
    ordering = ("-created_at",)
    list_select_related = ("import_job",)
    readonly_fields = ("id", "created_at", "updated_at", "started_at", "completed_at")
