import type { SelfStudyNextAction, SelfStudyOnboardingSummary, WorkspaceMaterial } from "@/services/self-study";

export function workspaceStatusLabel(status: string): string {
  return status
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function nextActionTone(action: SelfStudyNextAction): "ready" | "waiting" | "blocked" | "neutral" {
  if (["START_DIAGNOSTIC", "RESUME_DIAGNOSTIC", "START_LEARNING", "RESUME_LEARNING"].includes(action.code)) {
    return "ready";
  }
  if (["WAIT_FOR_PROCESSING", "WAIT_FOR_MAPPING", "WAIT_FOR_BRIDGE_PLAN", "WAIT_FOR_TEACHING_PREPARATION"].includes(action.code)) {
    return "waiting";
  }
  if (["RESOLVE_MATERIAL_ISSUES", "CONTACT_SUPPORT", "NO_ACTION_AVAILABLE"].includes(action.code)) {
    return "blocked";
  }
  return "neutral";
}

export function materialStatusSummary(materials: WorkspaceMaterial[]): string {
  if (!materials.length) return "No materials attached yet.";
  const counts = materials.reduce<Record<string, number>>((accumulator, material) => {
    accumulator[material.status] = (accumulator[material.status] ?? 0) + 1;
    return accumulator;
  }, {});
  return Object.entries(counts)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([status, count]) => `${count} ${workspaceStatusLabel(status)}`)
    .join(", ");
}

export function hasBlockingOnboarding(summary: SelfStudyOnboardingSummary | null): boolean {
  return Boolean(summary?.blocker_codes.length || summary?.next_action.blocker_codes.length);
}
