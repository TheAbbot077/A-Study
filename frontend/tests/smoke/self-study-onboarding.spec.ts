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

const workspaceId = "81111111-1111-4111-8111-111111111111";
const curriculumVersionId = "82222222-2222-4222-8222-222222222222";
const resolverCandidateId = "83333333-3333-4333-8333-333333333333";

const workspace = {
  id: workspaceId,
  tenant_id: "institution-1",
  learner_id: "user-1",
  display_name: "Biology",
  description: "A learner-owned Biology workspace",
  status: "INTENT_REQUIRED",
  intent_id: null,
  curriculum_resolution_id: null,
  published_graph_id: null,
  active_diagnostic_id: null,
  latest_coverage_evaluation_id: null,
  active_bridge_plan_id: null,
  active_teaching_preparation_id: null,
  active_teaching_session_id: null,
  created_at: "2026-07-24T08:00:00Z",
  updated_at: "2026-07-24T08:00:00Z",
  archived_at: null,
  version: 1,
};

function nextAction(overrides = {}) {
  return {
    code: "UPLOAD_MATERIALS",
    title: "Add your materials",
    explanation: "Attach or upload materials before the diagnostic.",
    primary_cta_label: "Add materials",
    target_route: `/dashboard/self-study/${workspaceId}/materials`,
    blocker_codes: [],
    safe_ids: { workspace_id: workspaceId },
    safe_status_summary: { workspace_status: "MATERIALS_REQUIRED" },
    ...overrides,
  };
}

function session(overrides = {}) {
  return {
    id: "onboarding-1",
    workspace_id: workspaceId,
    status: "COLLECTING_CONTEXT",
    current_stage: "STUDY_TOPIC",
    topic_query: "",
    study_intent: "",
    qualification_query: "",
    jurisdiction_query: "",
    awarding_body_query: "",
    level_query: "",
    target_description: "",
    target_date: null,
    target_date_known: false,
    weekly_study_minutes: null,
    selected_curriculum: null,
    created_intent_id: null,
    version: 1,
    next_action: nextAction({ code: "COMPLETE_INTENT", title: "Tell Abbot what you want to learn", primary_cta_label: "Start onboarding" }),
    ...overrides,
  };
}

const candidate = {
  candidate_id: resolverCandidateId,
  resolution_attempt_id: "resolution-1",
  curriculum_version_id: curriculumVersionId,
  title: "Cambridge International AS & A Level Biology",
  subject: "Biology",
  authority: "Cambridge International",
  qualification: "A Level",
  awarding_body: "Cambridge International",
  jurisdiction: "International",
  level: "A Level",
  version_label: "2026",
  status: "ACTIVE",
  selectable: true,
  blocker_codes: [],
  match_explanation: "Matched your topic and curriculum context.",
  rank: 1,
};

test.describe("Self-study conversational onboarding", () => {
  test.describe.configure({ timeout: 120_000 });

  test.beforeEach(async ({ context, page }, testInfo) => {
    await installUnhandledApiGuard(page, testInfo.title);
    await setAuthenticatedSession(context);
    await setCsrfSession(context);
    await mockAuthSession(page, {
      authenticated: true,
      user: buildCurrentUser(),
    });
    await mockApi(page, "self-study/workspaces/:workspaceId/", { json: workspace });
  });

  test("learner discovers and selects a governed curriculum without typing a subject id", async ({ page }) => {
    let current = null as ReturnType<typeof session> | null;
    let startObserved = false;
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/`, async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(current ?? { status: "NOT_STARTED" }) });
        return;
      }
      startObserved = true;
      current = session();
      await route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(current) });
    });
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/context/`, async (route) => {
      const payload = route.request().postDataJSON();
      const previous = current ?? session();
      current = session({
        ...previous,
        ...payload,
        current_stage: "CURRICULUM_DISCOVERY",
        version: previous.version + 1,
      });
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(current) });
    });
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/resolve-curriculum/`, async (route) => {
      const previous = current ?? session();
      current = session({ ...previous, status: "AWAITING_CURRICULUM_SELECTION", current_stage: "CURRICULUM_SELECTION", version: previous.version + 1 });
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(current) });
    });
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/curriculum-candidates/`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([candidate]) });
    });
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/select-curriculum/`, async (route) => {
      expect(route.request().postDataJSON()).toMatchObject({ candidate_id: resolverCandidateId });
      const previous = current ?? session();
      current = session({ ...previous, selected_curriculum: candidate, status: "REVIEWING_SUMMARY", current_stage: "WEEKLY_AVAILABILITY", version: previous.version + 1 });
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(current) });
    });
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/complete/`, async (route) => {
      const previous = current ?? session();
      current = session({ ...previous, status: "COMPLETED", current_stage: "COMPLETED", created_intent_id: "intent-1", next_action: nextAction(), version: previous.version + 1 });
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(current) });
    });

    await navigateToAuthenticatedRoute(page, `/dashboard/self-study/${workspaceId}/intent`);

    await expect(page.getByRole("heading", { name: "Let’s find the right governed curriculum" })).toBeVisible();
    await expect(page.getByText("Governed subject ID")).toHaveCount(0);
    await page.getByRole("button", { name: "Start onboarding" }).click();
    expect(startObserved).toBe(true);
    await page.getByLabel("What would you like to study?").fill("Biology");
    await page.getByLabel("I want to study to sit for an exam").check();
    await page.getByLabel("Exam, qualification, or curriculum").fill("Cambridge International A Level");
    await page.getByLabel("Weekly study time").selectOption("5");
    await page.getByRole("button", { name: "Save answers" }).click();
    await page.getByRole("button", { name: "Find governed curricula" }).click();
    await expect(page.getByText("Cambridge International AS & A Level Biology")).toBeVisible();
    await page.getByRole("button", { name: "Select curriculum" }).click();
    await expect(page.getByRole("heading", { name: "Onboarding summary" })).toBeVisible();
    await page.getByRole("button", { name: "Complete onboarding" }).click();
    await expect(page.getByRole("link", { name: "Add materials" })).toBeVisible();
  });

  test("verified curriculum without self-study subject binding is blocked safely", async ({ page }) => {
    const unboundCandidate = {
      ...candidate,
      candidate_id: "84444444-4444-4444-8444-444444444444",
      selectable: false,
      blocker_codes: ["CURRICULUM_SUBJECT_BINDING_MISSING"],
      match_explanation: "This curriculum is verified, but it is not yet available for self-study.",
    };
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(session({ status: "AWAITING_CURRICULUM_SELECTION", current_stage: "CURRICULUM_SELECTION", topic_query: "Biology", study_intent: "EXAM" })) });
    });
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/curriculum-candidates/`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([unboundCandidate]) });
    });

    await navigateToAuthenticatedRoute(page, `/dashboard/self-study/${workspaceId}/intent`);

    await expect(page.getByText("This curriculum is verified, but it is not yet available for self-study.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Select curriculum" })).toBeDisabled();
    await expect(page.getByText("Governed subject ID")).toHaveCount(0);
  });

  test("no governed curriculum match stays safe and does not fabricate a syllabus", async ({ page }) => {
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(session({ status: "AWAITING_CURRICULUM_SELECTION", current_stage: "CURRICULUM_SELECTION", topic_query: "Moon botany", study_intent: "LEARN_NEW" })) });
    });
    await page.route(`**/api/self-study/workspaces/${workspaceId}/onboarding-session/curriculum-candidates/`, async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
    });

    await navigateToAuthenticatedRoute(page, `/dashboard/self-study/${workspaceId}/intent`);

    await expect(page.getByText("No governed curriculum match yet")).toBeVisible();
    await expect(page.getByText("Abbot will not create an unverified syllabus.")).toBeVisible();
  });
});
