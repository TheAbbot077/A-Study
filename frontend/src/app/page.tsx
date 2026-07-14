"use client";

import Link from "next/link";
import { LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";
const secondaryButtonClassName =
  "inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25";
const primaryButtonClassName =
  "inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105";

export default function Home() {
  const { status } = useAuth();

  return (
    <section className="space-y-10">
      <div className="grid gap-8 lg:grid-cols-[1.35fr,0.95fr] lg:items-start">
        <section className="space-y-6">
          <div className="space-y-4">
            <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
              Frontend app shell
            </p>
            <h2 className="max-w-3xl text-4xl font-semibold tracking-tight text-[var(--color-foreground)] sm:text-5xl">
              A calm place to begin studying.
            </h2>
            <p className="max-w-2xl text-base text-[var(--color-muted-foreground)] sm:text-lg">
              Abbot Study is now ready for real student navigation: account entry, protected dashboard
              access, and a clean shell for the learning platform to grow into.
            </p>
          </div>

          {status === "loading" ? (
            <div className="max-w-md">
              <LoadingState message="Checking if you already have a session..." />
            </div>
          ) : (
            <div className="flex flex-col gap-3 sm:flex-row">
              {status === "authenticated" ? (
                <Link className={primaryButtonClassName} href="/dashboard">
                  Continue to dashboard
                </Link>
              ) : (
                <>
                  <Link className={primaryButtonClassName} href="/signup">
                    Sign up
                  </Link>
                  <Link className={secondaryButtonClassName} href="/login">
                    Log in
                  </Link>
                </>
              )}
            </div>
          )}
        </section>

        <section className={`${panelClassName} space-y-5`}>
          <h3 className="text-lg font-semibold text-[var(--color-foreground)]">What this shell includes</h3>
          <div className="grid gap-4">
            <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <h4 className="font-semibold text-[var(--color-foreground)]">Account entry</h4>
              <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
                Sign up and login flows wired to the platform auth API.
              </p>
            </article>
            <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <h4 className="font-semibold text-[var(--color-foreground)]">Protected dashboard</h4>
              <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
                A first student route with session-aware navigation and graceful empty states.
              </p>
            </article>
            <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <h4 className="font-semibold text-[var(--color-foreground)]">Reusable shell</h4>
              <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
                Shared layout, feedback states, and mobile-friendly top navigation.
              </p>
            </article>
          </div>
        </section>
      </div>
    </section>
  );
}
