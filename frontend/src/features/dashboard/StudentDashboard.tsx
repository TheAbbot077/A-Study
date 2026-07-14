"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { LogoutButton, useAuth } from "@/features/auth";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

export function StudentDashboard() {
  const router = useRouter();
  const { status, user, error } = useAuth();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login?next=/dashboard");
    }
  }, [router, status]);

  if (status === "loading") {
    return <LoadingState message="Preparing your dashboard..." />;
  }

  if (status === "unauthenticated") {
    return (
      <ErrorState
        title="Please log in"
        message="Your session is not available right now. We'll send you back to the login page."
      />
    );
  }

  if (error) {
    return (
      <ErrorState
        title="We couldn't load your dashboard"
        message={error}
      />
    );
  }

  const displayName = user?.profile?.display_name || user?.email?.split("@")[0] || "Student";

  return (
    <section className="space-y-8">
      <div className="grid gap-6 lg:grid-cols-[1.4fr,0.9fr]">
        <section className={`${panelClassName} space-y-5`}>
          <div className="space-y-2">
            <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
              Student dashboard
            </p>
            <h1 className="text-3xl font-semibold text-[var(--color-foreground)] sm:text-4xl">
              Welcome back, {displayName}
            </h1>
            <p className="max-w-2xl text-sm text-[var(--color-muted-foreground)] sm:text-base">
              This shell is ready for the next layer of learning experiences. For now, your account,
              session access, and navigation are all wired up and ready to grow.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">Account</p>
              <p className="mt-2 text-lg font-semibold text-[var(--color-foreground)]">Active</p>
            </article>
            <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">Learning workspace</p>
              <p className="mt-2 text-lg font-semibold text-[var(--color-foreground)]">Ready</p>
            </article>
            <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">Next milestone</p>
              <p className="mt-2 text-lg font-semibold text-[var(--color-foreground)]">PI-6B.2</p>
            </article>
          </div>
        </section>

        <aside className={`${panelClassName} space-y-4`}>
          <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Quick actions</h2>
          <div className="grid gap-3">
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105"
              href="/"
            >
              Return home
            </Link>
            <button
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
              onClick={() => router.refresh()}
              type="button"
            >
              Refresh dashboard
            </button>
            <LogoutButton className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25" />
          </div>
        </aside>
      </div>

      <section className={panelClassName}>
        <EmptyState
          title="No learning activity yet"
          description="Curriculum, sessions, and active study flows will appear here as the student experience grows."
        />
      </section>
    </section>
  );
}
