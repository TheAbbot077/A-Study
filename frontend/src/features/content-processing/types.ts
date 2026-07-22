export type ProcessingStatus =
  | "CREATED" | "QUEUED" | "INSPECTING" | "EXTRACTING" | "STRUCTURING"
  | "SEGMENTING" | "VALIDATING" | "POPULATING" | "INDEXING"
  | "READY_FOR_REVIEW" | "READY_FOR_TEACHING" | "FAILED" | "CANCELLED" | "DELETED";
export type ProcessingStage = "created" | "queued" | "inspecting" | "extracting" | "structuring" | "segmenting" | "validating" | "populating" | "indexing";
export type ProcessingFailure = { code: string | null; stage: string | null; message: string | null };
declare const processingJobIdBrand: unique symbol;
export type ProcessingJobId = string & { readonly [processingJobIdBrand]: "ProcessingJobId" };
export function toProcessingJobId(value: string): ProcessingJobId {
  return value as ProcessingJobId;
}
export type ProcessingJob = {
  id: ProcessingJobId; processing_job_id: ProcessingJobId; resource: string | null; stored_file: string | null;
  status: ProcessingStatus; stage: ProcessingStage; progress: number; stage_label: string;
  message: string | null; attempt: number; warning_count: number; can_retry: boolean;
  can_cancel: boolean; failure: ProcessingFailure | null; review_required: boolean;
  ready_for_teaching: boolean; completed_at: string | null; created_at: string; updated_at: string;
};
export type ProcessingAttempt = { id: string; attempt_number: number; status: "pending" | "running" | "succeeded" | "failed" | "cancelled"; created_at: string };
export type ProcessingDiagnostic = { id: string; stage: ProcessingStage; severity: "info" | "warning" | "error" | "fatal"; code: string; public_message: string; created_at: string };
