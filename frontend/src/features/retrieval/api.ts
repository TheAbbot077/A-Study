import { apiRequest } from "@/services/api";
import type { RetrievalSynchronizationReadiness, RetrievalSynchronizationRun } from "./types";

export const retrievalSynchronizationApi = {
  readiness: (populationRunId: string, signal?: AbortSignal) =>
    apiRequest<RetrievalSynchronizationReadiness>(`academic-review/population-runs/${populationRunId}/retrieval-readiness/`, { signal }),
  synchronize: (populationRunId: string, expectedSourceFingerprint: string, idempotencyKey: string, reason = "", signal?: AbortSignal) =>
    apiRequest<RetrievalSynchronizationRun>(`academic-review/population-runs/${populationRunId}/synchronize-retrieval/`, {
      method: "POST", signal,
      body: JSON.stringify({ expected_source_fingerprint: expectedSourceFingerprint, idempotency_key: idempotencyKey, reason }),
    }),
  get: (runId: string, signal?: AbortSignal) =>
    apiRequest<RetrievalSynchronizationRun>(`retrieval/synchronization-runs/${runId}/`, { signal }),
};
