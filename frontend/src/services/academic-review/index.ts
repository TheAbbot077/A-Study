import { apiRequest } from "@/services/api";

export type ReviewSummary = {
  section_accepted: number;
  section_rejected: number;
  section_pending: number;
  concept_accepted: number;
  concept_rejected: number;
  concept_pending: number;
  blocking_findings: number;
  resolved_findings: number;
  outstanding_findings: number;
  overrides: number;
  ready: boolean;
};

export type ReviewSessionStatus =
  | "not_started"
  | "in_progress"
  | "ready_for_approval"
  | "approved"
  | "approved_with_edits"
  | "rejected"
  | "reprocess_requested"
  | "superseded"
  | "abandoned";

export type ReviewSession = {
  id: string;
  proposal: string;
  proposal_version: string;
  version: number;
  status: ReviewSessionStatus;
  confidence: number;
  reviewer_id: string | null;
  approved_projection_id: string | null;
  resource: { id: string; title: string; source_label: string };
  summary: ReviewSummary;
  submitted_at: string | null;
  closed_at: string | null;
  created_at: string;
  updated_at: string;
};

export type ApprovalReadinessSnapshot = {
  id: string;
  proposal_version: string;
  review_session_version: number;
  ready: boolean;
  pending_sections: number;
  pending_concepts: number;
  accepted_sections: number;
  accepted_concepts: number;
  rejected_sections: number;
  rejected_concepts: number;
  blocking_findings: number;
  resolved_findings: number;
  orphan_concepts: number;
  invalid_hierarchy: number;
  duplicate_titles: number;
  override_count: number;
  policy_version: string;
  reasons: string[];
  checksum: string;
  evaluated_at: string;
};

export type ApprovalCommandResult = {
  projection_id: string;
  status: "created" | "ready_for_population";
  approval_version: string;
};

export type RejectionCommandResult = {
  decision_id: string;
  decision: "rejected";
};

export type ApprovedProjection = {
  id: string;
  proposal_id: string;
  session_id: string;
  approval_decision_id: string;
  approval_version: string;
  projection_version: string;
  resource_id: string;
  subject_id: string;
  institution_id: string;
  status: "created" | "ready_for_population" | "populating" | "populated" | "superseded";
  checksum: string;
  hierarchy_checksum: string;
  concepts_checksum: string;
  provenance_checksum: string;
  created_at: string;
  sections: Array<{
    id: number;
    source_proposed_section: string;
    final_title: string;
    canonical_title: string;
    parent_id: number | null;
    ordinal: number;
    depth: number;
    page_range: { start?: number; end?: number };
    evidence_references: unknown[];
  }>;
  concepts: Array<{
    id: number;
    source_proposed_concept: string;
    approved_section_id: number;
    final_title: string;
    canonical_title: string;
    ordinal: number;
    page_range: { start?: number; end?: number };
    supporting_evidence: unknown[];
  }>;
};

export type PopulationReadiness = {
  approved_projection_id: string;
  status: string;
  ready: boolean;
  expected_section_count: number;
  expected_concept_count: number;
  existing_population_run_id: string | null;
  blockers: Array<{ code: string; message: string }>;
};

export type PopulationResult = {
  population_run_id: string;
  approved_projection_id: string;
  status: "populated";
  resource_id: string;
  created_sections: number;
  matched_sections: number;
  created_concepts: number;
  matched_concepts: number;
  failed_items: number;
  populated_at: string;
};

export type ReviewDecision = "pending" | "accepted" | "rejected" | "edited" | "moved";
export type ReviewItem = {
  id: number;
  item_type: "section" | "concept";
  item_id: string;
  title: string;
  confidence: number;
  decision: ReviewDecision;
  reason: string;
  decided_at: string | null;
  edit: {
    title: string;
    ordering: number | null;
    parent_section_id: string | null;
    target_section_id: string | null;
  } | null;
};

export type ReviewEvidence = {
  id: number;
  page_start: number | null;
  page_end: number | null;
  evidence_strength: string;
  confidence: number;
  hierarchy: string;
  semantic_segment_id: string | null;
  block_id: string | null;
  supporting_text: string;
};

export type ReviewFinding = {
  id: number;
  code: string;
  severity: "info" | "warning" | "blocking";
  passed: boolean;
  message: string;
  resolved: boolean;
};

export type ReviewEditPayload = {
  title?: string;
  ordering?: number;
  parent_section_id?: string | null;
  target_section_id?: string | null;
  reason?: string;
};

export type FindingResolutionPayload = {
  validation_id: number;
  resolution_type: "rejection" | "edit" | "move";
  item_decision_id?: number;
  note?: string;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export async function startReview(proposalId: string, signal?: AbortSignal) {
  return (await apiRequest<ReviewSession>(
    `academic-review/sessions/proposals/${proposalId}/start/`,
    { method: "POST", body: "{}", signal },
  )) as ReviewSession;
}

export async function getReview(sessionId: string, signal?: AbortSignal) {
  return (await apiRequest<ReviewSession>(`academic-review/sessions/${sessionId}/`, { signal })) as ReviewSession;
}

export async function listOutline(sessionId: string, signal?: AbortSignal) {
  return (await apiRequest<Paginated<ReviewItem>>(
    `academic-review/sessions/${sessionId}/outline/?limit=500&offset=0`,
    { signal },
  )) as Paginated<ReviewItem>;
}

export async function getEvidence(sessionId: string, decisionId: number, signal?: AbortSignal) {
  return (await apiRequest<ReviewEvidence[]>(
    `academic-review/sessions/${sessionId}/items/${decisionId}/evidence/`,
    { signal },
  )) ?? [];
}

export async function listFindings(sessionId: string, signal?: AbortSignal) {
  return (await apiRequest<ReviewFinding[]>(`academic-review/sessions/${sessionId}/findings/`, { signal })) ?? [];
}

export function decideItem(
  sessionId: string,
  decisionId: number,
  decision: "accepted" | "rejected",
  reason: string,
  signal?: AbortSignal,
) {
  return apiRequest<ReviewItem>(
    `academic-review/sessions/${sessionId}/items/${decisionId}/decide/`,
    { method: "POST", body: JSON.stringify({ decision, reason }), signal },
  );
}

export function editItem(
  sessionId: string,
  decisionId: number,
  payload: ReviewEditPayload,
  signal?: AbortSignal,
) {
  return apiRequest<ReviewItem>(
    `academic-review/sessions/${sessionId}/items/${decisionId}/edit/`,
    { method: "POST", body: JSON.stringify(payload), signal },
  );
}

export function resolveFinding(
  sessionId: string,
  payload: FindingResolutionPayload,
  signal?: AbortSignal,
) {
  return apiRequest<{ id: number }>(
    `academic-review/sessions/${sessionId}/resolve-finding/`,
    { method: "POST", body: JSON.stringify(payload), signal },
  );
}

export function submitReview(sessionId: string, signal?: AbortSignal) {
  return apiRequest<ReviewSession>(
    `academic-review/sessions/${sessionId}/submit/`,
    { method: "POST", body: "{}", signal },
  );
}

export function evaluateApprovalReadiness(
  sessionId: string,
  expectedSessionVersion: number,
  signal?: AbortSignal,
) {
  return apiRequest<ApprovalReadinessSnapshot>(
    `academic-review/sessions/${sessionId}/evaluate-readiness/`,
    { method: "POST", body: JSON.stringify({ expected_session_version: expectedSessionVersion }), signal },
  );
}

export function approveReview(
  sessionId: string,
  readinessSnapshotId: string,
  expectedSessionVersion: number,
  idempotencyKey: string,
  signal?: AbortSignal,
) {
  return apiRequest<ApprovalCommandResult>(
    `academic-review/sessions/${sessionId}/approve/`,
    {
      method: "POST",
      body: JSON.stringify({
        readiness_snapshot_id: readinessSnapshotId,
        expected_session_version: expectedSessionVersion,
        idempotency_key: idempotencyKey,
      }),
      signal,
    },
  );
}

export function rejectReview(
  sessionId: string,
  reason: string,
  expectedSessionVersion: number,
  idempotencyKey: string,
  signal?: AbortSignal,
) {
  return apiRequest<RejectionCommandResult>(
    `academic-review/sessions/${sessionId}/reject/`,
    {
      method: "POST",
      body: JSON.stringify({
        reason,
        expected_session_version: expectedSessionVersion,
        idempotency_key: idempotencyKey,
      }),
      signal,
    },
  );
}

export function getApprovedProjection(projectionId: string, signal?: AbortSignal) {
  return apiRequest<ApprovedProjection>(`academic-review/projections/${projectionId}/`, { signal });
}

export function getPopulationReadiness(projectionId: string, signal?: AbortSignal) {
  return apiRequest<PopulationReadiness>(
    `academic-review/projections/${projectionId}/population-readiness/`,
    { signal },
  );
}

export function populateApprovedProjection(
  projectionId: string,
  expectedFingerprint: string,
  idempotencyKey: string,
  signal?: AbortSignal,
) {
  return apiRequest<PopulationResult>(
    `academic-review/projections/${projectionId}/populate/`,
    {
      method: "POST",
      body: JSON.stringify({
        expected_fingerprint: expectedFingerprint,
        idempotency_key: idempotencyKey,
      }),
      signal,
    },
  );
}
