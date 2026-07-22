import type { SelfStudyDiagnosticExperience, SelfStudyPlanExperience, SelfStudyPlanNodeSummary } from "@/services/self-study";

export function diagnosticExperienceTitle(experience: SelfStudyDiagnosticExperience): string {
  switch (experience.status) {
    case "READY_TO_START":
      return "You’re ready for your diagnostic";
    case "IN_PROGRESS":
      return "Resume your diagnostic";
    case "AWAITING_SCORING":
      return "Your diagnostic is being scored";
    case "COMPLETE":
      return "Your diagnostic summary is ready";
    case "STALE":
    case "INVALIDATED":
      return "Your diagnostic needs attention";
    case "BLOCKED":
    case "NOT_READY":
    default:
      return "Diagnostic is not ready yet";
  }
}

export function diagnosticProgressLabel(experience: SelfStudyDiagnosticExperience): string {
  const answered = experience.progress.answered;
  const maximum = experience.progress.maximum_items;
  if (!maximum) return "No diagnostic items have been started.";
  return `${answered} of ${maximum} diagnostic items recorded.`;
}

export function coverageMeaning(coverageState: string): string {
  switch (coverageState) {
    case "COVERED":
      return "Materials are available for this part.";
    case "PARTIAL":
      return "Some support exists, but it may not be enough.";
    case "MISSING":
      return "Required material is not available yet.";
    case "CONFLICTING":
      return "Materials disagree or contain unresolved conflict.";
    case "OUT_OF_SCOPE":
      return "Uploaded material does not support this curriculum area.";
    case "SUPPLEMENTARY":
      return "Helpful extra material exists, but it is not core support.";
    case "NOT_APPLICABLE":
      return "Material coverage is not required for this node.";
    case "UNEVALUATED":
    default:
      return "Coverage has not been evaluated yet.";
  }
}

export function planReadinessLabel(plan: SelfStudyPlanExperience): string {
  if (plan.can_start_learning) return "Start learning with Abbot";
  if (plan.blocker_codes.includes("TEACHING_NOT_PREPARED")) return "Your study plan is being prepared";
  if (plan.blocker_codes.length) return "Your study plan needs attention";
  return "Your study plan is waiting for governed readiness";
}

export function planNodeTone(node: SelfStudyPlanNodeSummary): "ready" | "blocked" | "optional" {
  if (node.blocked) return "blocked";
  if (!node.dependency_summary.required) return "optional";
  return "ready";
}
