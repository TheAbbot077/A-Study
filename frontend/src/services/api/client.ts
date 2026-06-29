import { API_BASE_URL } from "./config";
import { ApiError } from "./errors";

export async function apiRequest<TResponse>(
  path: string,
  options?: RequestInit,
): Promise<TResponse | undefined> {
  const normalizedPath = path.startsWith("/") ? path.slice(1) : path;
  const url = `${API_BASE_URL.replace(/\/$/, "")}/${normalizedPath}`;

  const response = await fetch(url, {
    ...options,
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
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

    throw new ApiError(
      `Request failed with status ${response.status}`,
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
