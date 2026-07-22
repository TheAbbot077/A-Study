import { API_BASE_URL } from "./config";
import { ensureCsrfToken } from "./csrf";
import { ApiError } from "./errors";

export async function apiRequest<TResponse>(
  path: string,
  options?: RequestInit,
): Promise<TResponse | undefined> {
  const normalizedPath = path.startsWith("/") ? path.slice(1) : path;
  const url = `${API_BASE_URL.replace(/\/$/, "")}/${normalizedPath}`;

  const method = options?.method?.toUpperCase() ?? "GET";
  const csrfToken =
    method === "GET" || method === "HEAD" || method === "OPTIONS"
      ? null
      : await ensureCsrfToken();
  const isFormData = typeof FormData !== "undefined" && options?.body instanceof FormData;
  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      Accept: "application/json",
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
      ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
      ...(options?.headers ?? {}),
    },
  });

  if (!response.ok) {
    let details: unknown;
    try {
      details = await response.json();
    } catch {
      details = undefined;
    }

    const safeMessage =
      details && typeof details === "object" && "detail" in details && typeof details.detail === "string"
        ? details.detail
        : `Request failed with status ${response.status}`;
    throw new ApiError(
      safeMessage,
      response.status,
      response.headers.get("x-error-code") ?? undefined,
      details,
    );
  }

  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined;
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.includes("application/json")) {
    return undefined;
  }

  return (await response.json()) as TResponse;
}
