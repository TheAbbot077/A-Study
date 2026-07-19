import { apiRequest } from "@/services/api";

export type ValidationFinding = {
  id: string;
  severity: "low" | "medium" | "high" | "critical";
  finding_type: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ProcessingStatus =
  | "created"
  | "queued"
  | "inspecting"
  | "extracting"
  | "structuring"
  | "segmenting"
  | "validating"
  | "populating"
  | "indexing"
  | "ready_for_review"
  | "ready_for_teaching"
  | "failed"
  | "cancelled"
  | "deleted";

export type ImportProposalSummary = {
  id?: string;
  status: string;
  decision: string;
  population_state: string;
  proposed_section_count: number;
  proposed_concept_count: number;
  confidence: number;
  blocking_finding_count: number;
};

export type ContentImportJob = {
  id: string;
  learning_resource: string;
  stored_file?: string | null;
  format_type: "pdf" | "docx";
  status: "created" | "pending" | "processing" | "completed" | "failed" | "cancelled";
  status_detail?: "created" | "pending" | "processing" | "review_required" | "completed" | "completed_with_warnings" | "failed" | "cancelled";
  requested_by?: string | null;
  error_message: string;
  ocr_requested: boolean;
  ocr_used: boolean;
  extraction_confidence?: number | null;
  section_confidence?: number | null;
  concept_confidence?: number | null;
  structural_confidence?: number | null;
  metadata: Record<string, unknown>;
  retry_count?: number;
  failure_details?: Record<string, unknown> | null;
  resource_ready_for_learning?: boolean;
  processing_job_id?: string | null;
  processing_status?: ProcessingStatus | string | null;
  processing_stage?: string | null;
  processing_progress?: number | null;
  processing_stage_label?: string | null;
  processing_message?: string | null;
  processing_attempt?: number | null;
  processing_warning_count?: number;
  can_retry_processing?: boolean;
  can_cancel_processing?: boolean;
  review_required?: boolean;
  ready_for_teaching?: boolean;
  processing_failure?: { code?: string | null; stage?: string | null; message?: string | null } | null;
  processing_completed_at?: string | null;
  proposal?: ImportProposalSummary | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  validation_findings?: ValidationFinding[];
};

const ACTIVE_PROCESSING_STATUSES = new Set<ProcessingStatus>([
  "created",
  "queued",
  "inspecting",
  "extracting",
  "structuring",
  "segmenting",
  "validating",
  "populating",
  "indexing",
]);

const PROCESSING_LABELS: Record<ProcessingStatus, string> = {
  created: "Preparing document processing",
  queued: "Waiting to begin processing",
  inspecting: "Inspecting the document",
  extracting: "Extracting document content",
  structuring: "Organizing chapters and sections",
  segmenting: "Building meaningful content units",
  validating: "Validating the academic proposal",
  populating: "Publishing approved academic content",
  indexing: "Preparing content for teaching",
  ready_for_review: "Ready for academic review",
  ready_for_teaching: "Ready for teaching",
  failed: "Processing failed",
  cancelled: "Processing cancelled",
  deleted: "Deleted",
};

export function authoritativeProcessingStatus(job: ContentImportJob | null): ProcessingStatus | null {
  const status = job?.processing_status?.toLowerCase() as ProcessingStatus | undefined;
  return status && status in PROCESSING_LABELS ? status : null;
}

export function isActivelyProcessing(job: ContentImportJob | null): boolean {
  const authoritative = authoritativeProcessingStatus(job);
  if (authoritative) {
    return ACTIVE_PROCESSING_STATUSES.has(authoritative);
  }
  return job?.status === "pending" || job?.status === "processing";
}

export function isReviewRequired(job: ContentImportJob | null): boolean {
  return authoritativeProcessingStatus(job) === "ready_for_review" || Boolean(job?.review_required);
}

export function isReadyForTeaching(job: ContentImportJob | null): boolean {
  return authoritativeProcessingStatus(job) === "ready_for_teaching" || Boolean(job?.ready_for_teaching);
}

export function isProcessingFailed(job: ContentImportJob | null): boolean {
  const authoritative = authoritativeProcessingStatus(job);
  return authoritative ? authoritative === "failed" : job?.status === "failed";
}

export function processingStatusLabel(job: ContentImportJob | null): string {
  const authoritative = authoritativeProcessingStatus(job);
  if (authoritative) {
    return PROCESSING_LABELS[authoritative];
  }
  return job?.processing_stage_label || job?.status_detail || job?.status || "Awaiting import";
}

export function isPollingTerminal(job: ContentImportJob | null): boolean {
  const authoritative = authoritativeProcessingStatus(job);
  return authoritative
    ? new Set<ProcessingStatus>(["ready_for_review", "ready_for_teaching", "failed", "cancelled", "deleted"]).has(authoritative)
    : !isActivelyProcessing(job);
}

export async function createImportJob(learningResourceId: string): Promise<ContentImportJob> {
  return (await apiRequest<ContentImportJob>("content-intelligence/import-jobs/", {
    method: "POST",
    body: JSON.stringify({ learning_resource: learningResourceId }),
  })) as ContentImportJob;
}

export async function listImportJobsForResource(learningResourceId: string): Promise<ContentImportJob[]> {
  return (
    (await apiRequest<ContentImportJob[]>(
      `content-intelligence/import-jobs/?learning_resource=${encodeURIComponent(learningResourceId)}`,
    )) ?? []
  );
}

export async function getImportJob(importJobId: string): Promise<ContentImportJob> {
  return (await apiRequest<ContentImportJob>(`content-intelligence/import-jobs/${importJobId}/`)) as ContentImportJob;
}

export async function retryImportJob(importJobId: string): Promise<ContentImportJob> {
  return (await apiRequest<ContentImportJob>(`content-intelligence/import-jobs/${importJobId}/retry/`, {
    method: "POST",
    body: JSON.stringify({}),
  })) as ContentImportJob;
}

export async function deleteImportJob(importJobId: string): Promise<void> {
  await apiRequest(`content-intelligence/import-jobs/${importJobId}/`, {
    method: "DELETE",
  });
}
