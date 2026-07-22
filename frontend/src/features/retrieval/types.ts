export type RetrievalSynchronizationStatus = "planned" | "synchronizing" | "synchronized" | "failed";
export type RetrievalGenerationStatus = "building" | "validating" | "active" | "superseded" | "failed";
export type RetrievalSynchronizationReadiness = {
  academic_population_run_id: string; resource_id: string; ready: boolean; source_fingerprint: string;
  expected_section_count: number; expected_concept_count: number; existing_synchronization_run_id: string | null;
  active_generation_id: string | null; blockers: string[]; warnings: string[];
};
export type RetrievalSynchronizationRun = {
  id: string; academic_population_run_id: string; approved_projection_id: string;
  processing_job_id: string | null; resource_id: string; subject_id: string;
  trigger: string; reason: string;
  status: RetrievalSynchronizationStatus; source_fingerprint: string; manifest_fingerprint: string;
  retrieval_generation_id: string | null; planned_chunk_count: number; indexed_chunk_count: number;
  keyword_indexed_count: number; vector_indexed_count: number; failed_chunk_count: number;
  citation_coverage: number; failure_code: string; failure_message: string; retry_eligible: boolean;
  started_at: string | null; completed_at: string | null; failed_at: string | null; created_at: string;
};
