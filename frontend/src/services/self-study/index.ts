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

export type LearningStudioCitation = {
  citation_id: string;
  resource_id: string;
  resource_title: string;
  page: string | number;
  segment: string;
  excerpt: string;
  evidence_unit_id: string;
  mapping_id: string;
  source_state: string;
};

export type LearningStudioTurn = {
  turn_id: string;
  role: "LEARNER" | "ABBOT" | "SYSTEM";
  action_type: string;
  status: string;
  content: string;
  created_at: string;
  citations: LearningStudioCitation[];
  rationale_codes: string[];
  requires_response: boolean;
  safe_transition: string;
};

export type LearningStudioNodeSummary = {
  plan_node_id: string;
  curriculum_node_id: string;
  node_type: string;
  title: string;
  learning_objective: string;
  sequence_index: number;
  total_sequence_count: number;
  dependency_summary: Record<string, unknown>;
  coverage_state: string;
  material_status: string;
  teaching_pack_id: string;
  citations_available: boolean;
  blocked: boolean;
  blocker_codes: string[];
};

export type LearningStudioExperience = {
  workspace_id: string;
  teaching_session_id: string;
  session_version: number;
  bridge_plan_id: string;
  current_plan_node_id: string;
  current_curriculum_node_id: string;
  session_status: string;
  node_status: string;
  can_start: boolean;
  can_resume: boolean;
  can_send_message: boolean;
  can_pause: boolean;
  can_request_recap: boolean;
  can_advance: boolean;
  can_start_concept_check: boolean;
  progress_summary: {
    completed_teaching_segments: number;
    total_teaching_segments: number;
    current_index: number;
    concept_check_ready: boolean;
    next_label?: string;
  };
  blocker_codes: string[];
  next_action: string;
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

export type SelfStudyIntent = {
  id: string;
  learner_id: string;
  tenant_id: string;
  subject_id: string;
  mode: "SELF_STUDY" | "INSTITUTION_GOVERNED";
  goal_statement: string;
  target_title: string;
  target_outcomes: string[];
  target_credential: string;
  preferred_curriculum_authority: string;
  jurisdiction: string;
  preferred_language: string;
  learner_age_band: string;
  accessibility_requirements: string[];
  desired_depth: string;
  pace_preference: string;
  time_budget_minutes_per_week: number | null;
  target_completion_date: string | null;
  policy_acknowledged_at: string | null;
  status: string;
  effective_policy_snapshot_id: string | null;
  created_at: string;
  updated_at: string;
  version: number;
};

export type WorkspaceIntentChoice = "exam" | "learn_new" | "master_subject";

export type CreateWorkspaceIntentPayload = {
  intent_choice: WorkspaceIntentChoice;
  tenant_id: string;
  subject_id: string;
  goal_statement: string;
  target_title?: string;
  preferred_language?: string;
  policy_acknowledged: boolean;
};

export type CreateWorkspaceIntentResponse = {
  workspace: SelfStudyWorkspace;
  intent: SelfStudyIntent;
};

export type OnboardingIntentChoice = "EXAM" | "LEARN_NEW" | "MASTER_SUBJECT";

export type SelfStudyOnboardingSession = {
  id: string;
  workspace_id: string;
  status: string;
  current_stage: string;
  topic_query: string;
  study_intent: OnboardingIntentChoice | "";
  qualification_query: string;
  jurisdiction_query: string;
  awarding_body_query: string;
  level_query: string;
  target_description: string;
  target_date: string | null;
  target_date_known: boolean;
  weekly_study_minutes: number | null;
  selected_curriculum: CurriculumCandidate | null;
  created_intent_id: string | null;
  version: number;
  next_action: SelfStudyNextAction;
};

export type CurriculumCandidate = {
  candidate_id: string;
  resolution_attempt_id: string;
  curriculum_version_id: string;
  title: string;
  subject: string;
  authority: string;
  qualification: string;
  awarding_body: string;
  jurisdiction: string;
  level: string;
  version_label: string;
  status: string;
  selectable: boolean;
  blocker_codes: string[];
  match_explanation: string;
  rank: number;
};

export type UpdateOnboardingContextPayload = Partial<{
  topic_query: string;
  study_intent: OnboardingIntentChoice;
  qualification_query: string;
  jurisdiction_query: string;
  awarding_body_query: string;
  level_query: string;
  target_description: string;
  target_date: string | null;
  target_date_known: boolean;
  weekly_study_minutes: number | null;
}> & { expected_version: number };

const workspacesPath = "self-study/workspaces/";
const workspacePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/`;
const workspaceDiagnosticExperiencePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/diagnostic/experience/`;
const workspaceDiagnosticResumePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/diagnostic/resume/`;
const workspaceDiagnosticSummaryPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/diagnostic/summary/`;
const workspacePlanExperiencePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/plan/experience/`;
const workspacePlanNodesPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/plan/nodes/`;
const workspacePlanFindingsPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/plan/findings/`;
const workspacePlanStartLearningPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/plan/start-learning/`;
const workspaceLearnExperiencePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/experience/`;
const workspaceLearnStartPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/start/`;
const workspaceLearnResumePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/resume/`;
const workspaceLearnPausePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/pause/`;
const workspaceLearnTurnsPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/turns/`;
const workspaceLearnNextTurnPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/turns/next/`;
const workspaceLearnRecapPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/recap/`;
const workspaceLearnReviewPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/review/`;
const workspaceLearnCurrentNodePath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/current-node/`;
const workspaceLearnProgressPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/progress/`;
const workspaceLearnCitationsPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/learn/citations/`;
const workspaceOnboardingSessionPath = (workspaceId: string) => `self-study/workspaces/${workspaceId}/onboarding-session/`;

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

export async function getConversationalOnboarding(workspaceId: string, signal?: AbortSignal): Promise<SelfStudyOnboardingSession | { status: "NOT_STARTED" }> {
  return (await apiRequest<SelfStudyOnboardingSession | { status: "NOT_STARTED" }>(workspaceOnboardingSessionPath(workspaceId), { signal })) as SelfStudyOnboardingSession | { status: "NOT_STARTED" };
}

export async function startConversationalOnboarding(workspaceId: string, idempotencyKey: string): Promise<SelfStudyOnboardingSession> {
  return (await apiRequest<SelfStudyOnboardingSession>(workspaceOnboardingSessionPath(workspaceId), {
    method: "POST",
    body: JSON.stringify({ idempotency_key: idempotencyKey }),
  })) as SelfStudyOnboardingSession;
}

export async function updateConversationalOnboarding(workspaceId: string, payload: UpdateOnboardingContextPayload): Promise<SelfStudyOnboardingSession> {
  return (await apiRequest<SelfStudyOnboardingSession>(`self-study/workspaces/${workspaceId}/onboarding-session/context/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  })) as SelfStudyOnboardingSession;
}

export async function resolveConversationalOnboardingCurriculum(workspaceId: string, expectedVersion: number): Promise<SelfStudyOnboardingSession> {
  return (await apiRequest<SelfStudyOnboardingSession>(`self-study/workspaces/${workspaceId}/onboarding-session/resolve-curriculum/`, {
    method: "POST",
    body: JSON.stringify({ expected_version: expectedVersion }),
  })) as SelfStudyOnboardingSession;
}

export async function listConversationalOnboardingCandidates(workspaceId: string, signal?: AbortSignal): Promise<CurriculumCandidate[]> {
  return (await apiRequest<CurriculumCandidate[]>(`self-study/workspaces/${workspaceId}/onboarding-session/curriculum-candidates/`, { signal })) ?? [];
}

export async function selectConversationalOnboardingCurriculum(workspaceId: string, expectedVersion: number, candidateId: string): Promise<SelfStudyOnboardingSession> {
  return (await apiRequest<SelfStudyOnboardingSession>(`self-study/workspaces/${workspaceId}/onboarding-session/select-curriculum/`, {
    method: "POST",
    body: JSON.stringify({ expected_version: expectedVersion, candidate_id: candidateId }),
  })) as SelfStudyOnboardingSession;
}

export async function completeConversationalOnboarding(workspaceId: string, expectedVersion: number): Promise<SelfStudyOnboardingSession> {
  return (await apiRequest<SelfStudyOnboardingSession>(`self-study/workspaces/${workspaceId}/onboarding-session/complete/`, {
    method: "POST",
    body: JSON.stringify({ expected_version: expectedVersion }),
  })) as SelfStudyOnboardingSession;
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

export async function createWorkspaceIntent(workspaceId: string, payload: CreateWorkspaceIntentPayload): Promise<CreateWorkspaceIntentResponse> {
  const intentDefaults = {
    exam: {
      desired_depth: "EXAM_PREPARATION",
      target_credential: "Exam preparation",
      pace_preference: "Structured exam preparation",
    },
    learn_new: {
      desired_depth: "GENERAL",
      target_credential: "",
      pace_preference: "Gentle exploratory learning",
    },
    master_subject: {
      desired_depth: "ACADEMIC",
      target_credential: "",
      pace_preference: "Deep mastery-oriented study",
    },
  } satisfies Record<WorkspaceIntentChoice, { desired_depth: string; target_credential: string; pace_preference: string }>;
  const selected = intentDefaults[payload.intent_choice];
  return (await apiRequest<CreateWorkspaceIntentResponse>(`self-study/workspaces/${workspaceId}/intent/`, {
    method: "POST",
    body: JSON.stringify({
      tenant_id: payload.tenant_id,
      subject_id: payload.subject_id,
      mode: "SELF_STUDY",
      goal_statement: payload.goal_statement,
      target_title: payload.target_title ?? "",
      target_outcomes: [],
      target_credential: selected.target_credential,
      preferred_curriculum_authority: "",
      jurisdiction: "",
      preferred_language: payload.preferred_language || "en",
      learner_age_band: "",
      accessibility_requirements: [],
      desired_depth: selected.desired_depth,
      pace_preference: selected.pace_preference,
      time_budget_minutes_per_week: null,
      target_completion_date: null,
      policy_acknowledged: payload.policy_acknowledged,
    }),
  })) as CreateWorkspaceIntentResponse;
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

export async function getLearningStudioExperience(workspaceId: string, signal?: AbortSignal): Promise<LearningStudioExperience> {
  return (await apiRequest<LearningStudioExperience>(workspaceLearnExperiencePath(workspaceId), { signal })) as LearningStudioExperience;
}

export async function startLearningStudio(workspaceId: string): Promise<LearningStudioExperience> {
  return (await apiRequest<LearningStudioExperience>(workspaceLearnStartPath(workspaceId), { method: "POST" })) as LearningStudioExperience;
}

export async function resumeLearningStudio(workspaceId: string): Promise<LearningStudioExperience> {
  return (await apiRequest<LearningStudioExperience>(workspaceLearnResumePath(workspaceId), { method: "POST" })) as LearningStudioExperience;
}

export async function pauseLearningStudio(workspaceId: string): Promise<LearningStudioExperience> {
  return (await apiRequest<LearningStudioExperience>(workspaceLearnPausePath(workspaceId), { method: "POST" })) as LearningStudioExperience;
}

export async function listLearningStudioTurns(workspaceId: string, signal?: AbortSignal): Promise<LearningStudioTurn[]> {
  return (await apiRequest<LearningStudioTurn[]>(workspaceLearnTurnsPath(workspaceId), { signal })) ?? [];
}

export async function submitLearningStudioTurn(workspaceId: string, text: string, idempotencyKey: string, expectedVersion: number): Promise<LearningStudioTurn> {
  return (await apiRequest<LearningStudioTurn>(workspaceLearnTurnsPath(workspaceId), {
    method: "POST",
    body: JSON.stringify({ text, idempotency_key: idempotencyKey, expected_version: expectedVersion }),
  })) as LearningStudioTurn;
}

export async function requestLearningStudioNextTurn(workspaceId: string): Promise<LearningStudioTurn> {
  return (await apiRequest<LearningStudioTurn>(workspaceLearnNextTurnPath(workspaceId), { method: "POST" })) as LearningStudioTurn;
}

export async function requestLearningStudioRecap(workspaceId: string): Promise<LearningStudioTurn> {
  return (await apiRequest<LearningStudioTurn>(workspaceLearnRecapPath(workspaceId), { method: "POST" })) as LearningStudioTurn;
}

export async function requestLearningStudioReview(workspaceId: string): Promise<LearningStudioTurn> {
  return (await apiRequest<LearningStudioTurn>(workspaceLearnReviewPath(workspaceId), { method: "POST" })) as LearningStudioTurn;
}

export async function getLearningStudioCurrentNode(workspaceId: string, signal?: AbortSignal): Promise<LearningStudioNodeSummary> {
  return (await apiRequest<LearningStudioNodeSummary>(workspaceLearnCurrentNodePath(workspaceId), { signal })) as LearningStudioNodeSummary;
}

export async function getLearningStudioProgress(workspaceId: string, signal?: AbortSignal): Promise<LearningStudioExperience["progress_summary"]> {
  return (await apiRequest<LearningStudioExperience["progress_summary"]>(workspaceLearnProgressPath(workspaceId), { signal })) as LearningStudioExperience["progress_summary"];
}

export async function listLearningStudioCitations(workspaceId: string, signal?: AbortSignal): Promise<LearningStudioCitation[]> {
  return (await apiRequest<LearningStudioCitation[]>(workspaceLearnCitationsPath(workspaceId), { signal })) ?? [];
}
