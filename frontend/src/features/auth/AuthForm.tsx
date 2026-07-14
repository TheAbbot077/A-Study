"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useMemo, useState } from "react";
import { ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "./AuthProvider";

type AuthMode = "login" | "signup";

type AuthFormProps = {
  mode: AuthMode;
};

const cardClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)] sm:p-8";
const inputClassName =
  "w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm text-[var(--color-foreground)] outline-none transition focus:border-[var(--color-primary)] focus:ring-2 focus:ring-[color:rgba(197,155,59,0.18)]";
const primaryButtonClassName =
  "inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-70";

export function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = useMemo(() => searchParams.get("next") || "/dashboard", [searchParams]);
  const { login, signup, status, error, clearError } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const isSignup = mode === "signup";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const email = String(formData.get("email") || "").trim();
    const password = String(formData.get("password") || "");
    const displayName = String(formData.get("display_name") || "").trim();

    if (!email || !password) {
      setFormError("Email and password are required.");
      return;
    }

    setPending(true);
    setFormError(null);
    clearError();

    try {
      if (isSignup) {
        await signup({ email, password, display_name: displayName });
      } else {
        await login({ email, password });
      }

      router.replace(nextPath);
      router.refresh();
    } catch (submitError) {
      setFormError(submitError instanceof Error ? submitError.message : "Unable to complete your request.");
    } finally {
      setPending(false);
    }
  }

  if (status === "loading" && pending === false) {
    return <LoadingState message="Checking your session..." />;
  }

  return (
    <section className="mx-auto w-full max-w-md space-y-6">
      <div className="space-y-2 text-center">
        <h1 className="text-3xl font-semibold text-[var(--color-foreground)]">
          {isSignup ? "Create your study account" : "Welcome back"}
        </h1>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          {isSignup
            ? "Start your dashboard, save your progress, and pick up where you left off."
            : "Log in to continue your learning dashboard."}
        </p>
      </div>

      {(formError || error) && (
        <ErrorState
          title={isSignup ? "Unable to create account" : "Unable to log in"}
          message={formError || error || undefined}
        />
      )}

      <form className={cardClassName} onSubmit={(event) => void handleSubmit(event)}>
        <div className="space-y-5">
          {isSignup ? (
            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Display name</span>
              <input
                className={inputClassName}
                name="display_name"
                type="text"
                placeholder="How should Abbot Study greet you?"
              />
            </label>
          ) : null}

          <label className="block space-y-2">
            <span className="text-sm font-medium text-[var(--color-foreground)]">Email</span>
            <input
              className={inputClassName}
              autoComplete="email"
              name="email"
              type="email"
              placeholder="you@example.com"
              required
            />
          </label>

          <label className="block space-y-2">
            <span className="text-sm font-medium text-[var(--color-foreground)]">Password</span>
            <input
              className={inputClassName}
              autoComplete={isSignup ? "new-password" : "current-password"}
              name="password"
              type="password"
              placeholder={isSignup ? "Choose a secure password" : "Enter your password"}
              required
            />
          </label>

          <button className={`${primaryButtonClassName} w-full`} disabled={pending} type="submit">
            {pending ? (isSignup ? "Creating account..." : "Logging in...") : isSignup ? "Sign up" : "Log in"}
          </button>
        </div>
      </form>

      <p className="text-center text-sm text-[var(--color-muted-foreground)]">
        {isSignup ? "Already have an account?" : "New here?"}{" "}
        <Link
          className="font-semibold text-[var(--color-primary)] underline-offset-4 hover:underline"
          href={isSignup ? "/login" : "/signup"}
        >
          {isSignup ? "Log in" : "Create an account"}
        </Link>
      </p>
    </section>
  );
}
