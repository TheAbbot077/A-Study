from django.contrib import admin
from apps.retrieval.models import GroundingCitation, GroundingPackage, RetrievalChunk, RetrievalChunkCollection, RetrievalDiagnostic, RetrievalGeneration, RetrievalIndexJob, RetrievalStatistic, RetrievalSynchronizationRun


class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False


@admin.register(RetrievalChunkCollection)
class CollectionAdmin(ReadOnlyAdmin):
    list_display = ("id", "population_job", "resource", "readiness", "chunk_count", "retrieval_version", "embedding_version", "completed_at")
    list_filter = ("readiness", "retrieval_version", "embedding_version")


@admin.register(RetrievalChunk)
class ChunkAdmin(ReadOnlyAdmin):
    list_display = ("id", "collection", "ordering", "chunk_type", "section", "concept", "source_page_start", "source_page_end", "confidence")
    list_filter = ("chunk_type", "retrieval_version", "embedding_version")
    exclude = ("embedding",)


@admin.register(RetrievalIndexJob)
class IndexJobAdmin(ReadOnlyAdmin):
    list_display = ("id", "population_job", "status", "chunk_count", "indexed_count", "failure_code", "started_at", "completed_at")
    list_filter = ("status", "retrieval_version", "embedding_version", "failure_code")


@admin.register(RetrievalGeneration)
class RetrievalGenerationAdmin(ReadOnlyAdmin):
    list_display = ("id", "resource", "subject", "status", "chunk_count", "manifest_fingerprint", "promoted_at", "superseded_at")
    list_filter = ("status", "created_at", "promoted_at")
    search_fields = ("id", "resource__id", "manifest_fingerprint", "source_fingerprint")


@admin.register(RetrievalSynchronizationRun)
class RetrievalSynchronizationRunAdmin(ReadOnlyAdmin):
    list_display = ("id", "academic_population_run", "resource", "subject", "trigger", "status", "retrieval_generation", "planned_chunk_count", "indexed_chunk_count", "citation_coverage", "failure_code", "completed_at")
    list_filter = ("status", "trigger", "failure_code", "created_at", "completed_at")
    search_fields = ("id", "academic_population_run__id", "approved_projection_id", "resource__id", "manifest_fingerprint", "idempotency_key")


class CitationInline(admin.TabularInline):
    model = GroundingCitation
    extra = 0
    can_delete = False
    readonly_fields = tuple(field.name for field in GroundingCitation._meta.fields)


@admin.register(GroundingPackage)
class GroundingPackageAdmin(ReadOnlyAdmin):
    list_display = ("id", "query_text", "checksum", "created_at")
    inlines = (CitationInline,)


@admin.register(GroundingCitation)
class GroundingCitationAdmin(ReadOnlyAdmin):
    list_display = ("package", "rank", "chunk", "resource", "section", "concept", "source_page_start", "source_page_end", "score")


@admin.register(RetrievalStatistic)
class RetrievalStatisticAdmin(ReadOnlyAdmin):
    list_display = ("index_job", "collection", "chunk_count", "indexed_count", "embedding_batch_count", "ranking_policy_version", "created_at")


@admin.register(RetrievalDiagnostic)
class RetrievalDiagnosticAdmin(ReadOnlyAdmin):
    list_display = ("id", "index_job", "grounding_package", "severity", "code", "created_at")
    list_filter = ("severity", "code")
