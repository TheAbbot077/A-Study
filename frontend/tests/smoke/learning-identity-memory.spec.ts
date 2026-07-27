import { expect, test } from "@playwright/test";
import { memoryCopyIsLearnerSafe, memoryItemTone, timelineEntryLabel } from "../../src/features/learning-identity/memoryViewModel";
import type { LearningMemoryItem, LearningTimelineEntry } from "../../src/services/learning-identity";

const item = (status: string): LearningMemoryItem => ({
  id: "memory-1",
  kind: "observation",
  label: "Diagnostic completed",
  value: "Recorded after a diagnostic",
  classification: "OBSERVED",
  source_summary: "Recorded after you completed a diagnostic",
  last_updated_at: "2026-07-26T00:00:00Z",
  status,
  currently_used: status === "ACTIVE",
  allowed_actions: status === "ACTIVE" ? ["contest"] : [],
});

test("learning identity memory tones keep contested and hidden states distinct", () => {
  expect(memoryItemTone(item("ACTIVE"))).toBe("current");
  expect(memoryItemTone(item("CONTESTED"))).toBe("needs-review");
  expect(memoryItemTone(item("WITHDRAWN"))).toBe("hidden");
});

test("learning identity copy avoids mastery and profiling language", () => {
  expect(memoryCopyIsLearnerSafe("Recorded after you completed a diagnostic. This is not a grade.")).toBe(true);
  expect(memoryCopyIsLearnerSafe("You mastered cellular respiration.")).toBe(false);
  expect(memoryCopyIsLearnerSafe("You are a visual learner.")).toBe(false);
});

test("timeline labels stay learner-facing rather than governance-facing", () => {
  const entry = (event_type: string): LearningTimelineEntry => ({
    timeline_id: event_type,
    occurred_at: "2026-07-26T00:00:00Z",
    recorded_at: "2026-07-26T00:00:00Z",
    event_type,
    title: "Memory updated",
    description: "You changed a study preference.",
    classification: "PREFERENCE",
    disposition: "ACTIVE",
    source_summary: "Chosen by you",
    related_profile_version: 1,
  });

  expect(timelineEntryLabel(entry("PREFERENCE_SELECTED"))).toBe("Study preference");
  expect(timelineEntryLabel(entry("OBSERVATION_RECORDED"))).toBe("Learning activity");
  expect(timelineEntryLabel(entry("DECLARATION_WITHDRAWN"))).toBe("What Abbot remembers");
});
