from django.contrib import admin

from apps.content_processing.models import AcademicImportProposal, AcademicPopulationJob, ContentProcessingJob, DocumentExtraction, DocumentHierarchy, DocumentHierarchyNode, DocumentSegmentation, ExtractedBlock, HierarchyBlockClassification, ProcessingAttempt, ProcessingDiagnostic, ProcessingStageResult, ProposalDecision, ProposalEvidence, ProposalRevision, ProposalValidation, ProposedConcept, ProposedSection, SemanticSegment, SourceDocumentProfile


@admin.register(ContentProcessingJob)
class ContentProcessingJobAdmin(admin.ModelAdmin):
    list_display = ("id", "resource", "status", "current_stage", "progress", "pipeline_version", "active_attempt_number", "updated_at")
    list_filter = ("status", "current_stage", "pipeline_version")
    search_fields = ("id", "resource__title", "stored_file__original_filename")
    readonly_fields = ("id", "created_at", "updated_at", "queued_at", "started_at", "completed_at", "last_transition_at", "transition_version", "failure")


@admin.register(ProcessingAttempt)
class ProcessingAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "attempt_number", "trigger", "restart_stage", "status", "created_at")
    list_filter = ("status", "trigger", "restart_stage")
    search_fields = ("id", "job__id", "correlation_id", "task_id")
    readonly_fields = ("id", "created_at", "started_at", "completed_at", "failure", "diagnostic_summary")


@admin.register(ProcessingDiagnostic)
class ProcessingDiagnosticAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "attempt", "stage", "severity", "code", "created_at")
    list_filter = ("severity", "stage", "code")
    search_fields = ("id", "job__id", "public_message", "code")
    readonly_fields = ("id", "created_at", "details", "internal_message")


@admin.register(ProcessingStageResult)
class ProcessingStageResultAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "attempt", "stage", "result_version", "completed_at")
    list_filter = ("stage", "pipeline_version")
    search_fields = ("id", "job__id", "idempotency_key")
    readonly_fields = ("id", "created_at", "completed_at", "output_references", "checksum")


class EvidenceAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SourceDocumentProfile)
class SourceDocumentProfileAdmin(EvidenceAdmin):
    list_display = ("id", "job", "attempt", "detected_format", "page_count", "text_classification", "ocr_requirement", "inspection_confidence", "created_at")
    list_filter = ("detected_format", "text_classification", "ocr_requirement", "encrypted", "corrupt")
    search_fields = ("id", "job__id", "source_filename", "source_checksum")
    readonly_fields = tuple(field.name for field in SourceDocumentProfile._meta.fields)


@admin.register(DocumentExtraction)
class DocumentExtractionAdmin(EvidenceAdmin):
    list_display = ("id", "job", "source_document_profile", "extractor_name", "extractor_version", "extraction_method", "block_count", "warning_count", "completed_at")
    list_filter = ("extraction_method", "status", "extractor_name")
    search_fields = ("id", "job__id", "source_checksum", "result_checksum")
    readonly_fields = tuple(field.name for field in DocumentExtraction._meta.fields)


@admin.register(ExtractedBlock)
class ExtractedBlockAdmin(EvidenceAdmin):
    list_display = ("id", "document_extraction", "sequence_number", "block_type", "evidence_origin", "text_preview", "confidence")
    list_filter = ("block_type", "evidence_origin", "source_method")
    search_fields = ("id", "document_extraction__id", "normalized_text")
    readonly_fields = tuple(field.name for field in ExtractedBlock._meta.fields)

    @admin.display(description="Text")
    def text_preview(self, obj):
        return obj.normalized_text[:120]


@admin.register(DocumentHierarchy)
class DocumentHierarchyAdmin(EvidenceAdmin):
    list_display = ("id", "job", "attempt", "reconstructor_name", "reconstructor_version", "node_count", "maximum_depth", "confidence", "review_recommended")
    list_filter = ("reconstructor_name", "review_recommended", "front_matter_detected", "back_matter_detected")
    search_fields = ("id", "job__id", "result_checksum")
    readonly_fields = tuple(field.name for field in DocumentHierarchy._meta.fields)


@admin.register(DocumentHierarchyNode)
class DocumentHierarchyNodeAdmin(EvidenceAdmin):
    list_display = ("id", "document_hierarchy", "parent_node", "node_type", "structural_role", "title", "depth", "ordinal", "start_sequence", "end_sequence", "confidence")
    list_filter = ("node_type", "structural_role", "evidence_strength", "depth")
    search_fields = ("id", "document_hierarchy__id", "title", "normalized_title")
    readonly_fields = tuple(field.name for field in DocumentHierarchyNode._meta.fields)


@admin.register(HierarchyBlockClassification)
class HierarchyBlockClassificationAdmin(EvidenceAdmin):
    list_display = ("id", "document_hierarchy", "extracted_block", "disposition", "structural_role", "reason_code", "confidence")
    list_filter = ("disposition", "structural_role", "reason_code")
    readonly_fields = tuple(field.name for field in HierarchyBlockClassification._meta.fields)


@admin.register(DocumentSegmentation)
class DocumentSegmentationAdmin(EvidenceAdmin):
    list_display = ("id", "job", "document_hierarchy", "segmenter_name", "segmenter_version", "segment_count", "confidence", "review_recommended")
    list_filter = ("segmenter_name", "review_recommended")
    search_fields = ("id", "job__id", "result_checksum")
    readonly_fields = tuple(field.name for field in DocumentSegmentation._meta.fields)


@admin.register(SemanticSegment)
class SemanticSegmentAdmin(EvidenceAdmin):
    list_display = ("id", "document_segmentation", "hierarchy_node", "segment_type", "ordinal", "text_preview", "character_count", "confidence")
    list_filter = ("segment_type", "evidence_strength")
    search_fields = ("id", "title", "normalized_text")
    readonly_fields = tuple(field.name for field in SemanticSegment._meta.fields)

    @admin.display(description="Text")
    def text_preview(self, obj):
        return obj.normalized_text[:120]


@admin.register(AcademicImportProposal)
class AcademicImportProposalAdmin(EvidenceAdmin):
    list_display = ("id", "job", "attempt", "resource", "review_state", "decision", "population_state", "confidence", "review_required", "created_at")
    list_filter = ("review_state", "decision", "population_state", "review_required", "proposal_engine")
    search_fields = ("id", "job__id", "resource__title", "result_checksum")
    readonly_fields = tuple(field.name for field in AcademicImportProposal._meta.fields)


@admin.register(ProposedSection)
class ProposedSectionAdmin(EvidenceAdmin):
    list_display = ("id", "proposal", "ordering", "title", "hierarchy_node", "confidence", "populated_section")
    search_fields = ("id", "proposal__id", "title", "normalized_title")
    readonly_fields = tuple(field.name for field in ProposedSection._meta.fields)


@admin.register(ProposedConcept)
class ProposedConceptAdmin(EvidenceAdmin):
    list_display = ("id", "proposal", "proposed_section", "ordering", "title", "semantic_segment", "confidence", "populated_concept")
    search_fields = ("id", "proposal__id", "title", "normalized_title")
    readonly_fields = tuple(field.name for field in ProposedConcept._meta.fields)


@admin.register(ProposalEvidence)
class ProposalEvidenceAdmin(EvidenceAdmin):
    list_display = ("id", "proposal", "item_type", "proposed_section", "proposed_concept", "hierarchy_node", "semantic_segment", "extracted_block", "confidence")
    list_filter = ("item_type", "evidence_strength")
    readonly_fields = tuple(field.name for field in ProposalEvidence._meta.fields)


@admin.register(ProposalValidation)
class ProposalValidationAdmin(EvidenceAdmin):
    list_display = ("id", "proposal", "code", "severity", "passed", "created_at")
    list_filter = ("severity", "passed", "code")
    readonly_fields = tuple(field.name for field in ProposalValidation._meta.fields)


@admin.register(ProposalDecision)
class ProposalDecisionAdmin(EvidenceAdmin):
    list_display = ("id", "proposal", "decision", "decided_by", "created_at")
    list_filter = ("decision",)
    readonly_fields = tuple(field.name for field in ProposalDecision._meta.fields)


@admin.register(ProposalRevision)
class ProposalRevisionAdmin(EvidenceAdmin):
    list_display = ("id", "proposal", "revision_number", "changed_by", "created_at")
    readonly_fields = tuple(field.name for field in ProposalRevision._meta.fields)


@admin.register(AcademicPopulationJob)
class AcademicPopulationJobAdmin(EvidenceAdmin):
    list_display = ("id", "proposal", "status", "created_sections", "updated_sections", "created_concepts", "updated_concepts", "started_at", "completed_at")
    list_filter = ("status", "population_version", "academic_schema_version")
    search_fields = ("id", "proposal__id", "job__id", "checksum")
    readonly_fields = tuple(field.name for field in AcademicPopulationJob._meta.fields)
