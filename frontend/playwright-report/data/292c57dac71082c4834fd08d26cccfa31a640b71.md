# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: dashboard-flow.spec.ts >> Dashboard and subject smoke flow >> subject creation navigates to a real subject detail route
- Location: tests/smoke/dashboard-flow.spec.ts:48:7

# Error details

```
Test timeout of 90000ms exceeded.
```

```
Error: page.waitForResponse: Test timeout of 90000ms exceeded.
```

# Page snapshot

```yaml
- generic [ref=e2]:
  - banner [ref=e3]:
    - generic [ref=e5]:
      - link "A Abbot Study Student shell for focused, ordered learning" [ref=e7] [cursor=pointer]:
        - /url: /
        - generic [ref=e8]: A
        - generic [ref=e9]:
          - heading "Abbot Study" [level=1] [ref=e10]
          - paragraph [ref=e11]: Student shell for focused, ordered learning
      - generic [ref=e12]:
        - link "Home" [ref=e13] [cursor=pointer]:
          - /url: /
        - generic [ref=e14]: Loading session...
  - main [ref=e15]:
    - status [ref=e17]:
      - paragraph [ref=e18]: Loading subject workspace...
  - contentinfo [ref=e19]:
    - generic [ref=e20]: Foundation first. AI later. Codex carefully.
```

# Test source

```ts
  1   | import path from "node:path";
  2   | import { expect, test } from "@playwright/test";
  3   | import {
  4   |   buildImportJob,
  5   |   buildLearningResource,
  6   |   buildReviewRequiredImportJob,
  7   |   buildSubject,
  8   |   buildValidationFinding,
  9   |   expectNoNextNotFound,
  10  |   installUnhandledApiGuard,
  11  |   mockApi,
  12  |   mockAuthSession,
  13  |   navigateToAuthenticatedRoute,
  14  |   setCsrfSession,
  15  |   setAuthenticatedSession,
  16  | } from "./helpers/api";
  17  | 
  18  | const samplePdfPath = path.resolve(process.cwd(), "tests", "fixtures", "sample.pdf");
  19  | 
  20  | test.describe("Dashboard and subject smoke flow", () => {
  21  |   test.describe.configure({ timeout: 90_000 });
  22  | 
  23  |   test.beforeEach(async ({ context, page }, testInfo) => {
  24  |     await installUnhandledApiGuard(page, testInfo.title);
  25  |     await setAuthenticatedSession(context);
  26  |     await setCsrfSession(context);
  27  |     await mockAuthSession(page, { authenticated: true });
  28  |   });
  29  | 
  30  |   test("authenticated user reaches dashboard and can log out", async ({ page }) => {
  31  |     await mockApi(page, "academic/subjects/", { json: [] });
  32  | 
  33  |     await navigateToAuthenticatedRoute(page, "/dashboard");
  34  | 
  35  |     await expect(page.getByRole("heading", { name: "Organize your study spaces" })).toBeVisible({ timeout: 15000 });
  36  |     await expectNoNextNotFound(page);
  37  | 
  38  |     const logoutResponse = page.waitForResponse((response) => {
  39  |       const url = new URL(response.url());
  40  |       return response.request().method() === "POST" && url.pathname === "/api/auth/logout/" && response.ok();
  41  |     });
  42  |     await page.getByRole("button", { name: "Log out" }).click();
  43  |     await logoutResponse;
  44  |     await page.waitForURL("/", { timeout: 60_000, waitUntil: "domcontentloaded" });
  45  |     await expect(page.getByText("A calm place to begin studying.")).toBeVisible({ timeout: 15000 });
  46  |   });
  47  | 
  48  |   test("subject creation navigates to a real subject detail route", async ({ page }) => {
  49  |     const subject = buildSubject();
  50  | 
  51  |     await mockApi(page, "academic/subjects/", { json: [] });
  52  |     await mockApi(page, "academic/subjects/", {
  53  |       method: "POST",
  54  |       status: 201,
  55  |       json: subject,
  56  |     });
  57  |     await mockApi(page, "academic/subjects/:subjectId/", { json: subject });
  58  |     await mockApi(page, "academic/learning-resources/", {
  59  |       json: [],
  60  |     });
  61  | 
  62  |     await navigateToAuthenticatedRoute(page, "/dashboard");
  63  |     await expect(page.getByRole("heading", { name: "Organize your study spaces" })).toBeVisible({ timeout: 15000 });
  64  |     await page.getByLabel("Subject name").fill("Biology");
  65  |     await page.getByLabel("Subject code").fill("BIO101");
  66  |     await page.getByLabel("Description").fill("Smoke subject");
  67  |     const createSubjectResponse = page.waitForResponse((response) => {
  68  |       const url = new URL(response.url());
  69  |       return (
  70  |         response.request().method() === "POST" &&
  71  |         url.pathname === "/api/academic/subjects/" &&
  72  |         response.status() === 201
  73  |       );
  74  |     });
> 75  |     const subjectDetailResponse = page.waitForResponse((response) => {
      |                                        ^ Error: page.waitForResponse: Test timeout of 90000ms exceeded.
  76  |       const url = new URL(response.url());
  77  |       return (
  78  |         response.request().method() === "GET" &&
  79  |         url.pathname === "/api/academic/subjects/subject-1/" &&
  80  |         response.ok()
  81  |       );
  82  |     });
  83  |     await page.getByRole("button", { name: "Create subject" }).click();
  84  |     await createSubjectResponse;
  85  |     await subjectDetailResponse;
  86  | 
  87  |     await expect(page).toHaveURL(/\/dashboard\/subjects\/subject-1$/, { timeout: 60_000 });
  88  |     await expect(page.getByRole("button", { name: "Log out" })).toBeVisible({ timeout: 15_000 });
  89  |     await expect(page.getByRole("heading", { name: "Biology" })).toBeVisible({ timeout: 15000 });
  90  |     await expectNoNextNotFound(page);
  91  |   });
  92  | 
  93  |   test("subject detail upload form posts to the canonical backend endpoints", async ({ page }) => {
  94  |     const uploadedResource = buildLearningResource({
  95  |       id: "resource-1",
  96  |       subject: "subject-1",
  97  |       stored_file: "stored-file-1",
  98  |       title: "Starter notes",
  99  |       description: "",
  100 |       status: "draft",
  101 |       source_label: "sample.pdf",
  102 |       resource_ready_for_learning: true,
  103 |     });
  104 |     const completedJob = buildImportJob({
  105 |       id: "job-1",
  106 |       learning_resource: "resource-1",
  107 |       resource_ready_for_learning: true,
  108 |     });
  109 |     const seenRequests = [];
  110 |     let resources = [];
  111 | 
  112 |     await mockApi(page, "academic/subjects/:subjectId/", {
  113 |       json: buildSubject(),
  114 |     });
  115 |     await page.route(/http:\/\/localhost:8000\/api\/academic\/learning-resources\/\?subject=subject-1$/, async (route) => {
  116 |       seenRequests.push(route.request().url());
  117 |       await route.fulfill({
  118 |         status: 200,
  119 |         contentType: "application/json",
  120 |         body: JSON.stringify(resources),
  121 |       });
  122 |     });
  123 |     await page.route(/http:\/\/localhost:8000\/api\/storage\/files\/$/, async (route) => {
  124 |       seenRequests.push(route.request().url());
  125 |       await route.fulfill({
  126 |         status: 201,
  127 |         contentType: "application/json",
  128 |         body: JSON.stringify({
  129 |           id: "stored-file-1",
  130 |           original_filename: "sample.pdf",
  131 |           stored_filename: "sample.pdf",
  132 |           content_type: "application/pdf",
  133 |           size_bytes: 512,
  134 |           checksum: "smoke",
  135 |           provider: "local",
  136 |           created_at: "2026-07-12T00:00:00Z",
  137 |           updated_at: "2026-07-12T00:00:00Z",
  138 |         }),
  139 |       });
  140 |     });
  141 |     await page.route(/http:\/\/localhost:8000\/api\/academic\/learning-resources\/$/, async (route) => {
  142 |       seenRequests.push(route.request().url());
  143 |       resources = [uploadedResource];
  144 |       await route.fulfill({
  145 |         status: 201,
  146 |         contentType: "application/json",
  147 |         body: JSON.stringify(uploadedResource),
  148 |       });
  149 |     });
  150 |     await page.route(/http:\/\/localhost:8000\/api\/content-intelligence\/import-jobs\/$/, async (route) => {
  151 |       seenRequests.push(route.request().url());
  152 |       await route.fulfill({
  153 |         status: 201,
  154 |         contentType: "application/json",
  155 |         body: JSON.stringify({
  156 |           ...buildImportJob({
  157 |             ...completedJob,
  158 |             status: "processing",
  159 |             status_detail: "processing",
  160 |             resource_ready_for_learning: false,
  161 |           }),
  162 |         }),
  163 |       });
  164 |     });
  165 |     await mockApi(page, "content-intelligence/import-jobs/:importJobId/", { json: completedJob });
  166 | 
  167 |     await navigateToAuthenticatedRoute(page, "/dashboard/subjects/subject-1");
  168 |     await expect(page.getByRole("heading", { name: "Biology" })).toBeVisible({ timeout: 15000 });
  169 |     await expect(page.getByLabel("File")).toBeVisible({ timeout: 15000 });
  170 |     await page.getByLabel("Resource title").fill("Starter notes");
  171 |     await page.getByLabel("File").setInputFiles(samplePdfPath);
  172 |     await page.getByRole("button", { name: "Upload PDF or DOCX" }).click();
  173 | 
  174 |     await expect(
  175 |       page.getByRole("article").filter({ hasText: "Starter notes" }).getByText("Completed", { exact: true }),
```