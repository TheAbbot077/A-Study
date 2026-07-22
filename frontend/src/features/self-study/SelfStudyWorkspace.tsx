"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth";
import {
  attachWorkspaceMaterial,
  getSelfStudyWorkspace,
  getWorkspaceDiagnosticStatus,
  getWorkspaceOnboarding,
  listWorkspaceMaterials,
  startWorkspaceDiagnostic,
  type PublicDiagnostic,
  type SelfStudyOnboardingSummary,
  type SelfStudyWorkspace as Workspace,
  type WorkspaceMaterial,
} from "@/services/self-study";
import { hasBlockingOnboarding, materialStatusSummary, nextActionTone, workspaceStatusLabel } from "./workspaceViewModel";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

type WorkspaceSection = "overview" | "intent" | "materials" | "diagnostic" | "plan" | "learn";

export function SelfStudyWorkspace({ workspaceId, section = "overview" }: { workspaceId: string; section?: WorkspaceSection }) {
  const router = useRouter();
  const { status } = useAuth();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [summary, setSummary] = useState<SelfStudyOnboardingSummary | null>(null);
  const [materials, setMaterials] = useState<WorkspaceMaterial[]>([]);
  const [diagnostic, setDiagnostic] = useState<PublicDiagnostic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [materialSubmitting, setMaterialSubmitting] = useState(false);
  const [diagnosticSubmitting, setDiagnosticSubmitting] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=/dashboard/self-study/${workspaceId}`);
    }
  }, [router, status, workspaceId]);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    const controller = new AbortController();
    async function synchronize() {
      try {
        const [nextWorkspace, nextSummary, nextMaterials, nextDiagnostic] = await Promise.all([
          getSelfStudyWorkspace(workspaceId, controller.signal),
          getWorkspaceOnboarding(workspaceId, controller.signal),
          listWorkspaceMaterials(workspaceId, controller.signal),
          getWorkspaceDiagnosticStatus(workspaceId, controller.signal),
        ]);
        if (!active) return;
        setWorkspace(nextWorkspace);
        setSummary(nextSummary);
        setMaterials(nextMaterials);
        setDiagnostic(nextDiagnostic);
        setError(null);
      } catch (loadError) {
        if (!active || controller.signal.aborted) return;
        setError(loadError instanceof Error ? loadError.message : "Unable to load this workspace.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void synchronize();
    return () => {
      active = false;
      controller.abort();
    };
  }, [status, workspaceId]);

  const nextAction = summary?.next_action;
  const tone = nextAction ? nextActionTone(nextAction) : "neutral";
  const materialSummary = useMemo(() => materialStatusSummary(materials), [materials]);

  async function handleAttachMaterial(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const resourceId = String(formData.get("resource_id") || "").trim();
    const jobId = String(formData.get("content_processing_job_id") || "").trim();
    if (!resourceId) {
      setError("Paste an existing learning resource ID to attach it to this workspace.");
      return;
    }
    setMaterialSubmitting(true);
    setError(null);
    try {
      await attachWorkspaceMaterial(workspaceId, {
        resource_id: resourceId,
        ...(jobId ? { content_processing_job_id: jobId } : {}),
        idempotency_key: `material:${resourceId}`,
      });
      const [nextSummary, nextMaterials] = await Promise.all([
        getWorkspaceOnboarding(workspaceId),
        listWorkspaceMaterials(workspaceId),
      ]);
      setSummary(nextSummary);
      setMaterials(nextMaterials);
      form.reset();
    } catch (attachError) {
      setError(attachError instanceof Error ? attachError.message : "Unable to attach that material.");
    } finally {
      setMaterialSubmitting(false);
    }
  }

  async function handleStartDiagnostic() {
    setDiagnosticSubmitting(true);
    setError(null);
    try {
      const nextDiagnostic = await startWorkspaceDiagnostic(workspaceId, true);
      const nextSummary = await getWorkspaceOnboarding(workspaceId);
      setDiagnostic(nextDiagnostic);
      setSummary(nextSummary);
    } catch (diagnosticError) {
      setError(diagnosticError instanceof Error ? diagnosticError.message : "Unable to start the diagnostic.");
    } finally {
      setDiagnosticSubmitting(false);
    }
  }

  if (status === "loading" || (status === "authenticated" && loading)) {
    return <LoadingState message="Opening your self-study workspace..." />;
  }

  if (status === "unauthenticated") {
    return <ErrorState title="Please log in" message="Log in to resume this self-study workspace." />;
  }

  if (!workspace) {
    return <ErrorState title="Workspace unavailable" message={error ?? "We could not load this workspace."} />;
  }

  return (
    <section className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link className="text-sm font-medium text-[var(--color-primary)] hover:underline" href="/dashboard/self-study">
          Back to self-study
        </Link>
        <nav aria-label="Self-study workspace sections" className="flex flex-wrap gap-2 text-sm">
          {(["overview", "intent", "materials", "diagnostic", "plan", "learn"] as WorkspaceSection[]).map((item) => (
            <Link
              aria-current={section === item ? "page" : undefined}
              className={`rounded-full border px-3 py-1 ${section === item ? "border-[var(--color-primary)] text-[var(--color-primary)]" : "border-[var(--color-border)] text-[var(--color-muted-foreground)]"}`}
              href={item === "overview" ? `/dashboard/self-study/${workspace.id}` : `/dashboard/self-study/${workspace.id}/${item}`}
              key={item}
            >
              {workspaceStatusLabel(item)}
            </Link>
          ))}
        </nav>
      </div>

      <header className={`${panelClassName} space-y-3`}>
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
          Study workspace
        </p>
        <h1 className="text-3xl font-semibold text-[var(--color-foreground)] sm:text-4xl">{workspace.display_name}</h1>
        <p className="max-w-3xl text-sm text-[var(--color-muted-foreground)] sm:text-base">
          {workspace.description || "This learner-owned workspace can collect intent, materials, and launch states without becoming curriculum authority."}
        </p>
        <p className="text-sm text-[var(--color-muted-foreground)]">Status: {workspaceStatusLabel(workspace.status)}</p>
      </header>

      {error ? <ErrorState title="Workspace issue" message={error} /> : null}

      {nextAction ? (
        <section className={`${panelClassName} space-y-4 border-l-4 ${tone === "blocked" ? "border-l-[var(--color-danger)]" : tone === "ready" ? "border-l-[var(--color-primary)]" : "border-l-[var(--color-border)]"}`}>
          <div className="space-y-2">
            <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-muted-foreground)]">Next action</p>
            <h2 className="text-2xl font-semibold text-[var(--color-foreground)]">{nextAction.title}</h2>
            <p className="text-sm text-[var(--color-muted-foreground)]">{nextAction.explanation}</p>
          </div>
          {nextAction.blocker_codes.length ? (
            <ul className="grid gap-2 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-2">
              {nextAction.blocker_codes.map((code) => <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2" key={code}>{code}</li>)}
            </ul>
          ) : null}
          <Link className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105" href={nextAction.target_route}>
            {nextAction.primary_cta_label}
          </Link>
        </section>
      ) : null}

      <div className="grid gap-6 lg:grid-cols-[1fr,1fr]">
        <section className={`${panelClassName} space-y-4`}>
          <h2 className="text-xl font-semibold text-[var(--color-foreground)]">Intent</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            {workspace.intent_id ? "An intent is attached. Continue through the governed intent flow to keep policy acknowledgements current." : "Answer what you want to learn before Abbot can safely plan anything."}
          </p>
          <Link className="inline-flex min-h-10 items-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium" href={`/dashboard/self-study/${workspace.id}/intent`}>
            {workspace.intent_id ? "Resume intent" : "Answer intent questions"}
          </Link>
        </section>

        <section className={`${panelClassName} space-y-4`}>
          <h2 className="text-xl font-semibold text-[var(--color-foreground)]">Materials</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">{materialSummary}</p>
          <form className="space-y-3" onSubmit={(event) => void handleAttachMaterial(event)}>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Existing learning resource ID</span>
              <input className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" name="resource_id" placeholder="Paste resource UUID" />
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Processing job ID (optional)</span>
              <input className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" name="content_processing_job_id" placeholder="Paste job UUID if known" />
            </label>
            <button className="inline-flex min-h-10 items-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium disabled:opacity-60" disabled={materialSubmitting} type="submit">
              {materialSubmitting ? "Attaching..." : "Attach material"}
            </button>
          </form>
          {materials.length ? (
            <ul className="space-y-2 text-sm">
              {materials.map((material) => (
                <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3" key={material.id}>
                  <p className="font-medium text-[var(--color-foreground)]">{material.resource_title || material.resource_id}</p>
                  <p className="mt-1 text-[var(--color-muted-foreground)]">{workspaceStatusLabel(material.status)}</p>
                  {material.blocker_codes.length ? <p className="mt-1 text-[var(--color-danger)]">{material.blocker_codes.join(", ")}</p> : null}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No materials attached" description="Upload through the existing resource pipeline, then attach the resulting learning resource to this workspace." />
          )}
        </section>
      </div>

      <section className={`${panelClassName} space-y-4`}>
        <h2 className="text-xl font-semibold text-[var(--color-foreground)]">Diagnostic and learning launch</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          Diagnostic status: {diagnostic?.status ? workspaceStatusLabel(diagnostic.status) : "Not created"}. Diagnostic placement remains private and is never displayed here as mastery.
        </p>
        <div className="flex flex-wrap gap-3">
          <button className="inline-flex min-h-10 items-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)] disabled:opacity-60" disabled={diagnosticSubmitting || hasBlockingOnboarding(summary)} onClick={() => void handleStartDiagnostic()} type="button">
            {diagnostic?.status === "IN_PROGRESS" ? "Resume diagnostic" : "Start diagnostic"}
          </button>
          <Link className="inline-flex min-h-10 items-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium" href={`/dashboard/self-study/${workspace.id}/learn`}>
            View learning status
          </Link>
        </div>
      </section>
    </section>
  );
}
