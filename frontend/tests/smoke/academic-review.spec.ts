import { expect, test } from "@playwright/test";
import {
  buildCurrentUser,
  installUnhandledApiGuard,
  mockApi,
  mockAuthSession,
  navigateToAuthenticatedRoute,
  setAuthenticatedSession,
  setCsrfSession,
} from "./helpers/api";

const proposalId = "11111111-1111-4111-8111-111111111111";
const sessionId = "22222222-2222-4222-8222-222222222222";
const session = {
  id: sessionId,
  proposal: proposalId,
  proposal_version: "6c6-proposal-1",
  version: 2,
  status: "in_progress",
  confidence: 0.728,
  reviewer_id: "user-1",
  approved_projection_id: null,
  resource: { id: "resource-1", title: "Economics module", source_label: "economics.pdf" },
  summary: {
    section_accepted: 0, section_rejected: 0, section_pending: 1,
    concept_accepted: 0, concept_rejected: 0, concept_pending: 1,
    blocking_findings: 1, resolved_findings: 0, outstanding_findings: 1,
    overrides: 0, ready: false,
  },
  submitted_at: null,
  closed_at: null,
  created_at: "2026-07-19T10:00:00Z",
  updated_at: "2026-07-19T10:30:00Z",
};
const outline = {
  count: 2, next: null, previous: null,
  results: [
    { id: 1, item_type: "section", item_id: "section-1", title: "Market Structure", confidence: 0.8, decision: "pending", reason: "", decided_at: null, edit: null },
    { id: 2, item_type: "concept", item_id: "concept-1", title: "Perfect competition", confidence: 0.82, decision: "pending", reason: "", decided_at: null, edit: null },
  ],
};
const findings = [{ id: 1, code: "section_page_ratio", severity: "blocking", passed: false, message: "The proposal contains unusually many sections.", resolved: false }];

test.describe("Academic proposal review workspace", () => {
  test.beforeEach(async ({ context, page }, testInfo) => {
    await installUnhandledApiGuard(page, testInfo.title);
    await setAuthenticatedSession(context);
    await setCsrfSession(context);
    await mockAuthSession(page, {
      authenticated: true,
      user: buildCurrentUser({
        institutions: [{ id: "institution-1", name: "Smoke Study Space", slug: "smoke-study-space", role: "reviewer", institution_type: "individual" }],
      }),
    });
    await mockApi(page, "academic-review/sessions/proposals/:proposalId/start/", { method: "POST", status: 201, json: session });
    await mockApi(page, "academic-review/sessions/:sessionId/outline/", { query: { limit: "500", offset: "0" }, json: outline });
    await mockApi(page, "academic-review/sessions/:sessionId/findings/", { json: findings });
    await mockApi(page, "academic-review/sessions/:sessionId/items/:decisionId/evidence/", {
      json: [{ id: 10, page_start: 4, page_end: 5, evidence_strength: "direct", confidence: 0.94, hierarchy: "Chapter 2", semantic_segment_id: "segment-1", block_id: "block-1", supporting_text: "Markets coordinate buyers and sellers." }],
    });
    await mockApi(page, "academic-review/sessions/:sessionId/", { json: session });
  });

  test("reviewer inspects ordered items, evidence, findings, and backend readiness", async ({ page }) => {
    await navigateToAuthenticatedRoute(page, `/dashboard/academic-review/${proposalId}`);

    await expect(page.getByRole("heading", { name: "Economics module" })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Governed content workflow" })).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Proposal items" })).toContainText("1. section");
    await page.getByRole("button", { name: /Perfect competition/ }).click();
    await expect(page.getByRole("heading", { name: "Source evidence" })).toBeVisible();
    const evidenceRegion = page.getByRole("region", { name: "Source evidence" });
    await evidenceRegion.getByText(/Pages 4/).click();
    await expect(evidenceRegion.getByText("Markets coordinate buyers and sellers.")).toBeVisible();
    await expect(page.getByText("Blocker · Unresolved")).toBeVisible();
    await expect(page.getByRole("button", { name: "Complete human review" })).toBeDisabled();
    await expect(page.getByRole("button", { name: /Approve/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: /Populate/ })).toHaveCount(0);
  });

  test("unsaved editor input is visibly retained", async ({ page }) => {
    await navigateToAuthenticatedRoute(page, `/dashboard/academic-review/${proposalId}`);
    const title = page.getByLabel("Reviewed title");
    await title.fill("Reviewed market structure");
    await expect(title).toHaveValue("Reviewed market structure");
    await expect(page.getByText("Unsaved changes")).toBeVisible();
  });

  test("supported decision command uses the exact PI-6D.1 endpoint and payload", async ({ page }) => {
    let payload: unknown;
    await page.route("**/api/academic-review/sessions/*/items/*/decide/", async (route) => {
      if (route.request().method() !== "POST") return route.fallback();
      payload = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ...outline.results[0], decision: "accepted", reason: "Evidence verified" }),
      });
    });
    await navigateToAuthenticatedRoute(page, `/dashboard/academic-review/${proposalId}`);
    await page.getByLabel("Review note").fill("Evidence verified");
    await page.getByRole("button", { name: "Include item" }).click();

    await expect.poll(() => payload).toEqual({ decision: "accepted", reason: "Evidence verified" });
    expect(payload).not.toHaveProperty("expected_session_version");
    expect(payload).not.toHaveProperty("idempotency_key");
  });
});
