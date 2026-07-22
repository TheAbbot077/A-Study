import { apiRequest } from "@/services/api";
import type { AcademicPopulationRun } from "./types";

export const academicPopulationApi = {
  get: (runId: string, signal?: AbortSignal) =>
    apiRequest<AcademicPopulationRun>(`academic-review/population-runs/${runId}/`, { signal }),
};
