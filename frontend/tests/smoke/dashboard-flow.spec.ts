import path from "node:path";
import { expect, test } from "@playwright/test";
import {
  buildImportJob,
  buildLearningResource,
  buildProcessingJob,
  buildReviewRequiredImportJob,
  buildSubject,
  buildValidationFinding,
  expectNoNextNotFound,
  installUnhandledApiGuard,
  mockApi,
  mockAuthSession,
  navigateToAuthenticatedRoute,
  setCsrfSession,
  setAuthenticatedSession,
} from "./helpers/api";

const samplePdfPath = path.resolve(process.cwd(), "tests", "fixtures", "sample.pdf");

test.describe("Dashboard and subject smoke flow", () => {
  test.describe.configure({ timeout: 90_000 });

  test.beforeEach(async ({ context, page }, testInfo) => {
    await installUnhandledApiGuard(page, testInfo.title);
    await setAuthenticatedSession(context);
    await setCsrfSession(context);
    await mockAuthSession(page, { authenticated: true });
  });

  test("authenticated user reaches dashboard and can log out", async ({ page }) => {
    await mockApi(page, "academic/subjects/", { json: [] });

    await navigateToAuthenticatedRoute(page, "/dashboard");

    await expect(page.getByRole("heading", { name: "Organize your study spaces" })).toBeVisible({ timeout: 15000 });
    await expectNoNextNotFound(page);

    const logoutResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return response.request().method() === "POST" && url.pathname === "/api/auth/logout/" && response.ok();
    });
    await page.getByRole("button", { name: "Log out" }).click();
    await logoutResponse;
    await page.waitForURL("/", { timeout: 60_000, waitUntil: "domcontentloaded" });
    await expect(page.getByText("A calm place to begin studying.")).toBeVisible({ timeout: 15000 });
  });

  test("subject creation navigates to a real subject detail route", async ({ page }) => {
    const subject = buildSubject();

    await mockApi(page, "academic/subjects/", { json: [] });
    await mockApi(page, "academic/subjects/", {
      method: "POST",
      status: 201,
      json: subject,
    });
    await mockApi(page, "academic/subjects/:subjectId/", { json: subject });
    await mockApi(page, "academic/learning-resources/", {
      json: [],
    });

    await navigateToAuthenticatedRoute(page, "/dashboard");
    await expect(page.getByRole("heading", { name: "Organize your study spaces" })).toBeVisible({ timeout: 15000 });
    await page.getByLabel("Subject name").fill("Biology");
    await page.getByLabel("Subject code").fill("BIO101");
    await page.getByLabel("Description").fill("Smoke subject");
    const createSubjectResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return (
        response.request().method() === "POST" &&
        url.pathname === "/api/academic/subjects/" &&
        response.status() === 201
      );
    });
    const subjectDetailResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());
      return (
        response.request().method() === "GET" &&
        url.pathname === "/api/academic/subjects/subject-1/" &&
        response.ok()
      );
    });
    await page.getByRole("button", { name: "Create subject" }).click();
    await createSubjectResponse;
    await subjectDetailResponse;

    await expect(page).toHaveURL(/\/dashboard\/subjects\/subject-1$/, { timeout: 60_000 });
    await expect(page.getByRole("button", { name: "Log out" })).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Biology" })).toBeVisible({ timeout: 15000 });
    await expectNoNextNotFound(page);
  });

  test("new upload hands off from legacy lineage to canonical processing polling", async ({ page }) => {
    const uploadedResource = buildLearningResource({
      id: "resource-1",
      subject: "subject-1",
      stored_file: "stored-file-1",
      title: "Starter notes",
      description: "",
      status: "draft",
      source_label: "sample.pdf",
      resource_ready_for_learning: false,
    });
    const legacyJob = buildImportJob({
      id: "job-1",
      learning_resource: "resource-1",
      processing_job_id: "processing-job-1",
      processing_status: "QUEUED",
      processing_stage: "queued",
      processing_progress: 5,
      resource_ready_for_learning: false,
    });
    const seenRequests: string[] = [];
    const canonicalStatuses: string[] = [];
    let canonicalPolls = 0;
    let legacyDetailPolls = 0;
    let resources: ReturnType<typeof buildLearningResource>[] = [];

    await mockApi(page, "academic/subjects/:subjectId/", {
      json: buildSubject(),
    });
    await page.route(/http:\/\/localhost:8000\/api\/academic\/learning-resources\/\?subject=subject-1$/, async (route) => {
      seenRequests.push(route.request().url());
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(resources),
      });
    });
    await page.route(/http:\/\/localhost:8000\/api\/storage\/files\/$/, async (route) => {
      seenRequests.push(route.request().url());
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          id: "stored-file-1",
          original_filename: "sample.pdf",
          stored_filename: "sample.pdf",
          content_type: "application/pdf",
          size_bytes: 512,
          checksum: "smoke",
          provider: "local",
          created_at: "2026-07-12T00:00:00Z",
          updated_at: "2026-07-12T00:00:00Z",
        }),
      });
    });
    await page.route(/http:\/\/localhost:8000\/api\/academic\/learning-resources\/$/, async (route) => {
      seenRequests.push(route.request().url());
      resources = [uploadedResource];
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify(uploadedResource),
      });
    });
    await page.route(/http:\/\/localhost:8000\/api\/content-intelligence\/import-jobs\/$/, async (route) => {
      seenRequests.push(route.request().url());
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({
          ...buildImportJob({
            ...legacyJob,
            status: "processing",
            status_detail: "processing",
            resource_ready_for_learning: false,
          }),
        }),
      });
    });
    await page.route("**/api/content-processing/jobs/processing-job-1/", async (route) => {
      canonicalPolls += 1;
      const canonical = canonicalPolls === 1
        ? buildProcessingJob({ status: "INSPECTING", stage: "inspecting", progress: 10, stage_label: "Inspecting the document" })
        : canonicalPolls === 2
          ? buildProcessingJob()
          : buildProcessingJob({
              status: "READY_FOR_REVIEW",
              stage: "validating",
              progress: 98,
              stage_label: "Ready for academic review",
              review_required: true,
              can_cancel: false,
              completed_at: "2026-07-20T09:20:00Z",
            });
      canonicalStatuses.push(String(canonical.status));
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(canonical) });
    });
    await page.route("**/api/content-intelligence/import-jobs/job-1/", async (route) => {
      legacyDetailPolls += 1;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(legacyJob) });
    });

    await navigateToAuthenticatedRoute(page, "/dashboard/subjects/subject-1");
    await expect(page.getByRole("heading", { name: "Biology" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByLabel("File")).toBeVisible({ timeout: 15000 });
    await page.getByLabel("Resource title").fill("Starter notes");
    await page.getByLabel("File").setInputFiles(samplePdfPath);
    await page.getByRole("button", { name: "Upload PDF or DOCX" }).click();

    await expect(
      page.getByRole("article").filter({ hasText: "Starter notes" }).getByRole("heading", { name: "Ready for review" }),
    ).toBeVisible({ timeout: 20_000 });
    const uploadedCard = page.getByRole("article").filter({ hasText: "Starter notes" });
    await expect(uploadedCard.getByText("98% processed — governed review required")).toBeVisible();
    await expect(uploadedCard.getByText(/Processing job: processing-job-1/)).toBeVisible();
    expect(canonicalStatuses).toEqual(["INSPECTING", "EXTRACTING", "READY_FOR_REVIEW"]);
    expect(legacyDetailPolls).toBe(0);
    expect(seenRequests).toEqual(
      expect.arrayContaining([
        "http://localhost:8000/api/storage/files/",
        "http://localhost:8000/api/academic/learning-resources/",
        "http://localhost:8000/api/content-intelligence/import-jobs/",
      ]),
    );
  });

  test("subject detail renders completed, review, warning, and failed import states", async ({ page }) => {
    await mockApi(page, "academic/subjects/:subjectId/", {
      json: buildSubject(),
    });
    await page.route(/http:\/\/localhost:8000\/api\/academic\/learning-resources\/\?subject=subject-1$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          buildLearningResource({
            id: "resource-complete",
            subject: "subject-1",
            title: "Complete",
            description: "",
            status: "active",
            source_label: "complete.pdf",
            resource_ready_for_learning: true,
          }),
          buildLearningResource({
            id: "resource-warning",
            subject: "subject-1",
            title: "Warning",
            description: "",
            status: "active",
            source_label: "warning.pdf",
            resource_ready_for_learning: true,
          }),
          buildLearningResource({
            id: "resource-review",
            subject: "subject-1",
            title: "Review required",
            description: "",
            status: "draft",
            source_label: "review.pdf",
            resource_ready_for_learning: false,
          }),
          buildLearningResource({
            id: "resource-failed",
            subject: "subject-1",
            title: "Failed",
            description: "",
            status: "draft",
            source_label: "failed.pdf",
            resource_ready_for_learning: false,
          }),
        ]),
      });
    });
    await page.route(/http:\/\/localhost:8000\/api\/content-intelligence\/import-jobs\/\?learning_resource=resource-complete$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          buildImportJob({
            id: "job-complete",
            learning_resource: "resource-complete",
            status: "completed",
            status_detail: "completed",
            resource_ready_for_learning: true,
            validation_findings: [],
          }),
        ]),
      });
    });
    await page.route(/http:\/\/localhost:8000\/api\/content-intelligence\/import-jobs\/\?learning_resource=resource-warning$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          buildImportJob({
            id: "job-warning",
            learning_resource: "resource-warning",
            status: "completed",
            status_detail: "completed_with_warnings",
            resource_ready_for_learning: true,
            validation_findings: [buildValidationFinding()],
          }),
        ]),
      });
    });
    await page.route(/http:\/\/localhost:8000\/api\/content-intelligence\/import-jobs\/\?learning_resource=resource-failed$/, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          buildImportJob({
            id: "job-failed",
            learning_resource: "resource-failed",
            status: "failed",
            status_detail: "failed",
            error_message: "Unable to extract sufficient text from this document.",
            ocr_requested: true,
            ocr_used: false,
            resource_ready_for_learning: false,
            failure_details: { failure_reason: "extracted_text_below_threshold" },
            validation_findings: [],
          }),
        ]),
      });
    });
    await mockApi(page, "content-intelligence/import-jobs/", {
      query: { learning_resource: "resource-review" },
      json: [buildReviewRequiredImportJob({ id: "job-review", learning_resource: "resource-review" })],
    });

    await navigateToAuthenticatedRoute(page, "/dashboard/subjects/subject-1");
    await expect(page.getByRole("heading", { name: "Biology" })).toBeVisible({ timeout: 15000 });

    await expect(
      page.getByRole("article").filter({ hasText: "complete.pdf" }).getByText("Completed", { exact: true }),
    ).toBeVisible({ timeout: 15000 });
    await expect(
      page.getByRole("article").filter({ hasText: "warning.pdf" }).getByText("Completed with warnings", { exact: true }),
    ).toBeVisible({ timeout: 15000 });
    await expect(
      page
        .getByRole("article")
        .filter({ hasText: "failed.pdf" })
        .locator("span")
        .filter({ hasText: /^Processing failed$/ }),
    ).toBeVisible({ timeout: 15000 });
    const reviewCard = page.getByRole("article").filter({ hasText: "review.pdf" });
    await expect(reviewCard.getByRole("heading", { name: "Ready for review" })).toBeVisible({ timeout: 15000 });
    await expect(reviewCard.getByText("Proposed sections")).toBeVisible();
    await expect(reviewCard.getByText("376", { exact: true })).toBeVisible();
    await expect(reviewCard.getByText("Proposed concepts")).toBeVisible();
    await expect(reviewCard.getByText("166", { exact: true })).toBeVisible();
    await expect(reviewCard.getByRole("button", { name: "Retry import" })).toHaveCount(0);
    await expect(reviewCard.getByText("Import is still running.")).toHaveCount(0);
    await expect(reviewCard.getByRole("link", { name: "Open resource outline" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Validation warnings" })).toBeVisible({ timeout: 15000 });
    await expect(page.getByText("Unable to extract sufficient text from this document.")).toBeVisible({ timeout: 15000 });
  });

  test("failed upload deletion uses the canonical import-job endpoint", async ({ page }) => {
    const failedResource = buildLearningResource({
      id: "resource-failed",
      subject: "subject-1",
      title: "Failed upload",
      status: "draft",
      source_label: "failed.pdf",
      resource_ready_for_learning: false,
    });
    await mockApi(page, "academic/subjects/:subjectId/", { json: buildSubject() });
    await mockApi(page, "academic/learning-resources/", {
      query: { subject: "subject-1" },
      json: [failedResource],
    });
    await mockApi(page, "content-intelligence/import-jobs/", {
      query: { learning_resource: "resource-failed" },
      json: [buildImportJob({ id: "job-failed", learning_resource: "resource-failed", status: "failed" })],
    });
    await mockApi(page, "content-intelligence/import-jobs/:importJobId/", {
      method: "DELETE",
      status: 204,
    });

    await navigateToAuthenticatedRoute(page, "/dashboard/subjects/subject-1");
    const card = page.getByRole("article").filter({ hasText: "failed.pdf" });
    const deleteAction = card.getByRole("button", { name: "Delete failed upload", exact: true });
    await expect(deleteAction).toHaveCount(1);
    await deleteAction.click();
    const deleteRequest = page.waitForRequest((request) => {
      const url = new URL(request.url());
      return (
        request.method() === "DELETE" &&
        url.pathname.endsWith("/api/content-intelligence/import-jobs/job-failed/")
      );
    });
    await page
      .getByRole("dialog", { name: "Delete failed upload" })
      .getByRole("button", { name: "Delete failed upload", exact: true })
      .click();
    await deleteRequest;
  });
});
