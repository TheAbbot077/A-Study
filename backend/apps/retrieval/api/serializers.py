from rest_framework import serializers
from apps.retrieval.models import RetrievalChunkCollection, RetrievalIndexJob, RetrievalSynchronizationRun


class RetrievalReadinessSerializer(serializers.ModelSerializer):
    resource_id = serializers.UUIDField(read_only=True)
    population_job_id = serializers.UUIDField(read_only=True)
    index_job_id = serializers.SerializerMethodField()
    indexed_count = serializers.SerializerMethodField()

    class Meta:
        model = RetrievalChunkCollection
        fields = ("id", "resource_id", "population_job_id", "population_version", "retrieval_version", "embedding_version", "readiness", "chunk_count", "indexed_count", "index_job_id", "completed_at")

    def _job(self, obj):
        return obj.index_jobs.order_by("-created_at").first()

    def get_index_job_id(self, obj):
        job = self._job(obj); return str(job.id) if job else None

    def get_indexed_count(self, obj):
        job = self._job(obj); return job.indexed_count if job else 0


class RetrievalIndexJobSummarySerializer(serializers.ModelSerializer):
    population_job_id = serializers.UUIDField(read_only=True)
    collection_id = serializers.UUIDField(read_only=True, allow_null=True)
    class Meta:
        model = RetrievalIndexJob
        fields = ("id", "population_job_id", "collection_id", "retrieval_version", "embedding_version", "status", "chunk_count", "indexed_count", "failure_code", "started_at", "completed_at")


class RetrievalSynchronizationRunSerializer(serializers.ModelSerializer):
    academic_population_run_id = serializers.UUIDField(read_only=True)
    resource_id = serializers.UUIDField(read_only=True)
    subject_id = serializers.UUIDField(read_only=True)
    retrieval_generation_id = serializers.UUIDField(read_only=True, allow_null=True)
    retry_eligible = serializers.SerializerMethodField()

    class Meta:
        model = RetrievalSynchronizationRun
        fields = (
            "id", "academic_population_run_id", "approved_projection_id", "processing_job_id",
            "resource_id", "subject_id", "trigger", "reason", "status", "source_fingerprint",
            "manifest_fingerprint", "retrieval_generation_id", "planned_chunk_count",
            "indexed_chunk_count", "keyword_indexed_count", "vector_indexed_count",
            "failed_chunk_count", "citation_coverage", "failure_code", "failure_message",
            "retry_eligible", "started_at", "completed_at", "failed_at", "created_at",
        )

    def get_retry_eligible(self, obj):
        return obj.status == RetrievalSynchronizationRun.Status.FAILED
