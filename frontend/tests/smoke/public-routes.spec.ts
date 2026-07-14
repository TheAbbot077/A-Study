import { expect, test } from "@playwright/test";
import { expectNoNextNotFound, installUnhandledApiGuard, mockAuthSession, setCsrfSession } from "./helpers/api";

test.describe("Public route smoke checks", () => {
  test.beforeEach(async ({ context, page }, testInfo) => {
    await installUnhandledApiGuard(page, testInfo.title);
    await setCsrfSession(context);
    await mockAuthSession(page, { authenticated: false });
  });

  test("landing page resolves", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText("A calm place to begin studying.")).toBeVisible();
    await expectNoNextNotFound(page);
  });

  test("login page resolves", async ({ page }) => {
    await page.goto("/login");
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
    await expectNoNextNotFound(page);
  });

  test("signup page resolves", async ({ page }) => {
    await page.goto("/signup");
    await expect(page.getByRole("heading", { name: "Create your study account" })).toBeVisible();
    await expectNoNextNotFound(page);
  });

  test("unauthenticated dashboard redirects to login", async ({ page }) => {
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login\?next=%2Fdashboard/);
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  });
});
