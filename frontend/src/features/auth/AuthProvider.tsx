"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  getCurrentUser,
  login as loginRequest,
  logout as logoutRequest,
  signup as signupRequest,
  type AuthUser,
} from "@/services/auth";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  user: AuthUser | null;
  status: AuthStatus;
  error: string | null;
  refreshUser: () => Promise<AuthUser | null>;
  login: (payload: { email: string; password: string }) => Promise<AuthUser>;
  signup: (payload: { email: string; password: string; display_name?: string }) => Promise<AuthUser>;
  logout: () => Promise<void>;
  clearError: () => void;
};

const AUTH_USER_CACHE_KEY = "abbot-study.auth.user";

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function readCachedUser(): AuthUser | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.sessionStorage.getItem(AUTH_USER_CACHE_KEY);
    return raw ? (JSON.parse(raw) as AuthUser) : null;
  } catch {
    return null;
  }
}

function writeCachedUser(user: AuthUser | null) {
  if (typeof window === "undefined") return;
  if (user) {
    window.sessionStorage.setItem(AUTH_USER_CACHE_KEY, JSON.stringify(user));
  } else {
    window.sessionStorage.removeItem(AUTH_USER_CACHE_KEY);
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    try {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setStatus(currentUser ? "authenticated" : "unauthenticated");
      writeCachedUser(currentUser);
      setError(null);
      return currentUser;
    } catch (refreshError) {
      setUser(null);
      setStatus("unauthenticated");
      writeCachedUser(null);
      setError(refreshError instanceof Error ? refreshError.message : "Unable to load your session.");
      return null;
    }
  }, []);

  useEffect(() => {
    let active = true;
    async function restoreSession() {
      const cachedUser = readCachedUser();
      if (cachedUser) {
        setUser(cachedUser);
        setStatus("authenticated");
      }

      try {
        const currentUser = await getCurrentUser();
        if (!active) return;
        setUser(currentUser);
        setStatus(currentUser ? "authenticated" : "unauthenticated");
        writeCachedUser(currentUser);
        setError(null);
      } catch (restoreError) {
        if (!active) return;
        setUser(null);
        setStatus("unauthenticated");
        writeCachedUser(null);
        setError(restoreError instanceof Error ? restoreError.message : "Unable to load your session.");
      }
    }
    void restoreSession();
    return () => { active = false; };
  }, []);

  const login = useCallback(async (payload: { email: string; password: string }) => {
    const authenticatedUser = await loginRequest(payload);
    setUser(authenticatedUser);
    setStatus("authenticated");
    writeCachedUser(authenticatedUser);
    setError(null);
    return authenticatedUser;
  }, []);

  const signup = useCallback(
    async (payload: { email: string; password: string; display_name?: string }) => {
      const authenticatedUser = await signupRequest(payload);
      setUser(authenticatedUser);
      setStatus("authenticated");
      writeCachedUser(authenticatedUser);
      setError(null);
      return authenticatedUser;
    },
    [],
  );

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
    setStatus("unauthenticated");
    writeCachedUser(null);
    setError(null);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      error,
      refreshUser,
      login,
      signup,
      logout,
      clearError,
    }),
    [clearError, error, login, logout, refreshUser, signup, status, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }

  return context;
}
