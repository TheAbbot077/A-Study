import { apiRequest } from "@/services/api";

export type SelfStudyWorkspaceStatus =
  | "DRAFT"
  | "INTENT_REQUIRED"
  | "INTENT_IN_PROGRESS"
  | "MATERIALS_REQUIRED"
  | "MATERIALS_PROCESSING"
  | "MATERIALS_BLOCKED"
  | "MATERIALS_READY"
  | "DIAGNOSTIC_READY"
  | "DIAGNOSTIC_IN_PROGRESS"
  | "DIAGNOSTIC_COMPLETE"
  | "PLANNING_REQUIRED"
  | "PLANNING_IN_PROGRESS"
  | "PLAN_READY"
  | "PREPARATION_IN_PROGRESS"
  | "READY_TO_LEARN"
  | "LEARNING_ACTIVE"
  | "BLOCKED"
  | "STALE"
  | "ARCHIVED";

export type SelfStudyWorkspace = {
  id: string;
  tenant_id: string;
  learner_id: string;
  display_name: string;
  description: string;
  status: SelfStudyWorkspaceStatus;
  intent_id: string | null;
  curriculum_resolution_id: string | null;
  published_graph_id: string | null;
  active_diagnostic_id: string | null;
  latest_coverage_evaluation_id: string | null;
  active_bridge_plan_id: string | null;
  active_teaching_preparation_id: string | null;
  active_teaching_session_id: string | null;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  version: number;
};

export type SelfStudyNextAction = {
  code:
    | "CREATE_WORKSPACE"
    | "COMPLETE_INTENT"
    | "UPLOAD_MATERIALS"
    | "WAIT_FOR_PROCESSING"
    | "RESOLVE_MATERIAL_ISSUES"
    | "START_DIAGNOSTIC"
    | "RESUME_DIAGNOSTIC"
    | "WAIT_FOR_MAPPING"
    | "WAIT_FOR_BRIDGE_PLAN"
    | "REVIEW_STUDY_PLAN"
    | "WAIT_FOR_TEACHING_PREPARATION"
    | "START_LEARNING"
    | "RESUME_LEARNING"
    | "CONTACT_SUPPORT"
    | "NO_ACTION_AVAILABLE";
  title: string;
  explanation: string;
  primary_cta_label: string;
  target_route: string;
  blocker_codes: string[];
  safe_ids: Record<string, string>;
  safe_status_summary: Record<string, string>;
};

export type SelfStudyOnboardingSummary = {
  workspace_id: string;
  status: SelfStudyWorkspaceStatus;
  version: number;
  next_action: SelfStudyNextAction;
  material_counts: Record<string, number>;
  blocker_codes: string[];
};

export type WorkspaceMaterial = {
  id: string;
  workspace_id: string;
  resource_id: string;
  resource_title: string;
  resource_status: string;
  processing_job_id: string | null;
  processing_status: string | null;
  status: string;
  blocker_codes: string[];
  safe_status_summary: Record<string, string>;
  created_at: string;
  updated_at: string;
  retired_at: string | null;
  version: number;
};

export type PublicDiagnostic = {
  id?: string;
  status: string;
  current_sequence?: number;
  maximum_items?: number;
  expires_at?: string;
};

export type SelfStudyDiagnosticExperience = {
  workspace_id: string;
  diagnostic_session_id: string;
  status: "NOT_READY" | "READY_TO_START" | "IN_PROGRESS" | "AWAITING_SCORING" | "COMPLETE" | "STALE" | "INVALIDATED" | "BLOCKED";
  can_start: boolean;
  can_resume: boolean;
  can_submit: boolean;
  progress: {
    answered: number;
    minimum_items: number;
    maximum_items: number;
  };
  disclosure_complete: boolean;
  privacy_notice_version: string;
  next_action: string;
  blocker_codes: string[];
};

export type LearnerPlacementSummary = {
  workspace_id: string;
  diagnostic_result_id: string;
  summary_state: string;
  placement_band: string;
  ready_domains: string[];
  needs_review_domains: string[];
  not_yet_ready_domains: string[];
  confidence_label: string;
  generated_at: string;
  privacy_warnings: string[];
};

export type SelfStudyPlanExperience = {
  workspace_id: string;
  bridge_plan_id: string;
  plan_status: string;
  approval_status: string;
  active: boolean;
  target_scope: Record<string, unknown>;
  estimated_node_count: number;
  required_node_count: number;
  optional_node_count: number;
  blocked_node_count: number;
  ready_node_count: number;
  next_plan_node_id: string;
  can_start_learning: boolean;
  blocker_codes: string[];
  findings: Array<{
    code: string;
    severity: string;
    blocking: boolean;
    scope: string;
  }>;
};

export type SelfStudyPlanNodeSummary = {
  plan_node_id: string;
  curriculum_node_id: string;
  node_type: string;
  title: string;
  sequence_index: number;
  disposition: string;
  coverage_state: string;
  material_status: string;
  estimated_effort_label: string;
  dependency_summary: {
    dependency_count: number;
    required: boolean;
  };
  blocked: boolean;
  blocker_codes: string[];
  finding_codes: string[];
};

export type SelfStudyPlanFinding = {
  id: string;
  code: string;
  severity: string;
  blocking: boolean;
  scope: string;
  details: Record<string, unknown>;
};

export type CreateWorkspacePayload = {
  tenant_id?: string;
  display_name: string;
  description?: string;
  idempotency_key?: string;
};

export type AttachMaterialPayload = {
  resource_id: string;
  content_processing_job_id?: string;
  idempotency_key?: string;
};

const workspacesPath = "self-study/workspaces/";
const workspacePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/`;
const workspaceDiagnosticExperiencePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/diagnostic/experience/`;
const workspaceDiagnosticResumePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/diagnostic/resume/`;
const workspaceDiagnosticSummaryPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/diagnostic/summary/`;
const workspacePlanExperiencePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/plan/experience/`;
const workspacePlanNodesPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/plan/nodes/`;
const workspacePlanFindingsPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/plan/findings/`;
const workspacePlanStartLearningPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/plan/start-learning/`;

export async function listSelfStudyWorkspaces(signal?: AbortSignal): Promise<SelfStudyWorkspace[]> {
  return (await apiRequest<SelfStudyWorkspace[]>(workspacesPath, { signal })) ?? [];
}

export async function createSelfStudyWorkspace(payload: CreateWorkspacePayload): Promise<SelfStudyWorkspace> {
  return (await apiRequest<SelfStudyWorkspace>(workspacesPath, {
    method: "POST",
    body: JSON.stringify(payload),
  })) as SelfStudyWorkspace;
}

export async function getSelfStudyWorkspace(workspaceId: string, signal?: AbortSignal): Promise<SelfStudyWorkspace> {
  return (await apiRequest<SelfStudyWorkspace>(workspacePath(workspaceId), { signal })) as SelfStudyWorkspace;
}

export async function archiveSelfStudyWorkspace(workspaceId: string, expectedVersion: number): Promise<SelfStudyWorkspace> {
  return (await apiRequest<SelfStudyWorkspace>(`self-study/workspaces/${workspaceId}/archive/`, {
    method: "POST",
    body: JSON.stringify({ expected_version: expectedVersion }),
  })) as SelfStudyWorkspace;
}

export async function getWorkspaceOnboarding(workspaceId: string, signal?: AbortSignal): Promise<SelfStudyOnboardingSummary> {
  return (await apiRequest<SelfStudyOnboardingSummary>(`self-study/workspaces/${workspaceId}/onboarding/`, { signal })) as SelfStudyOnboardingSummary;
}

export async function getWorkspaceNextAction(workspaceId: string, signal?: AbortSignal): Promise<SelfStudyNextAction> {
  return (await apiRequest<SelfStudyNextAction>(`self-study/workspaces/${workspaceId}/next-action/`, { signal })) as SelfStudyNextAction;
}

export async function listWorkspaceMaterials(workspaceId: string, signal?: AbortSignal): Promise<WorkspaceMaterial[]> {
  return (await apiRequest<WorkspaceMaterial[]>(`self-study/workspaces/${workspaceId}/materials/`, { signal })) ?? [];
}

export async function attachWorkspaceMaterial(workspaceId: string, payload: AttachMaterialPayload): Promise<WorkspaceMaterial> {
  return (await apiRequest<WorkspaceMaterial>(`self-study/workspaces/${workspaceId}/materials/`, {
    method: "POST",
    body: JSON.stringify(payload),
  })) as WorkspaceMaterial;
}

export async function getWorkspaceDiagnosticStatus(workspaceId: string, signal?: AbortSignal): Promise<PublicDiagnostic> {
  return (await apiRequest<PublicDiagnostic>(`self-study/workspaces/${workspaceId}/diagnostic/status/`, { signal })) as PublicDiagnostic;
}

export async function startWorkspaceDiagnostic(workspaceId: string, purposeAcknowledged: boolean): Promise<PublicDiagnostic> {
  return (await apiRequest<PublicDiagnostic>(`self-study/workspaces/${workspaceId}/diagnostic/start/`, {
    method: "POST",
    body: JSON.stringify({ purpose_acknowledged: purposeAcknowledged }),
  })) as PublicDiagnostic;
}

export async function getWorkspaceDiagnosticExperience(workspaceId: string, signal?: AbortSignal): Promise<SelfStudyDiagnosticExperience> {
  return (await apiRequest<SelfStudyDiagnosticExperience>(workspaceDiagnosticExperiencePath(workspaceId), { signal })) as SelfStudyDiagnosticExperience;
}

export async function resumeWorkspaceDiagnostic(workspaceId: string): Promise<PublicDiagnostic> {
  return (await apiRequest<PublicDiagnostic>(workspaceDiagnosticResumePath(workspaceId), { method: "POST" })) as PublicDiagnostic;
}

export async function getWorkspacePlacementSummary(workspaceId: string, signal?: AbortSignal): Promise<LearnerPlacementSummary> {
  return (await apiRequest<LearnerPlacementSummary>(workspaceDiagnosticSummaryPath(workspaceId), { signal })) as LearnerPlacementSummary;
}

export async function getWorkspacePlanExperience(workspaceId: string, signal?: AbortSignal): Promise<SelfStudyPlanExperience> {
  return (await apiRequest<SelfStudyPlanExperience>(workspacePlanExperiencePath(workspaceId), { signal })) as SelfStudyPlanExperience;
}

export async function listWorkspacePlanNodes(workspaceId: string, signal?: AbortSignal): Promise<SelfStudyPlanNodeSummary[]> {
  return (await apiRequest<SelfStudyPlanNodeSummary[]>(workspacePlanNodesPath(workspaceId), { signal })) ?? [];
}

export async function listWorkspacePlanFindings(workspaceId: string, signal?: AbortSignal): Promise<SelfStudyPlanFinding[]> {
  return (await apiRequest<SelfStudyPlanFinding[]>(workspacePlanFindingsPath(workspaceId), { signal })) ?? [];
}

export async function startWorkspaceLearning(workspaceId: string): Promise<{ workspace_id: string; teaching_session_id: string; state: string; target_route: string }> {
  return (await apiRequest<{ workspace_id: string; teaching_session_id: string; state: string; target_route: string }>(workspacePlanStartLearningPath(workspaceId), {
    method: "POST",
  })) as { workspace_id: string; teaching_session_id: string; state: string; target_route: string };
}
