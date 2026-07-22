from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum


class TeachingReadinessDecision(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    STALE = "stale"


class CheckSeverity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"
    INFORMATION = "information"


@dataclass(frozen=True)
class TeachingReadinessCheck:
    code: str
    category: str
    passed: bool
    severity: str
    expected: object
    observed: object
    explanation: str
    related_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TeachingReadinessSnapshot:
    resource_id: str
    subject_id: str
    processing_job_id: str
    processing_attempt_id: str
    stored_file_id: str
    source_fingerprint: str
    processing_source_fingerprint: str
    source_exists: bool
    source_available: bool
    processing_status: str
    processing_attempt_status: str
    processing_outputs_complete: bool
    blocking_diagnostic_count: int
    review_session_id: str
    review_status: str
    unresolved_review_findings: int
    approval_decision_id: str
    approval_decision: str
    approval_actor_authorized: bool
    approved_projection_id: str
    projection_fingerprint: str
    projection_status: str
    academic_population_run_id: str
    population_status: str
    population_fingerprint: str
    expected_section_count: int
    actual_section_count: int
    expected_concept_count: int
    actual_concept_count: int
    official_academic_fingerprint: str
    academic_content_valid: bool
    retrieval_synchronization_run_id: str
    synchronization_status: str
    synchronization_source_fingerprint: str
    manifest_fingerprint: str
    retrieval_generation_id: str
    generation_status: str
    planned_chunk_count: int
    stored_chunk_count: int
    keyword_indexed_count: int
    vector_indexed_count: int
    failed_chunk_count: int
    duplicate_chunk_count: int
    orphaned_chunk_count: int
    citation_coverage: float
    provenance_valid: bool
    policy_version: str

    def lineage_fingerprint(self) -> str:
        material = asdict(self)
        return hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), default=str).encode()
        ).hexdigest()


class TeachingReadinessPolicy:
    version = "teaching-readiness-v1"
    required_citation_coverage = 1.0

    def evaluate(self, snapshot: TeachingReadinessSnapshot) -> tuple[TeachingReadinessCheck, ...]:
        definitions = (
            ("READINESS_SOURCE_MISSING", "source", snapshot.source_exists, True, snapshot.source_exists, "The durable source file must exist."),
            ("READINESS_SOURCE_UNAVAILABLE", "source", snapshot.source_available, True, snapshot.source_available, "The durable source file must remain available."),
            ("READINESS_SOURCE_FINGERPRINT_MISMATCH", "source", snapshot.source_fingerprint == snapshot.processing_source_fingerprint, snapshot.processing_source_fingerprint, snapshot.source_fingerprint, "The current processing attempt must match the durable source."),
            ("READINESS_PROCESSING_INCOMPLETE", "processing", snapshot.processing_status in {"ready_for_review", "ready_for_teaching"}, "governed processing complete", snapshot.processing_status, "Governed processing must complete before evaluation."),
            ("READINESS_ATTEMPT_INCOMPLETE", "processing", snapshot.processing_attempt_status == "succeeded", "succeeded", snapshot.processing_attempt_status, "The current processing attempt must succeed."),
            ("READINESS_OUTPUTS_MISSING", "processing", snapshot.processing_outputs_complete, True, snapshot.processing_outputs_complete, "Extraction, structure, and segmentation outputs are required."),
            ("READINESS_DIAGNOSTICS_BLOCKING", "processing", snapshot.blocking_diagnostic_count == 0, 0, snapshot.blocking_diagnostic_count, "No unresolved blocking processing diagnostics may remain."),
            ("READINESS_REVIEW_INCOMPLETE", "review", snapshot.review_status in {"approved", "approved_with_edits"}, "approved", snapshot.review_status, "Human review must be completed and approved."),
            ("READINESS_REVIEW_FINDINGS_BLOCKING", "review", snapshot.unresolved_review_findings == 0, 0, snapshot.unresolved_review_findings, "No unresolved blocking review findings may remain."),
            ("READINESS_APPROVAL_INVALID", "approval", snapshot.approval_decision in {"approved", "approved_with_edits"}, "approved", snapshot.approval_decision, "An authorized approval decision is required."),
            ("READINESS_APPROVER_UNAUTHORIZED", "approval", snapshot.approval_actor_authorized, True, snapshot.approval_actor_authorized, "Approval must retain authorized actor evidence."),
            ("READINESS_PROJECTION_INVALID", "approval", snapshot.projection_status == "populated", "populated", snapshot.projection_status, "The immutable projection must be populated and current."),
            ("READINESS_POPULATION_INCOMPLETE", "academic", snapshot.population_status == "populated", "populated", snapshot.population_status, "Controlled Academic population must complete."),
            ("READINESS_POPULATION_FINGERPRINT_MISMATCH", "academic", snapshot.population_fingerprint == snapshot.projection_fingerprint, snapshot.projection_fingerprint, snapshot.population_fingerprint, "Population must match the approved projection."),
            ("READINESS_SECTION_MAPPING_MISMATCH", "academic", snapshot.actual_section_count == snapshot.expected_section_count, snapshot.expected_section_count, snapshot.actual_section_count, "Section mappings must reconcile."),
            ("READINESS_CONCEPT_MAPPING_MISMATCH", "academic", snapshot.actual_concept_count == snapshot.expected_concept_count, snapshot.expected_concept_count, snapshot.actual_concept_count, "Concept mappings must reconcile."),
            ("READINESS_ACADEMIC_CONTENT_INVALID", "academic", snapshot.academic_content_valid, True, snapshot.academic_content_valid, "Official Academic content must be active, owned, and substantive."),
            ("READINESS_SYNCHRONIZATION_INCOMPLETE", "retrieval", snapshot.synchronization_status == "synchronized", "synchronized", snapshot.synchronization_status, "Approved retrieval synchronization must complete."),
            ("READINESS_MANIFEST_INVALID", "retrieval", bool(snapshot.manifest_fingerprint), "nonblank", snapshot.manifest_fingerprint, "The synchronized retrieval manifest must be identifiable."),
            ("READINESS_ACADEMIC_FINGERPRINT_MISMATCH", "retrieval", snapshot.synchronization_source_fingerprint == snapshot.official_academic_fingerprint, snapshot.official_academic_fingerprint, snapshot.synchronization_source_fingerprint, "Retrieval must match current Academic truth."),
            ("READINESS_GENERATION_INACTIVE", "retrieval", snapshot.generation_status == "active", "active", snapshot.generation_status, "The synchronized generation must be active."),
            ("READINESS_CHUNK_COUNT_MISMATCH", "retrieval", snapshot.stored_chunk_count == snapshot.planned_chunk_count, snapshot.planned_chunk_count, snapshot.stored_chunk_count, "Planned and stored chunks must reconcile."),
            ("READINESS_KEYWORD_INDEX_INCOMPLETE", "retrieval", snapshot.keyword_indexed_count == snapshot.planned_chunk_count, snapshot.planned_chunk_count, snapshot.keyword_indexed_count, "Keyword indexing must be complete."),
            ("READINESS_VECTOR_INDEX_INCOMPLETE", "retrieval", snapshot.vector_indexed_count == snapshot.planned_chunk_count, snapshot.planned_chunk_count, snapshot.vector_indexed_count, "Vector indexing must be complete."),
            ("READINESS_FAILED_CHUNKS", "retrieval", snapshot.failed_chunk_count == 0, 0, snapshot.failed_chunk_count, "No retrieval chunk may have failed."),
            ("READINESS_DUPLICATE_CHUNKS", "provenance", snapshot.duplicate_chunk_count == 0, 0, snapshot.duplicate_chunk_count, "Active logical chunk keys must be unique."),
            ("READINESS_ORPHANED_CHUNKS", "provenance", snapshot.orphaned_chunk_count == 0, 0, snapshot.orphaned_chunk_count, "No active retrieval chunk may be orphaned."),
            ("READINESS_CITATION_COVERAGE_FAILED", "provenance", snapshot.citation_coverage >= self.required_citation_coverage, self.required_citation_coverage, snapshot.citation_coverage, "Every active teachable chunk requires accepted source provenance."),
            ("READINESS_PROVENANCE_INVALID", "provenance", snapshot.provenance_valid, True, snapshot.provenance_valid, "Active chunks must retain valid resource, section, concept, and source lineage."),
            ("READINESS_POLICY_VERSION_STALE", "policy", snapshot.policy_version == self.version, self.version, snapshot.policy_version, "The current readiness policy must be applied."),
        )
        return tuple(
            TeachingReadinessCheck(code, category, passed, CheckSeverity.BLOCKER, expected, observed, explanation)
            for code, category, passed, expected, observed, explanation in definitions
        )
