import type { ProcessingJob, ProcessingStatus } from "./types";

export const PROCESSING_POLL_INTERVAL_MS = 5_000;

const ACTIVE_PROCESSING_STATUSES = new Set<ProcessingStatus>([
  "CREATED",
  "QUEUED",
  "INSPECTING",
  "EXTRACTING",
  "STRUCTURING",
  "SEGMENTING",
  "VALIDATING",
  "POPULATING",
  "INDEXING",
]);

export function isCanonicalProcessingActive(job: ProcessingJob | null): boolean {
  return job !== null && ACTIVE_PROCESSING_STATUSES.has(job.status);
}

export function isCanonicalProcessingFailed(job: ProcessingJob | null): boolean {
  return job?.status === "FAILED";
}

export function isCanonicalProcessingTerminal(job: ProcessingJob): boolean {
  return !ACTIVE_PROCESSING_STATUSES.has(job.status);
}

export function canonicalWorkflowStatus(job: ProcessingJob | null): string | null {
  if (!job) return null;
  return job.status.toLowerCase();
}

export function canonicalStatusLabel(job: ProcessingJob): string {
  return job.stage_label || job.status.replaceAll("_", " ").toLowerCase();
}

export type LegacyProcessingProjection = {
  processing_status?: string | null;
  processing_stage?: string | null;
  processing_progress?: number | null;
  processing_stage_label?: string | null;
  processing_attempt?: number | null;
};

export function selectAuthoritativeProcessing(
  canonicalJob: ProcessingJob | null,
  legacyJob: LegacyProcessingProjection | null,
) {
  if (canonicalJob) {
    return {
      source: "canonical" as const,
      status: canonicalJob.status,
      stage: canonicalJob.stage,
      progress: canonicalJob.progress,
      stageLabel: canonicalStatusLabel(canonicalJob),
      attempt: canonicalJob.attempt,
    };
  }
  return {
    source: "legacy" as const,
    status: legacyJob?.processing_status ?? null,
    stage: legacyJob?.processing_stage ?? null,
    progress: legacyJob?.processing_progress ?? null,
    stageLabel: legacyJob?.processing_stage_label ?? null,
    attempt: legacyJob?.processing_attempt ?? null,
  };
}
