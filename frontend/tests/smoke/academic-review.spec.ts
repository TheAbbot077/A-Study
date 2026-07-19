import { expect, test } from "@playwright/test";
import { buildCurrentUser, installUnhandledApiGuard, mockApi, mockAuthSession, navigateToAuthenticatedRoute, setAuthenticatedSession, setCsrfSession } from "./helpers/api";

test.describe("Academic proposal review smoke flow", () => {
  test.describe.configure({ timeout: 90_000 });
  test.beforeEach(async ({ context, page }, testInfo) => {
    await installUnhandledApiGuard(page, testInfo.title); await setAuthenticatedSession(context); await setCsrfSession(context);
    await mockAuthSession(page, { authenticated: true, user: buildCurrentUser({ institutions: [{ id: "institution-1", name: "Smoke Study Space", slug: "smoke-study-space", role: "reviewer", institution_type: "individual" }] }) });
  });

  test("reviewer opens the immutable proposal workspace", async ({ page }) => {
    const session = { id: "review-1", proposal: "proposal-1", proposal_version: "6c6-proposal-1", version: 2, status: "in_progress", confidence: 0.728, reviewer_id: "user-1", resource: { id: "resource-1", title: "Economics module", source_label: "economics.pdf" }, summary: { section_accepted: 0, section_rejected: 0, section_pending: 1, concept_accepted: 0, concept_rejected: 0, concept_pending: 1, blocking_findings: 1, resolved_findings: 0, outstanding_findings: 1, overrides: 0, ready: false } };
    await mockApi(page, "academic-review/sessions/proposals/:proposalId/start/", { method: "POST", status: 201, json: session });
    await mockApi(page, "academic-review/sessions/:sessionId/outline/", { query: { limit: "500", offset: "0" }, json: { count: 2, next: null, previous: null, results: [{ id: 1, item_type: "section", item_id: "section-1", title: "Market Structure", confidence: 0.8, decision: "pending", reason: "", edit: null }, { id: 2, item_type: "concept", item_id: "concept-1", title: "Perfect competition", confidence: 0.82, decision: "pending", reason: "", edit: null }] } });
    await mockApi(page, "academic-review/sessions/:sessionId/findings/", { json: [{ id: 1, code: "section_page_ratio", severity: "blocking", passed: false, message: "The proposal contains unusually many sections.", resolved: false }] });
    await navigateToAuthenticatedRoute(page, "/dashboard/academic-review/proposal-1");
    await expect(page.getByRole("heading", { name: "Economics module" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: "Reject TOC-derived items" })).toBeVisible();
    await expect(page.getByText("Perfect competition")).toBeVisible();
    await expect(page.getByText(/Outstanding: The proposal contains unusually many sections/)).toBeVisible();
    await expect(page.getByRole("button", { name: "Submit for approval" })).toBeDisabled();
  });
});
