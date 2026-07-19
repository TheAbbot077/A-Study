# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: public-routes.spec.ts >> Public route smoke checks >> login page resolves
- Location: tests/smoke/public-routes.spec.ts:19:7

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('heading', { name: 'Welcome back' })
Expected: visible
Timeout: 15000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 15000ms
  - waiting for getByRole('heading', { name: 'Welcome back' })

```

```yaml
- banner:
  - link "A Abbot Study Student shell for focused, ordered learning":
    - /url: /
    - text: A
    - heading "Abbot Study" [level=1]
    - paragraph: Student shell for focused, ordered learning
  - link "Home":
    - /url: /
  - text: Loading session...
- main:
  - status:
    - paragraph: Checking your session...
- contentinfo: Foundation first. AI later. Codex carefully.
```

# Test source

```ts
  1  | import { expect, test } from "@playwright/test";
  2  | import { expectNoNextNotFound, installUnhandledApiGuard, mockAuthSession, setCsrfSession } from "./helpers/api";
  3  | 
  4  | test.describe("Public route smoke checks", () => {
  5  |   test.describe.configure({ timeout: 90_000 });
  6  | 
  7  |   test.beforeEach(async ({ context, page }, testInfo) => {
  8  |     await installUnhandledApiGuard(page, testInfo.title);
  9  |     await setCsrfSession(context);
  10 |     await mockAuthSession(page, { authenticated: false });
  11 |   });
  12 | 
  13 |   test("landing page resolves", async ({ page }) => {
  14 |     await page.goto("/", { waitUntil: "domcontentloaded" });
  15 |     await expect(page.getByText("A calm place to begin studying.")).toBeVisible({ timeout: 15_000 });
  16 |     await expectNoNextNotFound(page);
  17 |   });
  18 | 
  19 |   test("login page resolves", async ({ page }) => {
  20 |     await page.goto("/login", { waitUntil: "domcontentloaded" });
> 21 |     await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible({ timeout: 15_000 });
     |                                                                       ^ Error: expect(locator).toBeVisible() failed
  22 |     await expectNoNextNotFound(page);
  23 |   });
  24 | 
  25 |   test("signup page resolves", async ({ page }) => {
  26 |     await page.goto("/signup", { waitUntil: "domcontentloaded" });
  27 |     await expect(page.getByRole("heading", { name: "Create your study account" })).toBeVisible({ timeout: 15_000 });
  28 |     await expectNoNextNotFound(page);
  29 |   });
  30 | 
  31 |   test("unauthenticated dashboard redirects to login", async ({ page }) => {
  32 |     await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
  33 |     await expect(page).toHaveURL(/\/login\?next=%2Fdashboard/, { timeout: 15_000 });
  34 |     await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible({ timeout: 15_000 });
  35 |   });
  36 | });
  37 | 
```