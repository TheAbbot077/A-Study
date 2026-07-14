import { apiRequest } from "@/services/api";

export type ConceptBrowserStatus = {
  concept_id: string;
  status: "locked" | "available" | "in_progress" | "mastered" | "needs_remediation";
  can_start_or_resume: boolean;
  action_label?: string | null;
  session_id?: string | null;
  session_status?: string | null;
  mastery_decision?: string | null;
  remediation_plan_id?: string | null;
};

export type PedagogicalSession = {
  id: string;
  learner: string;
  content_concept: string;
  status: "created" | "active" | "paused" | "completed" | "abandoned";
  started_at: string;
  ended_at?: string | null;
  created_at: string;
  updated_at: string;
};

export type ConversationTurn = {
  sequence_number: number;
  sender_type: "learner" | "abbot" | "ariel" | "system";
  message_type: string;
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
};

export type SourceReference = {
  academic_object_type: string;
  object_id: string;
  title: string;
  relationship: string;
  sequence_number?: number | null;
};

export type AbbotResponseSection = {
  sequence_number: number;
  title: string;
  content: string;
  source_reference_ids?: string[];
  metadata?: Record<string, unknown>;
};

export type AbbotTeachingResponse = {
  session_id: string;
  concept_title: string;
  response_type: "teaching" | "clarification" | "summary" | "system";
  sections: AbbotResponseSection[];
  source_references: SourceReference[];
  strategy_used?: string | null;
  metadata?: Record<string, unknown>;
};

export type LearningConversationState = {
  session: PedagogicalSession;
  turns: ConversationTurn[];
  next_expected_interaction: string;
  streaming_supported: boolean;
};

export type LearningResponseEnvelope = {
  response: AbbotTeachingResponse;
  conversation: LearningConversationState;
};

export async function listConceptBrowserStates(resourceId: string): Promise<ConceptBrowserStatus[]> {
  return (
    (await apiRequest<ConceptBrowserStatus[]>(
      `learning/pedagogical-sessions/concept-browser/?learning_resource=${encodeURIComponent(resourceId)}`,
    )) ?? []
  );
}

export async function startOrResumeConcept(conceptId: string): Promise<PedagogicalSession> {
  return (await apiRequest<PedagogicalSession>("learning/pedagogical-sessions/start-or-resume/", {
    method: "POST",
    body: JSON.stringify({ content_concept: conceptId }),
  })) as PedagogicalSession;
}

export async function getSessionConversation(sessionId: string): Promise<LearningConversationState> {
  return (await apiRequest<LearningConversationState>(`learning/pedagogical-sessions/${sessionId}/conversation/`)) as LearningConversationState;
}

export async function teachSession(sessionId: string): Promise<LearningResponseEnvelope> {
  return (await apiRequest<LearningResponseEnvelope>(`learning/pedagogical-sessions/${sessionId}/teach/`, {
    method: "POST",
    body: JSON.stringify({}),
  })) as LearningResponseEnvelope;
}

export async function askSessionQuestion(sessionId: string, question: string): Promise<LearningResponseEnvelope> {
  return (await apiRequest<LearningResponseEnvelope>(`learning/pedagogical-sessions/${sessionId}/ask/`, {
    method: "POST",
    body: JSON.stringify({ question }),
  })) as LearningResponseEnvelope;
}
