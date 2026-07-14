import { API_BASE_URL } from "./config";

const BACKEND_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, "");

export function readCookie(name: string): string | null {
  if (typeof document === "undefined") {
    return null;
  }

  const cookie = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${name}=`));

  return cookie ? decodeURIComponent(cookie.split("=")[1] ?? "") : null;
}

export async function ensureCsrfToken(): Promise<string> {
  const existing = readCookie("csrftoken");
  if (existing) {
    return existing;
  }

  await fetch(`${BACKEND_BASE_URL}/admin/login/`, {
    method: "GET",
    credentials: "include",
  });

  const csrfToken = readCookie("csrftoken");
  if (!csrfToken) {
    throw new Error("Unable to establish a secure session. Please refresh and try again.");
  }

  return csrfToken;
}
