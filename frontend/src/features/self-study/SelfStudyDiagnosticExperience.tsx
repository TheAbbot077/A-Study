"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth";
import {
  getWorkspaceDiagnosticExperience,
  getWorkspacePlacementSummary,
  resumeWorkspaceDiagnostic,
  startWorkspaceDiagnostic,
  type LearnerPlacementSummary,
  type SelfStudyDiagnosticExperience as DiagnosticExperience,
} from "@/services/self-study";
import { diagnosticExperienceTitle, diagnosticProgressLabel } from "./experienceViewModel";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

export function SelfStudyDiagnosticExperience({ mode = "diagnostic", workspaceId }: { mode?: "diagnostic" | "summary"; workspaceId: string }) {
  const router = useRouter();
  const { status } = useAuth();
  const [experience, setExperience] = useState<DiagnosticExperience | null>(null);
  const [summary, setSummary] = useState<LearnerPlacementSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=/dashboard/self-study/${workspaceId}/diagnostic`);
    }
  }, [router, status, workspaceId]);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    const controller = new AbortController();
    async function synchronize() {
      try {
        const nextExperience = await getWorkspaceDiagnosticExperience(workspaceId, controller.signal);
        const nextSummary =
          mode === "summary" || nextExperience.status === "COMPLETE"
            ? await getWorkspacePlacementSummary(workspaceId, controller.signal).catch(() => null)
            : null;
        if (!active) return;
        setExperience(nextExperience);
        setSummary(nextSummary);
        setError(null);
      } catch (loadError) {
        if (!active || controller.signal.aborted) return;
        setError(loadError instanceof Error ? loadError.message : "Unable to load the diagnostic experience.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void synchronize();
    return () => {
      active = false;
      controller.abort();
    };
  }, [mode, status, workspaceId]);

  async function refreshExperience() {
    const nextExperience = await getWorkspaceDiagnosticExperience(workspaceId);
    setExperience(nextExperience);
    if (nextExperience.status === "COMPLETE") {
      setSummary(await getWorkspacePlacementSummary(workspaceId).catch(() => null));
    }
  }

  async function handleStartOrResume() {
    if (!experience) return;
    setSubmitting(true);
    setError(null);
    try {
      if (experience.can_resume) {
        await resumeWorkspaceDiagnostic(workspaceId);
      } else {
        await startWorkspaceDiagnostic(workspaceId, true);
      }
      await refreshExperience();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to update the diagnostic.");
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "loading" || (status === "authenticated" && loading)) {
    return <LoadingState message="Preparing your diagnostic experience..." />;
  }

  if (status === "unauthenticated") {
    return <ErrorState title="Please log in" message="Log in to continue your diagnostic." />;
  }

  if (error && !experience) {
    return <ErrorState title="Diagnostic unavailable" message={error} />;
  }

  if (!experience) {
    return <EmptyState title="Diagnostic unavailable" description="Abbot could not find a diagnostic state for this workspace." />;
  }

  return (
    <section className="space-y-6">
      <Link className="text-sm font-medium text-[var(--color-primary)] hover:underline" href={`/dashboard/self-study/${workspaceId}`}>
        Back to workspace
      </Link>

      {error ? <ErrorState title="Diagnostic issue" message={error} /> : null}

      <header className={`${panelClassName} space-y-4`}>
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">Diagnostic</p>
        <h1 className="text-3xl font-semibold text-[var(--color-foreground)]">{diagnosticExperienceTitle(experience)}</h1>
        <p className="max-w-3xl text-sm text-[var(--color-muted-foreground)]">
          Your diagnostic helps Abbot find a good starting point. It is not a grade, does not award mastery, and does not change the curriculum graph.
        </p>
        <p className="text-sm text-[var(--color-muted-foreground)]">{diagnosticProgressLabel(experience)}</p>
      </header>

      <section className={`${panelClassName} space-y-4`}>
        <h2 className="text-xl font-semibold text-[var(--color-foreground)]">Privacy and limits</h2>
        <ul className="grid gap-2 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-2">
          <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3">Raw answers and item-level scores are not shown here.</li>
          <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3">Placement is a starting-point signal, not mastery or credit.</li>
          <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3">Your study plan follows the published curriculum graph.</li>
          <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3">Uploaded documents never become curriculum authority.</li>
        </ul>
      </section>

      {experience.blocker_codes.length ? (
        <section className={`${panelClassName} space-y-3 border-l-4 border-l-[var(--color-danger)]`}>
          <h2 className="text-xl font-semibold text-[var(--color-foreground)]">What is blocking this?</h2>
          <ul className="grid gap-2 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-2">
            {experience.blocker_codes.map((code) => (
              <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2" key={code}>
                {code}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className={`${panelClassName} flex flex-wrap gap-3`}>
        {(experience.can_start || experience.can_resume) && experience.status !== "COMPLETE" ? (
          <button
            className="inline-flex min-h-11 items-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)] disabled:opacity-60"
            disabled={submitting}
            onClick={() => void handleStartOrResume()}
            type="button"
          >
            {submitting ? "Opening diagnostic..." : experience.can_resume ? "Resume diagnostic" : "Start diagnostic"}
          </button>
        ) : null}
        {experience.status === "COMPLETE" ? (
          <Link className="inline-flex min-h-11 items-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)]" href={`/dashboard/self-study/${workspaceId}/diagnostic/summary`}>
            View placement summary
          </Link>
        ) : null}
        <Link className="inline-flex min-h-11 items-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium" href={`/dashboard/self-study/${workspaceId}/plan`}>
          View study plan
        </Link>
      </section>

      {summary ? (
        <section className={`${panelClassName} space-y-4`} aria-label="Learner-safe placement summary">
          <h2 className="text-2xl font-semibold text-[var(--color-foreground)]">Learner-safe placement summary</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Placement band: {summary.placement_band}. Confidence: {summary.confidence_label}. This is not mastery.
          </p>
          <div className="grid gap-4 md:grid-cols-3">
            <DomainList title="Ready to begin near" domains={summary.ready_domains} />
            <DomainList title="Needs review" domains={summary.needs_review_domains} />
            <DomainList title="Not yet ready" domains={summary.not_yet_ready_domains} />
          </div>
          {summary.privacy_warnings.map((warning) => (
            <p className="text-sm text-[var(--color-muted-foreground)]" key={warning}>
              {warning}
            </p>
          ))}
        </section>
      ) : mode === "summary" ? (
        <EmptyState title="Summary is not ready" description="Abbot will show a learner-safe placement summary after the governed diagnostic result exists." />
      ) : null}
    </section>
  );
}

function DomainList({ domains, title }: { domains: string[]; title: string }) {
  return (
    <section className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
      <h3 className="font-semibold text-[var(--color-foreground)]">{title}</h3>
      {domains.length ? (
        <ul className="mt-3 space-y-2 text-sm text-[var(--color-muted-foreground)]">
          {domains.map((domain) => (
            <li key={domain}>{domain}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-sm text-[var(--color-muted-foreground)]">No learner-visible domains in this group yet.</p>
      )}
    </section>
  );
}
