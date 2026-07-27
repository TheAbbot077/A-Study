import type { LearningMemoryItem, LearningTimelineEntry } from "@/services/learning-identity";

const prohibitedMasteryLanguage = /\b(mastered|passed|certified|low ability|weak learner|visual learner)\b/i;

export function memoryItemTone(item: LearningMemoryItem): "current" | "needs-review" | "hidden" {
  if (item.status === "CONTESTED" || item.status === "STALE") return "needs-review";
  if (item.status === "HIDDEN" || item.status === "WITHDRAWN") return "hidden";
  return "current";
}

export function memoryCopyIsLearnerSafe(text: string): boolean {
  return !prohibitedMasteryLanguage.test(text);
}

export function timelineEntryLabel(entry: LearningTimelineEntry): string {
  if (entry.event_type.includes("PREFERENCE")) return "Study preference";
  if (entry.event_type.includes("OBSERVATION")) return "Learning activity";
  if (entry.event_type.includes("DECLARATION")) return "What Abbot remembers";
  return "Your journey";
}
