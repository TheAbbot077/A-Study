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

const proposalId = "31111111-1111-4111-8111-111111111111";
const sessionId = "32222222-2222-4222-8222-222222222222";
const projectionId = "33333333-3333-4333-8333-333333333333";
const baseSession = {
  id: sessionId, proposal: proposalId, proposal_version: "proposal-v1", version: 7,
  status: "ready_for_approval", confidence: 0.91, reviewer_id: "user-1",
  approved_projection_id: null,
  resource: { id: "resource-1", title: "Economics module", source_label: "economics.pdf" },
  summary: {
    section_accepted: 1, section_rejected: 0, section_pending: 0,
    concept_accepted: 1, concept_rejected: 0, concept_pending: 0,
    blocking_findings: 0, resolved_findings: 0, outstanding_findings: 0,
    overrides: 0, ready: true,
  },
  submitted_at: "2026-07-19T10:00:00Z", closed_at: null,
  created_at: "2026-07-19T09:00:00Z", updated_at: "2026-07-19T10:00:00Z",
};
const approvedSession = { ...baseSession, status: "approved", approved_projection_id: projectionId };

test("completed review advances through separate approval and population commands", async ({ context, page }, testInfo) => {
  await installUnhandledApiGuard(page, testInfo.title);
  await setAuthenticatedSession(context);
  await setCsrfSession(context);
  await mockAuthSession(page, {
    authenticated: true,
    user: buildCurrentUser({
      is_staff: true,
      institutions: [{ id: "institution-1", name: "Governance University", slug: "governance", role: "administrator", institution_type: "university" }],
    }),
  });
  await mockApi(page, "academic-review/sessions/proposals/:proposalId/start/", { method: "POST", status: 201, json: baseSession });
  await mockApi(page, "academic-review/sessions/:sessionId/", { json: approvedSession });
  await mockApi(page, "academic-review/sessions/:sessionId/evaluate-readiness/", {
    method: "POST", status: 201,
    json: {
      id: "snapshot-1", proposal_version: "proposal-v1", review_session_version: 7, ready: true,
      pending_sections: 0, pending_concepts: 0, accepted_sections: 1, accepted_concepts: 1,
      rejected_sections: 0, rejected_concepts: 0, blocking_findings: 0, resolved_findings: 0,
      orphan_concepts: 0, invalid_hierarchy: 0, duplicate_titles: 0, override_count: 0,
      policy_version: "6d2", reasons: [], checksum: "snapshot-checksum", evaluated_at: "2026-07-19T10:05:00Z",
    },
  });
  let approvalPayload: unknown;
  await page.route("**/api/academic-review/sessions/*/approve/", async (route) => {
    approvalPayload = route.request().postDataJSON();
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ projection_id: projectionId, status: "ready_for_population", approval_version: "approval-v1" }) });
  });
  await mockApi(page, "academic-review/projections/:projectionId/", {
    json: {
      id: projectionId, proposal_id: proposalId, session_id: sessionId, approval_decision_id: "decision-1",
      approval_version: "approval-v1", projection_version: "projection-v1", resource_id: "resource-1",
      subject_id: "subject-1", institution_id: "institution-1", status: "ready_for_population",
      checksum: "projection-checksum", hierarchy_checksum: "hierarchy", concepts_checksum: "concepts",
      provenance_checksum: "provenance", created_at: "2026-07-19T10:06:00Z",
      sections: [{ id: 1, source_proposed_section: "source-section-1", final_title: "Markets", canonical_title: "markets", parent_id: null, ordinal: 1, depth: 1, page_range: { start: 1, end: 4 }, evidence_references: [] }],
      concepts: [{ id: 1, source_proposed_concept: "source-concept-1", approved_section_id: 1, final_title: "Competition", canonical_title: "competition", ordinal: 1, page_range: { start: 2, end: 3 }, supporting_evidence: [] }],
    },
  });
  let populated = false;
  await page.route(`**/api/academic-review/projections/${projectionId}/population-readiness/`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      approved_projection_id: projectionId, status: populated ? "populated" : "ready", ready: !populated,
      expected_section_count: 1, expected_concept_count: 1,
      existing_population_run_id: populated ? "run-1" : null, blockers: [],
    }) });
  });
  let populationPayload: unknown;
  await page.route("**/api/academic-review/projections/*/populate/", async (route) => {
    populationPayload = route.request().postDataJSON();
    populated = true;
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify({ population_run_id: "run-1", approved_projection_id: projectionId, status: "populated", resource_id: "resource-1", created_sections: 1, matched_sections: 0, created_concepts: 1, matched_concepts: 0, failed_items: 0, populated_at: "2026-07-19T10:10:00Z" }) });
  });
  await mockApi(page, "academic-review/population-runs/:runId/", {
    json: {
      id: "run-1", approved_projection_id: projectionId, approval_decision_id: "decision-1",
      resource_id: "resource-1", subject_id: "subject-1", status: "populated",
      projection_fingerprint: "projection-checksum", created_section_count: 1,
      matched_section_count: 0, created_concept_count: 1, matched_concept_count: 0,
      failure_code: "", failure_message: "", started_at: "2026-07-19T10:09:00Z",
      completed_at: "2026-07-19T10:10:00Z", failed_at: null,
    },
  });
  let synchronized = false;
  let synchronizationPayload: unknown;
  const synchronizationRun = {
    id: "sync-run-1", academic_population_run_id: "run-1", approved_projection_id: projectionId,
    processing_job_id: "processing-1", resource_id: "resource-1", subject_id: "subject-1",
    trigger: "staff", reason: "", status: "synchronized", source_fingerprint: "source-fingerprint",
    manifest_fingerprint: "manifest-fingerprint", retrieval_generation_id: "generation-1",
    planned_chunk_count: 1, indexed_chunk_count: 1, keyword_indexed_count: 1,
    vector_indexed_count: 1, failed_chunk_count: 0, citation_coverage: 1,
    failure_code: "", failure_message: "", retry_eligible: false,
    started_at: "2026-07-19T10:11:00Z", completed_at: "2026-07-19T10:12:00Z",
    failed_at: null, created_at: "2026-07-19T10:11:00Z",
  };
  await page.route("**/api/academic-review/population-runs/run-1/retrieval-readiness/", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      academic_population_run_id: "run-1", resource_id: "resource-1", ready: true,
      source_fingerprint: "source-fingerprint", expected_section_count: 1, expected_concept_count: 1,
      existing_synchronization_run_id: synchronized ? "sync-run-1" : null,
      active_generation_id: synchronized ? "generation-1" : null, blockers: [], warnings: [],
    }) });
  });
  await page.route("**/api/academic-review/population-runs/run-1/synchronize-retrieval/", async (route) => {
    synchronizationPayload = route.request().postDataJSON();
    synchronized = true;
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(synchronizationRun) });
  });
  await mockApi(page, "retrieval/synchronization-runs/:runId/", { json: synchronizationRun });
  let evaluated = false;
  let evaluationPayload: unknown;
  const evaluation = {
    id: "evaluation-1", resource_id: "resource-1", subject_id: "subject-1",
    processing_job_id: "processing-1", processing_attempt_id: "attempt-1",
    approved_projection_id: projectionId, approval_decision_id: "decision-1",
    academic_population_run_id: "run-1", retrieval_synchronization_run_id: "sync-run-1",
    retrieval_generation_id: "generation-1", trigger: "staff", reason: "",
    lineage_fingerprint: "lineage-fingerprint", policy_version: "teaching-readiness-v1",
    decision: "ready", checks_passed: 1, checks_failed: 0, blocker_count: 0,
    warning_count: 0, snapshot: {}, checks: [{
      code: "READINESS_GENERATION_ACTIVE", category: "retrieval", passed: true,
      severity: "blocker", expected: "active", observed: "active",
      explanation: "The retrieval generation is active.", related_ids: ["generation-1"],
    }], invalidation_reason: "", invalidated_at: null,
    supersedes_evaluation_id: null, evaluated_at: "2026-07-19T10:13:00Z",
  };
  await page.route("**/api/academic/learning-resources/resource-1/teaching-readiness/", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({
      resource_id: "resource-1", status: evaluated ? "ready_for_teaching" : "not_ready",
      latest_evaluation_id: evaluated ? "evaluation-1" : null, decision: evaluated ? "ready" : null,
      lineage_fingerprint: evaluated ? "lineage-fingerprint" : undefined,
      policy_version: evaluated ? "teaching-readiness-v1" : undefined,
      checks_passed: evaluated ? 1 : undefined, checks_failed: evaluated ? 0 : undefined,
      blocker_count: 0, warning_count: 0, blockers: [], warnings: [],
      can_evaluate: true, can_reevaluate: evaluated,
    }) });
  });
  await page.route("**/api/academic/learning-resources/resource-1/teaching-readiness/evaluate/", async (route) => {
    evaluationPayload = route.request().postDataJSON();
    evaluated = true;
    await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(evaluation) });
  });

  await navigateToAuthenticatedRoute(page, `/dashboard/academic-review/${proposalId}/governance`);
  const workflowNavigation = page.getByRole("navigation", { name: "Governed content workflow" });
  await expect(workflowNavigation).toBeVisible();
  await expect(workflowNavigation.getByText("Approval", { exact: true })).toBeVisible();
  await expect(page.getByText("Backend approval readiness: Ready for approval.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Populate Academic Platform" })).toHaveCount(0);
  await page.getByRole("button", { name: "Approve proposal" }).click();
  await page.getByRole("button", { name: "Confirm approval" }).click();
  await expect.poll(() => approvalPayload).toMatchObject({
    readiness_snapshot_id: "snapshot-1",
    expected_session_version: 7,
  });
  expect(approvalPayload).toHaveProperty("idempotency_key");
  await expect(page.getByRole("heading", { name: "2. Immutable approved projection" })).toBeVisible();
  await page.getByRole("button", { name: "Populate Academic Platform" }).click();
  await expect(page.getByText("It does not synchronize retrieval and does not make the resource ready for teaching.")).toBeVisible();
  await page.getByRole("button", { name: "Create official Academic content" }).click();
  await expect.poll(() => populationPayload).toMatchObject({ expected_fingerprint: "projection-checksum" });
  expect(populationPayload).toHaveProperty("idempotency_key");
  await expect(page.getByText("Status: populated")).toBeVisible();
  await page.getByRole("button", { name: "Synchronize retrieval" }).click();
  await expect(page.getByText("It does not mark the resource ready for teaching.")).toBeVisible();
  await page.getByRole("button", { name: "Start synchronization" }).click();
  await expect.poll(() => synchronizationPayload).toMatchObject({ expected_source_fingerprint: "source-fingerprint" });
  expect(synchronizationPayload).toHaveProperty("idempotency_key");
  await expect(page.getByText("Retrieval is synchronized. This does not grant teaching readiness.")).toBeVisible();
  await expect(page.getByText("NOT EVALUATED", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Evaluate teaching readiness" }).click();
  await page.getByRole("button", { name: "Request evaluation" }).click();
  await expect.poll(() => evaluationPayload).toMatchObject({ expected_lineage_fingerprint: "" });
  expect(evaluationPayload).toHaveProperty("idempotency_key");
  await expect(page.getByText("READY FOR TEACHING", { exact: true })).toBeVisible();
  await expect(page.getByText("This does not mean it is learner-published.")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole("navigation", { name: "Governed content workflow" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Reevaluate teaching readiness" })).toBeVisible();
});
