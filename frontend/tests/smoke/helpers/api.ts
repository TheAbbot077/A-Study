import { expect, type BrowserContext, type Page, type Route } from "@playwright/test";

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api").replace(/\/$/, "");
const API_BASE = new URL(API_BASE_URL);
const API_BASE_PATH = API_BASE.pathname.replace(/\/$/, "");
const SMOKE_APP_ORIGIN = new URL(process.env.SMOKE_BASE_URL ?? "http://localhost:3000").origin;

export type MockOptions = {
  method?: string;
  status?: number;
  json?: unknown;
  text?: string;
  contentType?: string;
  query?: Record<string, string>;
};

export type MockAuthUser = {
  id: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
  profile: {
    display_name: string;
    timezone: string;
    preferred_language: string;
  };
  institutions: Array<{
    id: string;
    name: string;
    slug: string;
    role: string;
    institution_type: string;
  }>;
};

export function apiUrl(pathname: string) {
  const normalized = pathname.startsWith("/") ? pathname.slice(1) : pathname;
  return `${API_BASE_URL}/${normalized}`;
}

function canonicalApiPath(pathname: string) {
  const normalized = pathname.startsWith("/") ? pathname : `/${pathname}`;
  return `${API_BASE_PATH}${normalized}`.replace(/\/+/g, "/");
}

function matchesApiPath(requestUrl: string, pathname: string, query?: Record<string, string>) {
  const url = new URL(requestUrl);
  const requestPath = url.pathname.replace(/\/+$/, "/");
  const routePath = canonicalApiPath(pathname).replace(/:([A-Za-z0-9_]+)/g, "[^/]+");
  const expression = new RegExp(`^${routePath}$`);
  return expression.test(requestPath) && Object.entries(query ?? {}).every(([key, value]) => url.searchParams.get(key) === value);
}

function apiRouteMatcher(pathname: string, query?: Record<string, string>) {
  return (requestUrl: URL | string) => matchesApiPath(String(requestUrl), pathname, query);
}

const mockResponseHeaders = {
  "Access-Control-Allow-Credentials": "true",
  "Access-Control-Allow-Headers": "Accept, Content-Type, X-CSRFToken",
  "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS, POST, PUT, PATCH, DELETE",
  "Access-Control-Allow-Origin": SMOKE_APP_ORIGIN,
  "Cache-Control": "no-store",
};

export async function setAuthenticatedSession(context: BrowserContext) {
  await context.addCookies([
    {
      name: "sessionid",
      value: "smoke-session",
      domain: "localhost",
      path: "/",
      httpOnly: false,
      secure: false,
      sameSite: "Lax",
    },
  ]);
}

export async function setCsrfSession(context: BrowserContext) {
  await context.addCookies([
    {
      name: "csrftoken",
      value: "smoke-csrf-token",
      domain: "localhost",
      path: "/",
      httpOnly: false,
      secure: false,
      sameSite: "Lax",
    },
  ]);
}

export async function mockApi(page: Page, pathname: string, options: MockOptions = {}) {
  const method = (options.method ?? "GET").toUpperCase();
  await page.route(apiRouteMatcher(pathname, options.query), async (route: Route) => {
    if (route.request().method().toUpperCase() === "OPTIONS") {
      await route.fulfill({
        status: 204,
        headers: mockResponseHeaders,
      });
      return;
    }

    if (route.request().method().toUpperCase() !== method) {
      await route.fallback();
      return;
    }

    if (options.status === 204) {
      await route.fulfill({ status: 204, headers: mockResponseHeaders });
      return;
    }

    if (options.text !== undefined) {
      await route.fulfill({
        status: options.status ?? 200,
        body: options.text,
        contentType: options.contentType ?? "text/plain",
        headers: mockResponseHeaders,
      });
      return;
    }

    await route.fulfill({
      status: options.status ?? 200,
      contentType: options.contentType ?? "application/json",
      headers: mockResponseHeaders,
      body: JSON.stringify(options.json ?? {}),
    });
  });
}

export async function mockCurrentUser(page: Page, authenticated = true) {
  const state = await mockAuthSession(page, { authenticated });
  return state;
}

export async function mockLogout(page: Page) {
  await mockApi(page, "auth/logout/", {
    method: "POST",
    json: { detail: "Logged out successfully." },
  });
}

export async function mockAuthSession(
  page: Page,
  options: { authenticated?: boolean; user?: MockAuthUser } = {},
) {
  let authenticated = options.authenticated ?? true;
  const mockUser = options.user ?? buildCurrentUser();

  await page.route(apiRouteMatcher("auth/me/"), async (route: Route) => {
    if (route.request().method().toUpperCase() !== "GET") {
      await route.fallback();
      return;
    }

    if (authenticated) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        headers: mockResponseHeaders,
        body: JSON.stringify(mockUser),
      });
      return;
    }

    await route.fulfill({
      status: 401,
      contentType: "application/json",
      headers: mockResponseHeaders,
      body: JSON.stringify({ detail: "Authentication credentials were not provided." }),
    });
  });

  await page.route(apiRouteMatcher("auth/logout/"), async (route: Route) => {
    if (route.request().method().toUpperCase() === "OPTIONS") {
      await route.fulfill({ status: 204, headers: mockResponseHeaders });
      return;
    }

    if (route.request().method().toUpperCase() !== "POST") {
      await route.fallback();
      return;
    }

    authenticated = false;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      headers: {
        ...mockResponseHeaders,
        "Set-Cookie": "sessionid=; Path=/; Max-Age=0; SameSite=Lax",
      },
      body: JSON.stringify({ detail: "Logged out successfully." }),
    });
  });

  return {
    isAuthenticated: () => authenticated,
    setAuthenticated(value: boolean) {
      authenticated = value;
    },
    user: mockUser,
  };
}

export async function navigateToAuthenticatedRoute(page: Page, target: string) {
  const authResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.request().method().toUpperCase() === "GET" &&
      url.pathname === `${API_BASE_PATH}/auth/me/` &&
      response.ok()
    );
  });

  await page.goto(target, { waitUntil: "domcontentloaded" });
  await authResponse;
  await expect(page.getByRole("button", { name: "Log out" })).toBeVisible({ timeout: 15_000 });
}

export async function installUnhandledApiGuard(page: Page, testName = "unknown smoke test") {
  await page.route(
    (requestUrl) => {
      const url = new URL(String(requestUrl));
      return url.pathname === API_BASE_PATH || url.pathname.startsWith(`${API_BASE_PATH}/`);
    },
    async (route) => {
      const url = new URL(route.request().url());
      const detail = {
        testName,
        method: route.request().method(),
        url: route.request().url(),
        pathname: url.pathname,
        pageUrl: page.url(),
      };

      console.error(`Unhandled smoke-test API request: ${JSON.stringify(detail)}`);

      await route.fulfill({
        status: 599,
        contentType: "application/json",
        headers: mockResponseHeaders,
        body: JSON.stringify({
          detail: `Unhandled smoke-test API request`,
          ...detail,
        }),
      });
    },
  );
}

export function buildCurrentUser(overrides: Partial<MockAuthUser> = {}): MockAuthUser {
  return {
    id: "user-1",
    email: "smoke@example.com",
    is_staff: false,
    is_superuser: false,
    profile: {
      display_name: "Smoke Student",
      timezone: "Africa/Maseru",
      preferred_language: "en",
    },
    institutions: [
      {
        id: "institution-1",
        name: "Smoke Study Space",
        slug: "smoke-study-space",
        role: "student",
        institution_type: "individual",
      },
    ],
    ...overrides,
  };
}

export function buildSubject(overrides: Record<string, unknown> = {}) {
  return {
    id: "subject-1",
    code: "BIO101",
    name: "Biology",
    description: "Smoke subject",
    is_active: true,
    created_at: "2026-07-12T00:00:00Z",
    updated_at: "2026-07-12T00:00:00Z",
    ...overrides,
  };
}

export function buildLearningResource(overrides: Record<string, unknown> = {}) {
  return {
    id: "resource-1",
    subject: "subject-1",
    title: "Unit 1 Notes",
    description: "Imported notes",
    resource_type: "notes",
    status: "active",
    source_label: "unit-1.pdf",
    resource_ready_for_learning: true,
    created_at: "2026-07-12T00:00:00Z",
    updated_at: "2026-07-12T00:00:00Z",
    ...overrides,
  };
}

export function buildValidationFinding(overrides: Record<string, unknown> = {}) {
  return {
    id: "finding-1",
    severity: "medium",
    finding_type: "low_confidence",
    message: "Section confidence was lower than expected.",
    metadata: {},
    created_at: "2026-07-12T00:00:00Z",
    ...overrides,
  };
}

export function buildImportJob(overrides: Record<string, unknown> = {}) {
  const base = {
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
    extraction_confidence: 0.96,
    section_confidence: 0.94,
    concept_confidence: 0.93,
    structural_confidence: 0.95,
    metadata: {},
    retry_count: 0,
    failure_details: null,
    resource_ready_for_learning: true,
    created_at: "2026-07-12T00:00:00Z",
    updated_at: "2026-07-12T00:00:00Z",
    validation_findings: [],
  };
  return { ...base, ...overrides };
}

export function buildReviewRequiredImportJob(overrides: Record<string, unknown> = {}) {
  return buildImportJob({
    status: "processing",
    status_detail: "review_required",
    error_message: "Review is required before academic content can be published.",
    resource_ready_for_learning: false,
    processing_status: "ready_for_review",
    processing_stage: "validating",
    processing_progress: 98,
    processing_stage_label: "Ready for academic review",
    processing_message: "Review is required before academic content can be published.",
    review_required: true,
    ready_for_teaching: false,
    processing_failure: null,
    can_retry_processing: false,
    can_cancel_processing: false,
    proposal: {
      id: "proposal-1",
      status: "ready_for_review",
      decision: "pending",
      population_state: "not_ready",
      proposed_section_count: 376,
      proposed_concept_count: 166,
      confidence: 0.728,
      blocking_finding_count: 4,
    },
    ...overrides,
  });
}

export function buildSection(overrides: Record<string, unknown> = {}) {
  return {
    id: "section-1",
    learning_resource: "resource-1",
    title: "Chapter 1",
    description: "",
    sequence_number: 1,
    review_status: "approved",
    quality_status: "acceptable",
    is_active: true,
    created_at: "2026-07-12T00:00:00Z",
    updated_at: "2026-07-12T00:00:00Z",
    ...overrides,
  };
}

export function buildConcept(overrides: Record<string, unknown> = {}) {
  return {
    id: "concept-1",
    content_section: "section-1",
    title: "Cell Structure",
    description: "Understand the cell",
    learning_objective: "Explain organelles",
    sequence_number: 1,
    review_status: "approved",
    quality_status: "acceptable",
    is_active: true,
    created_at: "2026-07-12T00:00:00Z",
    updated_at: "2026-07-12T00:00:00Z",
    ...overrides,
  };
}

export function buildConceptBrowserState(overrides: Record<string, unknown> = {}) {
  return {
    concept_id: "concept-1",
    status: "available",
    can_start_or_resume: true,
    action_label: "Start concept",
    session_id: null,
    session_status: null,
    mastery_decision: null,
    remediation_plan_id: null,
    ...overrides,
  };
}

export function buildRemediationPlan(overrides: Record<string, unknown> = {}) {
  return {
    id: "plan-1",
    status: "pending",
    rationale: "Review this concept again.",
    started_at: null,
    completed_at: null,
    recommendations: [],
    activities: [],
    ...overrides,
  };
}

export function buildMasteryCheckSnapshot(overrides: Record<string, unknown> = {}) {
  return {
    content_concept_id: "concept-1",
    assessment: {
      id: "assessment-1",
      content_concept: "concept-1",
      title: "Cell Check",
      description: "",
      state: "active",
      metadata: {},
      created_at: "2026-07-12T00:00:00Z",
      updated_at: "2026-07-12T00:00:00Z",
    },
    delivery_session: null,
    questions: [],
    current_question_id: null,
    result: null,
    mastery_profile: null,
    evidence: [],
    remediation_plan: null,
    next_available_concept_id: null,
    next_available_concept_title: null,
    can_start: true,
    can_submit: false,
    is_complete: false,
    ...overrides,
  };
}

export async function expectNoNextNotFound(page: Page) {
  await expect(page.locator("body")).not.toContainText("This page could not be found");
}
