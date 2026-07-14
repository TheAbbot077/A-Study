"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LogoutButton, useAuth } from "@/features/auth";

const navLinkClassName =
  "inline-flex min-h-10 items-center rounded-[var(--radius-md)] px-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/35";
const secondaryButtonClassName =
  "inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25";
const primaryButtonClassName =
  "inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105";

export function Header() {
  const pathname = usePathname();
  const { status, user } = useAuth();

  const displayName = user?.profile?.display_name || user?.email || "Student";
  const isDashboardRoute = pathname.startsWith("/dashboard");

  return (
    <header className="border-b border-[var(--color-border)] bg-[var(--color-background)]/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <Link className="inline-flex items-center gap-3" href="/">
              <div className="flex h-11 w-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] text-base font-semibold text-[var(--color-primary-foreground)]">
                A
              </div>
              <div className="min-w-0">
                <h1 className="text-lg font-semibold tracking-tight text-[var(--color-foreground)]">
                  Abbot Study
                </h1>
                <p className="truncate text-sm text-[var(--color-muted-foreground)]">
                  Student shell for focused, ordered learning
                </p>
              </div>
            </Link>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Link className={navLinkClassName} href="/">
              Home
            </Link>

            {status === "loading" ? (
              <span className="px-2 text-sm text-[var(--color-muted-foreground)]">Loading session...</span>
            ) : status === "authenticated" ? (
              <>
                <Link
                  className={`${navLinkClassName} ${isDashboardRoute ? "bg-[var(--color-accent)]/35" : ""}`.trim()}
                  href="/dashboard"
                >
                  Dashboard
                </Link>
                <span className="px-2 text-sm text-[var(--color-muted-foreground)]">
                  Hi, {displayName}
                </span>
                <LogoutButton className={secondaryButtonClassName} />
              </>
            ) : (
              <>
                <Link className={secondaryButtonClassName} href="/login">
                  Log in
                </Link>
                <Link className={primaryButtonClassName} href="/signup">
                  Sign up
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
