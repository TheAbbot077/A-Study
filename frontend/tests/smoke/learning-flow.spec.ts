import { expect, test } from "@playwright/test";
import {
  buildConcept,
  buildConceptBrowserState,
  buildLearningResource,
  buildMasteryCheckSnapshot,
  buildRemediationPlan,
  buildReviewRequiredImportJob,
  buildSection,
  buildSubject,
  expectNoNextNotFound,
  installUnhandledApiGuard,
  mockApi,
  mockAuthSession,
  navigateToAuthenticatedRoute,
  setCsrfSession,
  setAuthenticatedSession,
} from "./helpers/api";

test.describe("Resource, concept, and assessment smoke flow", () => {
  async function mockConceptHierarchy(page: import("@playwright/test").Page) {
    await mockApi(page, "academic/content-concepts/:conceptId/", { json: buildConcept() });
    await mockApi(page, "academic/content-sections/:sectionId/", { json: buildSection() });
    await mockApi(page, "academic/learning-resources/:resourceId/", { json: buildLearningResource() });
    await mockApi(page, "academic/subjects/:subjectId/", { json: buildSubject() });
  }

  test.beforeEach(async ({ context, page }, testInfo) => {
    await installUnhandledApiGuard(page, testInfo.title);
    await setAuthenticatedSession(context);
    await setCsrfSession(context);
    await mockAuthSession(page, { authenticated: true });
  });

  test("resource detail route resolves and shows low-confidence warning", async ({ page }) => {
    await mockApi(page, "academic/learning-resources/:resourceId/", {
      json: buildLearningResource({
        id: "resource-1",
        subject: "subject-1",
        title: "Unit 1 Notes",
        description: "Imported notes",
        resource_ready_for_learning: true,
      }),
    });
    await mockApi(page, "academic/subjects/:subjectId/", {
      json: buildSubject(),
    });
    await page.route(/http:\/\/localhost:8000\/api\/academic\/content-sections\/\?learning_resource=resource-1$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([buildSection()]),
      });
    });
    await page.route(/http:\/\/localhost:8000\/api\/academic\/content-concepts\/\?learning_resource=resource-1$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([buildConcept()]),
      });
    });
    await page.route(/http:\/\/localhost:8000\/api\/learning\/pedagogical-sessions\/concept-browser\/\?learning_resource=resource-1$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([buildConceptBrowserState()]),
      });
    });
    await page.route(/http:\/\/localhost:8000\/api\/content-intelligence\/import-jobs\/\?learning_resource=resource-1$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "job-1",
            learning_resource: "resource-1",
            stored_file: "stored-file-1",
            format_type: "pdf",
            status: "completed",
            status_detail: "completed",
            requested_by: "user-1",
            error_message: "",
            ocr_requested: false,
            ocr_used: false,
            extraction_confidence: 0.72,
            section_confidence: 0.77,
            concept_confidence: 0.79,
            structural_confidence: 0.78,
            metadata: {},
            retry_count: 0,
            failure_details: null,
            resource_ready_for_learning: true,
            created_at: "2026-07-12T00:00:00Z",
            updated_at: "2026-07-12T00:00:00Z",
            validation_findings: [],
          },
        ]),
      });
    });

    await navigateToAuthenticatedRoute(page, "/dashboard/resources/resource-1");

    await expect(page.getByRole("heading", { name: "Unit 1 Notes" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Low-confidence import warning")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("heading", { name: "Cell Structure", level: 4 })).toBeVisible({ timeout: 15000 });
    await expectNoNextNotFound(page);
  });

  test("resource detail represents ready for review without official Academic content", async ({ page }) => {
    await mockApi(page, "academic/learning-resources/:resourceId/", {
      json: buildLearningResource({
        id: "resource-review",
        subject: "subject-1",
        title: "Economics module",
        resource_ready_for_learning: false,
      }),
    });
    await mockApi(page, "academic/subjects/:subjectId/", { json: buildSubject() });
    await mockApi(page, "academic/content-sections/", {
      query: { learning_resource: "resource-review" },
      json: [],
    });
    await mockApi(page, "academic/content-concepts/", {
      query: { learning_resource: "resource-review" },
      json: [],
    });
    await mockApi(page, "learning/pedagogical-sessions/concept-browser/", {
      query: { learning_resource: "resource-review" },
      json: [],
    });
    await mockApi(page, "content-intelligence/import-jobs/", {
      query: { learning_resource: "resource-review" },
      json: [buildReviewRequiredImportJob({ learning_resource: "resource-review" })],
    });

    await navigateToAuthenticatedRoute(page, "/dashboard/resources/resource-review");

    await expect(page.getByRole("heading", { name: "Ready for review" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("navigation", { name: "Governed content workflow" })).toBeVisible();
    await expect(page.getByText("No official Academic sections or concepts exist yet.")).toBeVisible();
    await expect(page.getByText("Academic review required", { exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Retry import" })).toHaveCount(0);
    await expect(page.getByRole("link", { name: /Next concept/ })).toHaveCount(0);
  });

  test("concept learning route resolves and question flow stays on a valid route", async ({ page }) => {
    await mockApi(page, "academic/content-concepts/:conceptId/", {
      json: buildConcept(),
    });
    await mockApi(page, "academic/content-sections/:sectionId/", {
      json: buildSection(),
    });
    await mockApi(page, "academic/learning-resources/:resourceId/", {
      json: buildLearningResource(),
    });
    await mockApi(page, "academic/subjects/:subjectId/", {
      json: buildSubject(),
    });
    await page.route(/http:\/\/localhost:8000\/api\/learning\/pedagogical-sessions\/concept-browser\/\?learning_resource=resource-1$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          buildConceptBrowserState({
            status: "in_progress",
            action_label: "Continue concept",
            session_id: "session-1",
            session_status: "active",
          }),
        ]),
      });
    });
    await mockApi(page, "learning/pedagogical-sessions/:sessionId/conversation/", {
      json: {
        session: {
          id: "session-1",
          learner: "user-1",
          content_concept: "concept-1",
          status: "active",
          started_at: "2026-07-12T00:00:00Z",
          ended_at: null,
          created_at: "2026-07-12T00:00:00Z",
          updated_at: "2026-07-12T00:00:00Z",
        },
        turns: [
          {
            sequence_number: 1,
            sender_type: "abbot",
            message_type: "explanation",
            content: "A cell contains organelles with specialized roles.",
            timestamp: "2026-07-12T00:00:00Z",
            metadata: {},
          },
        ],
        next_expected_interaction: "clarification",
        streaming_supported: false,
      },
    });
    await mockApi(page, "learning/pedagogical-sessions/:sessionId/ask/", {
      method: "POST",
      json: {
        response: {
          session_id: "session-1",
          concept_title: "Cell Structure",
          response_type: "clarification",
          sections: [],
          source_references: [],
          strategy_used: "Guided Practice",
          metadata: {},
        },
        conversation: {
          session: {
            id: "session-1",
            learner: "user-1",
            content_concept: "concept-1",
            status: "active",
            started_at: "2026-07-12T00:00:00Z",
            ended_at: null,
            created_at: "2026-07-12T00:00:00Z",
            updated_at: "2026-07-12T00:00:00Z",
          },
          turns: [
            {
              sequence_number: 1,
              sender_type: "abbot",
              message_type: "explanation",
              content: "A cell contains organelles with specialized roles.",
              timestamp: "2026-07-12T00:00:00Z",
              metadata: {}
            },
            {
              sequence_number: 2,
              sender_type: "learner",
              message_type: "learner_question",
              content: "What does the nucleus do?",
              timestamp: "2026-07-12T00:00:10Z",
              metadata: {}
            },
            {
              sequence_number: 3,
              sender_type: "abbot",
              message_type: "clarification",
              content: "The nucleus stores genetic material and helps regulate activity.",
              timestamp: "2026-07-12T00:00:11Z",
              metadata: {}
            }
          ],
          next_expected_interaction: "reflection",
          streaming_supported: false
        }
      },
    });

    await navigateToAuthenticatedRoute(page, "/dashboard/concepts/concept-1?session=session-1");

    await expect(page.getByRole("heading", { name: "Cell Structure" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("A cell contains organelles with specialized roles.")).toBeVisible({ timeout: 15000 });
    await expectNoNextNotFound(page);

    await page.getByLabel("Ask The Abbot a question").fill("What does the nucleus do?");
    await page.getByRole("button", { name: "Ask The Abbot" }).click();
    await expect(
      page.getByText("The nucleus stores genetic material and helps regulate activity.", { exact: true }),
    ).toBeVisible({ timeout: 15000 });
  });

  test("assessment route resolves for mastery success", async ({ page }) => {
    await mockConceptHierarchy(page);
    await mockApi(page, "assessments/mastery-check/", {
      query: { content_concept: "concept-1" },
      json: buildMasteryCheckSnapshot({
        delivery_session: {
            id: "delivery-1",
            assessment: "assessment-1",
            learner: "user-1",
            assessment_attempt: "attempt-1",
            status: "completed",
            current_sequence_number: 1,
            started_at: "2026-07-12T00:00:00Z",
            submitted_at: "2026-07-12T00:10:00Z",
            completed_at: "2026-07-12T00:10:10Z",
            metadata: {},
            created_at: "2026-07-12T00:00:00Z",
            updated_at: "2026-07-12T00:10:10Z"
        },
        result: {
            id: "result-1",
            attempt: "attempt-1",
            total_score: 5,
            max_score: 5,
            percentage: 100,
            passed: true,
            result_data: {},
            created_at: "2026-07-12T00:10:10Z",
            updated_at: "2026-07-12T00:10:10Z"
        },
        mastery_profile: {
            id: "profile-1",
            learner: "user-1",
            content_concept: "concept-1",
            current_decision: "mastered",
            confidence: 0.96,
            evidence_count: 3,
            last_evidence_at: "2026-07-12T00:10:10Z",
            created_at: "2026-07-12T00:10:10Z",
            updated_at: "2026-07-12T00:10:10Z"
        },
        next_available_concept_id: "concept-2",
        next_available_concept_title: "Cell Transport",
        can_start: false,
        can_submit: false,
        is_complete: true
      }),
    });

    await navigateToAuthenticatedRoute(page, "/dashboard/concepts/concept-1/assessment?session=session-1");
    await expect(page.getByRole("heading", { name: "Cell Structure" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Mastery success")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("link", { name: /Next concept/ })).toBeVisible({ timeout: 15000 });
    await expectNoNextNotFound(page);
  });

  test("assessment route resolves for remediation", async ({ page }) => {
    await mockConceptHierarchy(page);
    await mockApi(page, "assessments/mastery-check/", {
      query: { content_concept: "concept-1" },
      json: buildMasteryCheckSnapshot({
        mastery_profile: {
            id: "profile-1",
            learner: "user-1",
            content_concept: "concept-1",
            current_decision: "needs_review",
            confidence: 0.52,
            evidence_count: 2,
            last_evidence_at: "2026-07-12T00:10:10Z",
            created_at: "2026-07-12T00:10:10Z",
            updated_at: "2026-07-12T00:10:10Z"
        },
        remediation_plan: buildRemediationPlan(),
        next_available_concept_id: null,
        next_available_concept_title: null,
        can_start: true,
        can_submit: false,
        is_complete: false
      }),
    });
    await mockApi(page, "remediation/plans/:planId/start/", {
      method: "POST",
      json: {
        id: "plan-1",
        status: "active",
        rationale: "Review this concept again.",
      },
    });

    await navigateToAuthenticatedRoute(page, "/dashboard/concepts/concept-1/assessment?session=session-1");
    await expect(page.getByRole("heading", { name: "Cell Structure" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Remediation available")).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole("button", { name: "Start remediation" })).toBeVisible({ timeout: 15000 });
    await expectNoNextNotFound(page);
  });
});
