import type { CurriculumCandidate, SelfStudyOnboardingSession } from "@/services/self-study";
import { workspaceStatusLabel } from "./workspaceViewModel";

export function onboardingStageTitle(session: SelfStudyOnboardingSession | null): string {
  if (!session) return "Start onboarding";
  if (session.status === "COMPLETED") return "Onboarding complete";
  if (session.current_stage === "CURRICULUM_SELECTION") return "Choose a governed curriculum";
  if (session.current_stage === "SUMMARY") return "Review your onboarding summary";
  return workspaceStatusLabel(session.current_stage);
}

export function candidateSubtitle(candidate: CurriculumCandidate): string {
  return [candidate.authority, candidate.level, candidate.jurisdiction].filter(Boolean).join(" · ");
}

export function normalLearnerPromptContainsRawSubjectId(text: string): boolean {
  const normalized = text
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
  return /\b(?:academic\s+|governed\s+)?subject\s+(?:id|uuid|identifier)\b/.test(normalized);
}
