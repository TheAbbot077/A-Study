from rest_framework import serializers

from apps.academic.domain.models import ContentConcept
from apps.content_intelligence.models import (
    ContentExtractionResult,
    ContentImportJob,
    ContentValidationFinding,
    ParsedConceptCandidate,
    ParsedDocument,
    ParsedSection,
    ParserPipelineRun,
)


class ParsedConceptCandidateSerializer(serializers.ModelSerializer):
    decision = serializers.SerializerMethodField()
    rejection_reasons = serializers.SerializerMethodField()
    normalized_title = serializers.SerializerMethodField()

    class Meta:
        model = ParsedConceptCandidate
        fields = [
            "id",
            "title",
            "description",
            "learning_objective",
            "sequence_number",
            "confidence",
            "decision",
            "rejection_reasons",
            "normalized_title",
            "metadata",
            "created_at",
            "updated_at",
        ]

    def get_decision(self, obj):
        return (obj.metadata or {}).get("decision")

    def get_rejection_reasons(self, obj):
        return (obj.metadata or {}).get("rejection_reasons", [])

    def get_normalized_title(self, obj):
        return (obj.metadata or {}).get("normalized_title", obj.title)


class ParsedSectionSerializer(serializers.ModelSerializer):
    concept_candidates = ParsedConceptCandidateSerializer(many=True, read_only=True)
    section_origin = serializers.SerializerMethodField()

    class Meta:
        model = ParsedSection
        fields = [
            "id",
            "heading",
            "body_text",
            "sequence_number",
            "section_type",
            "section_origin",
            "confidence",
            "metadata",
            "concept_candidates",
            "created_at",
            "updated_at",
        ]

    def get_section_origin(self, obj):
        return (obj.metadata or {}).get("section_origin", "unknown")


class ParsedDocumentSerializer(serializers.ModelSerializer):
    sections = ParsedSectionSerializer(many=True, read_only=True)
    cleaned_semantic_text = serializers.SerializerMethodField()

    class Meta:
        model = ParsedDocument
        fields = [
            "id",
            "import_job",
            "title",
            "normalized_text",
            "cleaned_semantic_text",
            "format_type",
            "extraction_method",
            "page_count",
            "metadata",
            "sections",
            "created_at",
            "updated_at",
        ]

    def get_cleaned_semantic_text(self, obj):
        return (obj.metadata or {}).get("cleaned_semantic_text", obj.normalized_text)


class ContentExtractionResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentExtractionResult
        fields = [
            "id",
            "import_job",
            "extraction_method",
            "sufficient_text",
            "ocr_requested",
            "ocr_used",
            "char_count",
            "page_count",
            "metadata",
            "created_at",
            "updated_at",
        ]


class ContentValidationFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentValidationFinding
        fields = ["id", "severity", "finding_type", "message", "metadata", "created_at"]


class ParserPipelineRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParserPipelineRun
        fields = ["id", "status", "current_stage", "metadata", "started_at", "completed_at", "created_at", "updated_at"]


class ContentImportJobSerializer(serializers.ModelSerializer):
    extraction_result = ContentExtractionResultSerializer(read_only=True)
    validation_findings = ContentValidationFindingSerializer(many=True, read_only=True)
    pipeline_runs = ParserPipelineRunSerializer(many=True, read_only=True)
    status_detail = serializers.SerializerMethodField()
    retry_count = serializers.SerializerMethodField()
    failure_details = serializers.SerializerMethodField()
    resource_ready_for_learning = serializers.SerializerMethodField()
    concept_quality_summary = serializers.SerializerMethodField()
    processing_job_id = serializers.SerializerMethodField()
    processing_status = serializers.SerializerMethodField()
    processing_stage = serializers.SerializerMethodField()
    processing_progress = serializers.SerializerMethodField()
    processing_stage_label = serializers.SerializerMethodField()
    processing_message = serializers.SerializerMethodField()
    processing_attempt = serializers.SerializerMethodField()
    processing_warning_count = serializers.SerializerMethodField()
    can_retry_processing = serializers.SerializerMethodField()
    can_cancel_processing = serializers.SerializerMethodField()
    review_required = serializers.SerializerMethodField()
    ready_for_teaching = serializers.SerializerMethodField()
    processing_failure = serializers.SerializerMethodField()
    processing_completed_at = serializers.SerializerMethodField()
    proposal = serializers.SerializerMethodField()

    class Meta:
        model = ContentImportJob
        fields = [
            "id",
            "learning_resource",
            "stored_file",
            "format_type",
            "status",
            "status_detail",
            "requested_by",
            "error_message",
            "ocr_requested",
            "ocr_used",
            "extraction_confidence",
            "section_confidence",
            "concept_confidence",
            "structural_confidence",
            "metadata",
            "retry_count",
            "failure_details",
            "resource_ready_for_learning",
            "concept_quality_summary",
            "processing_job_id",
            "processing_status",
            "processing_stage",
            "processing_progress",
            "processing_stage_label",
            "processing_message",
            "processing_attempt",
            "processing_warning_count",
            "can_retry_processing",
            "can_cancel_processing",
            "review_required",
            "ready_for_teaching",
            "processing_failure",
            "processing_completed_at",
            "proposal",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "extraction_result",
            "validation_findings",
            "pipeline_runs",
        ]
        read_only_fields = [
            "id",
            "format_type",
            "status",
            "error_message",
            "ocr_requested",
            "ocr_used",
            "extraction_confidence",
            "section_confidence",
            "concept_confidence",
            "structural_confidence",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "extraction_result",
            "validation_findings",
            "pipeline_runs",
        ]

    def get_status_detail(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        if processing_job is not None and processing_job.status == "ready_for_review":
            return "review_required"
        if obj.status == ContentImportJob.Status.COMPLETED and obj.validation_findings.exists():
            return "completed_with_warnings"
        return obj.status

    def get_retry_count(self, obj):
        return int((obj.metadata or {}).get("retry_count", 0) or 0)

    def get_failure_details(self, obj):
        return (obj.metadata or {}).get("failure")

    def get_resource_ready_for_learning(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        if processing_job is not None and processing_job.status == "ready_for_teaching":
            return True
        if obj.status != ContentImportJob.Status.COMPLETED:
            return False
        learning_resource = getattr(obj, "learning_resource", None)
        if learning_resource is None:
            return False
        has_sections = learning_resource.content_sections.exists()
        has_concepts = ContentConcept.objects.filter(content_section__learning_resource=learning_resource).exists()
        return has_sections and has_concepts

    def get_concept_quality_summary(self, obj):
        return (obj.metadata or {}).get("content_quality", {})

    def get_processing_job_id(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        return str(processing_job.id) if processing_job is not None else None

    def get_processing_status(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        if processing_job is None:
            return None
        return processing_job.flattened_status()

    def get_processing_stage(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        return getattr(processing_job, "current_stage", None)

    def get_processing_progress(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        return getattr(processing_job, "progress", None)

    def get_processing_stage_label(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        if processing_job is None:
            return None
        try:
            from apps.content_processing.application.services import STAGE_LABELS

            key = processing_job.current_stage if processing_job.status == "active" else processing_job.status
            return STAGE_LABELS.get(key, key.replace("_", " ").title())
        except Exception:
            return None

    def get_processing_message(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        if processing_job is None:
            return obj.error_message or None
        if processing_job.status == "ready_for_review":
            return "Review is required before academic content can be published."
        if processing_job.status == "ready_for_teaching":
            return "Academic content is published and ready for teaching."
        if processing_job.status == "failed":
            return (processing_job.failure or {}).get("public_message") or obj.error_message or "Processing failed."
        return None

    def get_processing_attempt(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        return getattr(processing_job, "active_attempt_number", None)

    def get_processing_warning_count(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        if processing_job is None:
            return 0
        return processing_job.diagnostics.filter(severity__in=["warning", "error", "fatal"]).count()

    def get_can_retry_processing(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        if processing_job is None:
            return False
        from apps.content_processing.application.services import RetryPolicy

        return RetryPolicy().can_retry(processing_job)

    def get_can_cancel_processing(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        if processing_job is None:
            return False
        return processing_job.status == "active" and not processing_job.cancellation_requested

    def get_review_required(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        return bool(processing_job is not None and processing_job.status == "ready_for_review")

    def get_ready_for_teaching(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        return bool(processing_job is not None and processing_job.status == "ready_for_teaching")

    def get_processing_failure(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        failure = getattr(processing_job, "failure", None) if processing_job is not None else None
        if not failure:
            return None
        return {
            "code": failure.get("code"),
            "stage": failure.get("stage"),
            "message": failure.get("public_message"),
        }

    def get_processing_completed_at(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        return getattr(processing_job, "completed_at", None)

    def get_proposal(self, obj):
        processing_job = getattr(obj, "processing_job", None)
        if processing_job is None:
            return None
        proposal = processing_job.academic_import_proposals.order_by("-created_at").first()
        if proposal is None:
            return None
        statistics = proposal.statistics or {}
        return {
            "id": str(proposal.id),
            "status": proposal.review_state,
            "decision": proposal.decision,
            "population_state": proposal.population_state,
            "proposed_section_count": int(statistics.get("section_count", 0) or 0),
            "proposed_concept_count": int(statistics.get("concept_count", 0) or 0),
            "confidence": proposal.confidence,
            "blocking_finding_count": proposal.validations.filter(passed=False, severity="blocking").count(),
        }


class CreateImportJobSerializer(serializers.Serializer):
    learning_resource = serializers.UUIDField()
    metadata = serializers.JSONField(required=False)


class RetryImportJobSerializer(serializers.Serializer):
    metadata = serializers.JSONField(required=False)
