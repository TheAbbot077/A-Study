import { apiRequest } from "@/services/api";

export type ValidationFinding = {
  id: string;
  severity: "low" | "medium" | "high" | "critical";
  finding_type: string;
  message: string;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ContentImportJob = {
  id: string;
  learning_resource: string;
  stored_file?: string | null;
  format_type: "pdf" | "docx";
  status: "created" | "pending" | "processing" | "completed" | "failed" | "cancelled";
  status_detail?: "created" | "pending" | "processing" | "completed" | "completed_with_warnings" | "failed" | "cancelled";
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
  processing_status?: string | null;
  processing_stage?: string | null;
  processing_progress?: number | null;
  processing_stage_label?: string | null;
  processing_attempt?: number | null;
  processing_warning_count?: number;
  can_retry_processing?: boolean;
  can_cancel_processing?: boolean;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  validation_findings?: ValidationFinding[];
};

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
