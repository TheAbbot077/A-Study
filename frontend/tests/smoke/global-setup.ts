import { request, type FullConfig } from "@playwright/test";
import { warmFrontendRoutes } from "./helpers/api";

const PUBLIC_WARMUP_ROUTES = [
  "/",
  "/login",
  "/signup",
] as const;

const AUTHENTICATED_WARMUP_ROUTES = [
  "/dashboard",
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
