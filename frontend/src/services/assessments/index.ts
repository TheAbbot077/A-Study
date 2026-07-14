import { apiRequest } from "@/services/api";

export type AssessmentSummary = {
  id: string;
  content_concept: string;
  title: string;
  description: string;
  state: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AssessmentDeliverySession = {
  id: string;
  assessment: string;
  learner: string;
  assessment_attempt?: string | null;
  status: "created" | "active" | "paused" | "submitted" | "completed" | "abandoned";
  current_sequence_number: number;
  started_at?: string | null;
  submitted_at?: string | null;
  completed_at?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type AssessmentOption = {
  id: string;
  label: string;
  content: string;
};

export type AssessmentQuestion = {
  id: string;
  sequence_number: number;
  item_type: string;
  prompt: string;
  options?: AssessmentOption[];
  response_data?: Record<string, unknown> | null;
  submitted: boolean;
  source_type: string;
};

export type AssessmentResult = {
  id: string;
  attempt: string;
  total_score: number;
  max_score: number;
  percentage?: number | null;
  passed?: boolean | null;
  result_data?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MasteryProfile = {
  id: string;
  learner: string;
  content_concept: string;
  current_decision: string;
  confidence: number;
  evidence_count: number;
  last_evidence_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type LearningEvidence = {
  id: string;
  source_type: string;
  source_id: string;
  evidence_type: string;
  score?: number | null;
  confidence: number;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type RemediationPlanSummary = {
  id: string;
  status: string;
  rationale: string;
  started_at?: string | null;
  completed_at?: string | null;
  recommendations: Array<{
    id: string;
    recommendation_type: string;
    title: string;
    rationale: string;
    priority: number;
  }>;
  activities: Array<{
    id: string;
    activity_type: string;
    title: string;
    instructions: string;
    status: string;
  }>;
};

export type MasteryCheckSnapshot = {
  content_concept_id: string;
  assessment: AssessmentSummary | null;
  delivery_session: AssessmentDeliverySession | null;
  questions: AssessmentQuestion[];
  current_question_id: string | null;
  result: AssessmentResult | null;
  mastery_profile: MasteryProfile | null;
  evidence: LearningEvidence[];
  remediation_plan: RemediationPlanSummary | null;
  next_available_concept_id: string | null;
  next_available_concept_title: string | null;
  can_start: boolean;
  can_submit: boolean;
  is_complete: boolean;
};

export async function getMasteryCheck(contentConceptId: string): Promise<MasteryCheckSnapshot> {
  return (await apiRequest<MasteryCheckSnapshot>(`assessments/mastery-check/?content_concept=${encodeURIComponent(contentConceptId)}`)) as MasteryCheckSnapshot;
}

export async function startMasteryCheck(contentConceptId: string): Promise<MasteryCheckSnapshot> {
  return (await apiRequest<MasteryCheckSnapshot>("assessments/mastery-check/start/", {
    method: "POST",
    body: JSON.stringify({ content_concept: contentConceptId }),
  })) as MasteryCheckSnapshot;
}

export async function submitAssessmentAnswer(
  deliverySessionId: string,
  itemId: string,
  responseData: Record<string, unknown>,
): Promise<MasteryCheckSnapshot> {
  return (await apiRequest<MasteryCheckSnapshot>(`assessments/mastery-check/${deliverySessionId}/submit-answer/`, {
    method: "POST",
    body: JSON.stringify({ item_id: itemId, response_data: responseData }),
  })) as MasteryCheckSnapshot;
}

export async function completeMasteryCheck(deliverySessionId: string): Promise<MasteryCheckSnapshot> {
  return (await apiRequest<MasteryCheckSnapshot>(`assessments/mastery-check/${deliverySessionId}/complete/`, {
    method: "POST",
    body: JSON.stringify({}),
  })) as MasteryCheckSnapshot;
}
