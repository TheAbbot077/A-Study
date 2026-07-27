import type { LearningStudioExperience, LearningStudioTurn } from "@/services/self-study";

export function studioStatusTitle(experience: LearningStudioExperience): string {
  if (experience.blocker_codes.length) return "Learning is blocked for now";
  switch (experience.session_status) {
    case "NOT_STARTED":
      return "Ready to start learning with Abbot";
    case "PENDING":
    case "ACTIVE":
      return "Learning with Abbot";
    case "AWAITING_LEARNER":
      return "Your turn";
    case "PAUSED":
      return "Paused";
    case "NODE_COMPLETE":
      return "Ready for concept check";
    case "COMPLETED":
      return "Study plan teaching is complete";
    case "STALE":
    case "INVALIDATED":
    case "BLOCKED":
      return "Learning needs attention";
    default:
      return "Learning Studio";
  }
}

export function studioProgressLabel(experience: LearningStudioExperience): string {
  const progress = experience.progress_summary;
  if (!progress.total_teaching_segments) return "No teaching segments have started yet.";
  return `${progress.completed_teaching_segments} of ${progress.total_teaching_segments} teaching segments completed.`;
}

export function turnAuthorLabel(turn: LearningStudioTurn): string {
  if (turn.role === "ABBOT") return "Abbot";
  if (turn.role === "LEARNER") return "You";
  return "System";
}

export function turnActionLabel(action: string): string {
  return action
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function canSubmitLearnerMessage(experience: LearningStudioExperience, pending: boolean, text: string): boolean {
  return experience.can_send_message && !pending && text.trim().length > 0;
}
