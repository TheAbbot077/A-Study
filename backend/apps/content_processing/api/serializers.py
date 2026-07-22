from rest_framework import serializers

from apps.content_processing.application.services import RetryPolicy, STAGE_LABELS
from apps.content_processing.models import (
    ContentProcessingJob,
    JobStatus,
    ProcessingAttempt,
    ProcessingDiagnostic,
    TeachingReadinessEvaluation,
)


class ProcessingAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingAttempt
        fields = [
            "id",
            "attempt_number",
            "trigger",
            "restart_stage",
            "status",
            "failure",
            "correlation_id",
            "task_id",
            "started_at",
            "completed_at",
            "created_at",
        ]


class ProcessingDiagnosticSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessingDiagnostic
        fields = [
            "id",
            "stage",
            "severity",
            "code",
            "public_message",
            "details",
            "source_component",
            "created_at",
        ]


class TeachingReadinessEvaluationSerializer(serializers.ModelSerializer):
    resource_id = serializers.UUIDField(read_only=True)
    subject_id = serializers.UUIDField(read_only=True)
    processing_job_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = TeachingReadinessEvaluation
        fields = (
            "id", "resource_id", "subject_id", "processing_job_id", "processing_attempt_id",
            "approved_projection_id", "approval_decision_id", "academic_population_run_id",
            "retrieval_synchronization_run_id", "retrieval_generation_id", "trigger", "reason",
            "lineage_fingerprint", "policy_version", "decision", "checks_passed", "checks_failed",
            "blocker_count", "warning_count", "snapshot", "checks", "invalidation_reason",
            "invalidated_at", "supersedes_evaluation_id", "evaluated_at",
        )


class ContentProcessingJobSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    stage = serializers.CharField(source="current_stage", read_only=True)
    stage_label = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    attempt = serializers.IntegerField(source="active_attempt_number", read_only=True)
    warning_count = serializers.SerializerMethodField()
    can_retry = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    failure = serializers.SerializerMethodField()
    processing_job_id = serializers.UUIDField(source="id", read_only=True)
    extraction_summary = serializers.SerializerMethodField()
    structure_summary = serializers.SerializerMethodField()
    proposal_summary = serializers.SerializerMethodField()
    review_required = serializers.SerializerMethodField()
    ready_for_teaching = serializers.SerializerMethodField()

    class Meta:
        model = ContentProcessingJob
        fields = [
            "processing_job_id",
            "id",
            "resource",
            "stored_file",
            "status",
            "stage",
            "progress",
            "stage_label",
            "message",
            "attempt",
            "warning_count",
            "can_retry",
            "can_cancel",
            "failure",
            "pipeline_version",
            "extraction_summary",
            "structure_summary",
            "proposal_summary",
            "review_required",
            "ready_for_teaching",
            "completed_at",
            "created_at",
            "updated_at",
        ]

    def get_status(self, obj):
        return obj.flattened_status()

    def get_stage_label(self, obj):
        key = obj.current_stage if obj.status == JobStatus.ACTIVE else obj.status
        return STAGE_LABELS.get(key, key.replace("_", " ").title())

    def get_warning_count(self, obj):
        return obj.diagnostics.filter(severity__in=["warning", "error", "fatal"]).count()

    def get_message(self, obj):
        if obj.status == JobStatus.READY_FOR_REVIEW:
            return "Review is required before academic content can be published."
        if obj.status == JobStatus.READY_FOR_TEACHING:
            return "Academic content is published and ready for teaching."
        if obj.status == JobStatus.FAILED:
            return (obj.failure or {}).get("public_message") or "Processing failed."
        return None

    def get_review_required(self, obj):
        return obj.status == JobStatus.READY_FOR_REVIEW

    def get_ready_for_teaching(self, obj):
        return obj.status == JobStatus.READY_FOR_TEACHING

    def get_can_retry(self, obj):
        return RetryPolicy().can_retry(obj)

    def get_can_cancel(self, obj):
        return obj.status == JobStatus.ACTIVE and not obj.cancellation_requested

    def get_failure(self, obj):
        if not obj.failure:
            return None
        return {
            "code": obj.failure.get("code"),
            "stage": obj.failure.get("stage"),
            "message": obj.failure.get("public_message"),
        }

    def get_extraction_summary(self, obj):
        extraction = obj.document_extractions.order_by("-created_at").first()
        profile = obj.source_profiles.order_by("-created_at").first()
        if profile is None:
            return None
        return {
            "detected_format": profile.detected_format,
            "page_count": profile.page_count,
            "text_classification": profile.text_classification,
            "ocr_requirement": profile.ocr_requirement,
            "block_count": extraction.block_count if extraction else None,
            "native_page_count": extraction.native_text_pages if extraction else None,
            "ocr_page_count": extraction.ocr_pages if extraction else None,
            "warning_count": extraction.warning_count if extraction else len(profile.warnings),
            "extractor_name": extraction.extractor_name if extraction else None,
            "extractor_version": extraction.extractor_version if extraction else None,
        }

    def get_structure_summary(self, obj):
        hierarchy = obj.document_hierarchies.order_by("-created_at").first()
        segmentation = obj.document_segmentations.order_by("-created_at").first()
        if hierarchy is None:
            return None
        return {
            "hierarchy_node_count": hierarchy.node_count,
            "maximum_hierarchy_depth": hierarchy.maximum_depth,
            "front_matter_detected": hierarchy.front_matter_detected,
            "semantic_segment_count": segmentation.segment_count if segmentation else None,
            "review_recommended": segmentation.review_recommended if segmentation else hierarchy.review_recommended,
            "warning_count": hierarchy.warning_count + (segmentation.warning_count if segmentation else 0),
        }

    def get_proposal_summary(self, obj):
        proposal = obj.academic_import_proposals.order_by("-created_at").first()
        if proposal is None:
            return None
        population = proposal.population_jobs.order_by("-created_at").first()
        return {
            "id": str(proposal.id),
            "review_state": proposal.review_state,
            "decision": proposal.decision,
            "population_state": proposal.population_state,
            "review_required": proposal.review_required,
            "section_count": proposal.statistics.get("section_count", 0),
            "concept_count": proposal.statistics.get("concept_count", 0),
            "confidence": proposal.confidence,
            "blocking_finding_count": proposal.validations.filter(passed=False, severity="blocking").count(),
            "population_status": population.status if population else None,
        }
