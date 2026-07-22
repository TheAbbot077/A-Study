import { apiRequest } from "@/services/api";
import type { TeachingReadinessEvaluation, TeachingReadinessStatusResponse } from "./types";

export const teachingReadinessApi = {
  status: (resourceId: string, signal?: AbortSignal) =>
    apiRequest<TeachingReadinessStatusResponse>(`academic/learning-resources/${resourceId}/teaching-readiness/`, { signal }),
  evaluate: (resourceId: string, idempotencyKey: string, expectedLineageFingerprint = "", reason = "", signal?: AbortSignal) =>
    apiRequest<TeachingReadinessEvaluation>(`academic/learning-resources/${resourceId}/teaching-readiness/evaluate/`, {
      method: "POST", signal,
      body: JSON.stringify({ idempotency_key: idempotencyKey, expected_lineage_fingerprint: expectedLineageFingerprint, reason }),
    }),
  get: (evaluationId: string, signal?: AbortSignal) =>
    apiRequest<TeachingReadinessEvaluation>(`content-processing/teaching-readiness/evaluations/${evaluationId}/`, { signal }),
};
