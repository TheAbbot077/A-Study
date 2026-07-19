import { expect, test } from "@playwright/test";
import { expectNoNextNotFound, installUnhandledApiGuard, mockAuthSession, setCsrfSession } from "./helpers/api";

test.describe("Public route smoke checks", () => {
  test.describe.configure({ timeout: 90_000 });

  test.beforeEach(async ({ context, page }, testInfo) => {
    await installUnhandledApiGuard(page, testInfo.title);
    await setCsrfSession(context);
    await mockAuthSession(page, { authenticated: false });
  });

  test("landing page resolves", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await expect(page.getByText("A calm place to begin studying.")).toBeVisible({ timeout: 15_000 });
    await expectNoNextNotFound(page);
  });

  test("login page resolves", async ({ page }) => {
    await page.goto("/login", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible({ timeout: 15_000 });
    await expectNoNextNotFound(page);
  });

  test("signup page resolves", async ({ page }) => {
    await page.goto("/signup", { waitUntil: "domcontentloaded" });
    await expect(page.getByRole("heading", { name: "Create your study account" })).toBeVisible({ timeout: 15_000 });
    await expectNoNextNotFound(page);
  });

  test("unauthenticated dashboard redirects to login", async ({ page }) => {
    await page.goto("/dashboard", { waitUntil: "domcontentloaded" });
    await expect(page).toHaveURL(/\/login\?next=%2Fdashboard/, { timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible({ timeout: 15_000 });
  });
});
