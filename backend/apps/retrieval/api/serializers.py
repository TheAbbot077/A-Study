from rest_framework import serializers
from apps.retrieval.models import RetrievalChunkCollection, RetrievalIndexJob


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
