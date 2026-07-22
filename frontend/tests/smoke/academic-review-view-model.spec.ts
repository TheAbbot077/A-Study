import { expect, test } from "@playwright/test";
import {
  completionSummary,
  orderedItems,
  reviewCounts,
  reviewLifecycle,
  unresolvedFindings,
} from "../../src/features/academic-review/reviewViewModel";
import type { ReviewFinding, ReviewItem, ReviewSession } from "../../src/services/academic-review";

const session: ReviewSession = {
  id: "session-1", proposal: "proposal-1", proposal_version: "v1", version: 4,
  status: "in_progress", confidence: 0.9, reviewer_id: "reviewer-1", approved_projection_id: null,
  resource: { id: "resource-1", title: "Resource", source_label: "source.pdf" },
  summary: {
    section_accepted: 2, section_rejected: 1, section_pending: 0,
    concept_accepted: 3, concept_rejected: 1, concept_pending: 0,
    blocking_findings: 1, resolved_findings: 1, outstanding_findings: 0,
    overrides: 0, ready: true,
  },
  submitted_at: null, closed_at: null,
  created_at: "2026-07-19T10:00:00Z", updated_at: "2026-07-19T10:30:00Z",
};
const findings: ReviewFinding[] = [
  { id: 1, code: "resolved", severity: "blocking", passed: false, message: "Resolved", resolved: true },
  { id: 2, code: "warning", severity: "warning", passed: false, message: "Warning", resolved: false },
];

test("view model preserves backend order and deterministically aggregates display counts", () => {
  const items = [
    { id: 9, item_type: "section", item_id: "s1", title: "First from backend" },
    { id: 2, item_type: "concept", item_id: "c1", title: "Second from backend" },
  ] as ReviewItem[];
  expect(orderedItems(items).map(({ item }) => item.id)).toEqual([9, 2]);
  expect(reviewCounts(session)).toEqual({
    sections: { total: 3, included: 2, excluded: 1, pending: 0 },
    concepts: { total: 4, included: 3, excluded: 1, pending: 0 },
  });
});

test("completion display uses backend readiness without inferring a replacement decision", () => {
  const summary = completionSummary(session, findings);
  expect(summary.allowed).toBe(true);
  expect(summary.blockerCount).toBe(0);
  expect(summary.warningCount).toBe(1);
  expect(unresolvedFindings(findings).map((finding) => finding.id)).toEqual([2]);
  expect(reviewLifecycle("ready_for_approval")).toMatchObject({ editable: false, label: "Review completed" });
  expect(reviewLifecycle("superseded")).toMatchObject({ editable: false, label: "Superseded" });
});
