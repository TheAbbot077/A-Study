import { apiRequest } from "@/services/api";

export type ReviewSummary = {
  section_accepted: number; section_rejected: number; section_pending: number;
  concept_accepted: number; concept_rejected: number; concept_pending: number;
  blocking_findings: number; resolved_findings: number; outstanding_findings: number;
  overrides: number; ready: boolean;
};
export type ReviewSession = { id: string; proposal: string; proposal_version: string; version: number; status: string; confidence: number; approved_projection_id: string | null; resource: { id: string; title: string; source_label: string }; summary: ReviewSummary };
export type ApprovalReadinessSnapshot = { id: string; review_session_version: number; ready: boolean; reasons: string[]; checksum: string };
export type ReviewItem = { id: number; item_type: "section" | "concept"; item_id: string; title: string; confidence: number; decision: string; reason: string; edit: { title: string; ordering: number | null; parent_section_id: string | null; target_section_id: string | null } | null };
export type ReviewEvidence = { id: number; page_start: number | null; page_end: number | null; evidence_strength: string; confidence: number; hierarchy: string; semantic_segment_id: string | null; block_id: string | null; supporting_text: string };
export type ReviewFinding = { id: number; code: string; severity: string; passed: boolean; message: string; resolved: boolean };
export type ApprovedProjection = { id: string; status: string; checksum: string; resource_id: string; sections: unknown[]; concepts: unknown[] };
export type PopulationReadiness = { approved_projection_id: string; status: string; ready: boolean; expected_section_count: number; expected_concept_count: number; existing_population_run_id: string | null; blockers: { code: string; message: string }[] };
export type PopulationResult = { population_run_id: string; approved_projection_id: string; status: string; resource_id: string; created_sections: number; matched_sections: number; created_concepts: number; matched_concepts: number; failed_items: number; populated_at: string };
type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export async function startReview(proposalId: string) { return (await apiRequest<ReviewSession>(`academic-review/sessions/proposals/${proposalId}/start/`, { method: "POST", body: "{}" })) as ReviewSession; }
export async function getReview(sessionId: string) { return (await apiRequest<ReviewSession>(`academic-review/sessions/${sessionId}/`)) as ReviewSession; }
export async function listOutline(sessionId: string, query = "", offset = 0) { const params = new URLSearchParams({ limit: "500", offset: String(offset) }); if (query) params.set("search", query); return (await apiRequest<Paginated<ReviewItem>>(`academic-review/sessions/${sessionId}/outline/?${params}`)) as Paginated<ReviewItem>; }
export async function getEvidence(sessionId: string, decisionId: number) { return (await apiRequest<ReviewEvidence[]>(`academic-review/sessions/${sessionId}/items/${decisionId}/evidence/`)) ?? []; }
export async function listFindings(sessionId: string) { return (await apiRequest<ReviewFinding[]>(`academic-review/sessions/${sessionId}/findings/`)) ?? []; }
export async function decideItem(sessionId: string, decisionId: number, decision: "accepted" | "rejected", reason = "") { return apiRequest<ReviewItem>(`academic-review/sessions/${sessionId}/items/${decisionId}/decide/`, { method: "POST", body: JSON.stringify({ decision, reason }) }); }
export async function editItem(sessionId: string, decisionId: number, payload: { title?: string; ordering?: number; parent_section_id?: string | null; target_section_id?: string | null; reason?: string }) { return apiRequest<ReviewItem>(`academic-review/sessions/${sessionId}/items/${decisionId}/edit/`, { method: "POST", body: JSON.stringify(payload) }); }
export async function bulkReview(sessionId: string, policyCode: string, previewOnly: boolean) { return apiRequest<{ affected_count: number }>(`academic-review/sessions/${sessionId}/bulk/`, { method: "POST", body: JSON.stringify({ policy_code: policyCode, preview_only: previewOnly }) }); }
export async function submitReview(sessionId: string) { return apiRequest<ReviewSession>(`academic-review/sessions/${sessionId}/submit/`, { method: "POST", body: "{}" }); }
export async function evaluateApprovalReadiness(sessionId: string, expectedSessionVersion: number) { return apiRequest<ApprovalReadinessSnapshot>(`academic-review/sessions/${sessionId}/evaluate-readiness/`, { method: "POST", body: JSON.stringify({ expected_session_version: expectedSessionVersion }) }); }
export async function approveReview(sessionId: string, readinessSnapshotId: string, expectedSessionVersion: number, idempotencyKey: string) { return apiRequest<{ projection_id: string; status: string; approval_version: string }>(`academic-review/sessions/${sessionId}/approve/`, { method: "POST", body: JSON.stringify({ readiness_snapshot_id: readinessSnapshotId, expected_session_version: expectedSessionVersion, idempotency_key: idempotencyKey }) }); }
export async function getApprovedProjection(projectionId: string) { return apiRequest<ApprovedProjection>(`academic-review/projections/${projectionId}/`); }
export async function getPopulationReadiness(projectionId: string) { return apiRequest<PopulationReadiness>(`academic-review/projections/${projectionId}/population-readiness/`); }
export async function populateApprovedProjection(projectionId: string, expectedFingerprint: string, idempotencyKey: string) { return apiRequest<PopulationResult>(`academic-review/projections/${projectionId}/populate/`, { method: "POST", body: JSON.stringify({ expected_fingerprint: expectedFingerprint, idempotency_key: idempotencyKey }) }); }
export async function rejectReview(sessionId: string, reason: string, expectedSessionVersion: number, idempotencyKey: string) { return apiRequest<{ decision_id: string; decision: string }>(`academic-review/sessions/${sessionId}/reject/`, { method: "POST", body: JSON.stringify({ reason, expected_session_version: expectedSessionVersion, idempotency_key: idempotencyKey }) }); }
export async function requestReprocessing(sessionId: string, reason: string) { return apiRequest<ReviewSession>(`academic-review/sessions/${sessionId}/request-reprocessing/`, { method: "POST", body: JSON.stringify({ reason }) }); }
export async function resolveFinding(sessionId: string, payload: { validation_id: number; resolution_type: "rejection" | "edit" | "move" | "override"; item_decision_id?: number; note?: string; override_reason?: string }) { return apiRequest<{ id: number }>(`academic-review/sessions/${sessionId}/resolve-finding/`, { method: "POST", body: JSON.stringify(payload) }); }
