import { apiRequest } from "@/services/api";
import type { ProcessingAttempt, ProcessingDiagnostic, ProcessingJob, ProcessingJobId } from "./types";

export function processingJobPath(jobId: ProcessingJobId, action?: "attempts" | "diagnostics" | "retry" | "cancel") {
  return `content-processing/jobs/${jobId}/${action ? `${action}/` : ""}`;
}

export const contentProcessingApi = {
  listForResource: (resourceId: string, signal?: AbortSignal) =>
    apiRequest<ProcessingJob[]>(`content-processing/jobs/?resource=${encodeURIComponent(resourceId)}`, { signal }),
  get: (jobId: ProcessingJobId, signal?: AbortSignal) => apiRequest<ProcessingJob>(processingJobPath(jobId), { signal }),
  attempts: (jobId: ProcessingJobId, signal?: AbortSignal) => apiRequest<ProcessingAttempt[]>(processingJobPath(jobId, "attempts"), { signal }),
  diagnostics: (jobId: ProcessingJobId, signal?: AbortSignal) => apiRequest<ProcessingDiagnostic[]>(processingJobPath(jobId, "diagnostics"), { signal }),
  retry: (jobId: ProcessingJobId, signal?: AbortSignal) => apiRequest<ProcessingJob>(processingJobPath(jobId, "retry"), { method: "POST", body: "{}", signal }),
  cancel: (jobId: ProcessingJobId, signal?: AbortSignal) => apiRequest<ProcessingJob>(processingJobPath(jobId, "cancel"), { method: "POST", body: "{}", signal }),
};
