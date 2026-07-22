export type TeachingReadinessDecision = "ready" | "blocked" | "stale";
export type TeachingReadinessStatus = "not_ready" | "ready_for_teaching" | "stale";
export type TeachingReadinessCheckCategory = "source" | "processing" | "review" | "approval" | "academic" | "retrieval" | "provenance" | "policy";
export type TeachingReadinessCheckSeverity = "blocker" | "warning" | "information";
export type TeachingReadinessCheck = {
  code: string; category: TeachingReadinessCheckCategory; passed: boolean;
  severity: TeachingReadinessCheckSeverity; expected: unknown; observed: unknown;
  explanation: string; related_ids: string[];
};
export type TeachingReadinessEvaluation = {
  id: string; resource_id: string; subject_id: string; processing_job_id: string;
  processing_attempt_id: string | null; approved_projection_id: string | null;
  approval_decision_id: string | null; academic_population_run_id: string | null;
  retrieval_synchronization_run_id: string | null; retrieval_generation_id: string | null;
  trigger: string; reason: string;
  decision: TeachingReadinessDecision; lineage_fingerprint: string; policy_version: string;
  checks_passed: number; checks_failed: number; blocker_count: number; warning_count: number;
  snapshot: Record<string, unknown>;
  checks: TeachingReadinessCheck[]; invalidation_reason: string; invalidated_at: string | null;
  supersedes_evaluation_id: string | null; evaluated_at: string;
};
export type TeachingReadinessStatusResponse = {
  resource_id: string; status: TeachingReadinessStatus; latest_evaluation_id: string | null;
  decision: TeachingReadinessDecision | null; lineage_fingerprint?: string; policy_version?: string;
  checks_passed?: number; checks_failed?: number; blocker_count?: number; warning_count?: number;
  blockers: TeachingReadinessCheck[]; warnings: TeachingReadinessCheck[];
  can_evaluate: boolean; can_reevaluate: boolean;
};
