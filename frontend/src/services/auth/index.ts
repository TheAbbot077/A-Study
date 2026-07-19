import { API_BASE_URL } from "../api/config";
import { ensureCsrfToken } from "../api/csrf";

export type AuthUser = {
  id: string;
  email: string;
  is_staff: boolean;
  is_superuser: boolean;
  profile?: {
    display_name?: string;
    timezone?: string;
    preferred_language?: string;
  } | null;
  institutions?: Array<{
    id: string;
    name: string;
    slug: string;
    role: string;
    institution_type: string;
  }>;
};

type LoginPayload = {
  email: string;
  password: string;
};

type SignupPayload = LoginPayload & {
  display_name?: string;
};

const AUTH_ENDPOINTS = {
  login: "auth/login/",
  register: "auth/register/",
  logout: "auth/logout/",
  currentUser: "auth/me/",
} as const;

type AuthEndpointKey = "login" | "register" | "logout";

async function parseError(response: Response): Promise<string> {
  try {
    const details = (await response.json()) as Record<string, unknown>;
    if (typeof details.detail === "string") {
      return details.detail;
    }

    const firstError = Object.values(details)[0];
    if (Array.isArray(firstError) && typeof firstError[0] === "string") {
      return firstError[0];
    }
  } catch {
    // Fall through to generic message.
  }

  return `Request failed with status ${response.status}.`;
}

async function authPost<TResponse>(
  endpoint: AuthEndpointKey,
  payload?: Record<string, unknown>,
): Promise<TResponse> {
  const csrfToken = await ensureCsrfToken();
  const response = await fetch(`${API_BASE_URL.replace(/\/$/, "")}/${AUTH_ENDPOINTS[endpoint]}`, {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as TResponse;
}

export async function getCurrentUser(): Promise<AuthUser | null> {
  const response = await fetch(`${API_BASE_URL.replace(/\/$/, "")}/${AUTH_ENDPOINTS.currentUser}`, {
    method: "GET",
    cache: "no-store",
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  });

  if (response.status === 401 || response.status === 403) {
    return null;
  }

  if (!response.ok) {
    throw new Error(await parseError(response));
  }

  return (await response.json()) as AuthUser;
}

export async function login(payload: LoginPayload): Promise<AuthUser> {
  return authPost<AuthUser>("login", payload);
}

export async function signup(payload: SignupPayload): Promise<AuthUser> {
  return authPost<AuthUser>("register", payload);
}

export async function logout(): Promise<void> {
  await authPost<{ detail: string }>("logout");
}
