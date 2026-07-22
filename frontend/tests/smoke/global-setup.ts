import { request, type FullConfig } from "@playwright/test";
import { warmFrontendRoutes } from "./helpers/api";

const PUBLIC_WARMUP_ROUTES = [
  "/",
  "/login",
  "/signup",
] as const;

const AUTHENTICATED_WARMUP_ROUTES = [
  "/dashboard",
  "/dashboard/subjects/warmup-subject",
  "/dashboard/resources/warmup-resource",
  "/dashboard/concepts/warmup-concept",
  "/dashboard/concepts/warmup-concept/assessment?session=warmup-session",
  "/dashboard/academic-review/warmup-proposal",
  "/dashboard/academic-review/warmup-proposal/governance?session=warmup-session",
] as const;

export default async function globalSetup(config: FullConfig) {
  const baseURL = config.projects[0]?.use.baseURL;
  if (typeof baseURL !== "string") {
    throw new Error("Playwright smoke route warm-up requires a string baseURL.");
  }

  const publicRequest = await request.newContext({ baseURL });
  const authenticatedRequest = await request.newContext({
    baseURL,
    extraHTTPHeaders: {
      Cookie: "sessionid=smoke-session; csrftoken=smoke-csrf-token",
    },
  });

  try {
    await warmFrontendRoutes(publicRequest, PUBLIC_WARMUP_ROUTES);
    await warmFrontendRoutes(authenticatedRequest, AUTHENTICATED_WARMUP_ROUTES);
  } finally {
    await Promise.all([
      publicRequest.dispose(),
      authenticatedRequest.dispose(),
    ]);
  }
}
