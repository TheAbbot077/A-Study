"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth";
import { createSelfStudyWorkspace, listSelfStudyWorkspaces, type SelfStudyWorkspace } from "@/services/self-study";
import { workspaceStatusLabel } from "./workspaceViewModel";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

export function SelfStudyDashboard() {
  const router = useRouter();
  const { status, user } = useAuth();
  const [workspaces, setWorkspaces] = useState<SelfStudyWorkspace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login?next=/dashboard/self-study");
    }
  }, [router, status]);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    const controller = new AbortController();
    async function synchronize() {
      try {
        const nextWorkspaces = await listSelfStudyWorkspaces(controller.signal);
        if (!active) return;
        setWorkspaces(nextWorkspaces);
        setError(null);
      } catch (loadError) {
        if (!active || controller.signal.aborted) return;
        setError(loadError instanceof Error ? loadError.message : "Unable to load self-study workspaces.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void synchronize();
    return () => {
      active = false;
      controller.abort();
    };
  }, [status]);

  const tenantOptions = user?.institutions ?? [];
  const defaultTenant = tenantOptions[0]?.id ?? "";
  const activeCount = useMemo(() => workspaces.filter((workspace) => workspace.status !== "ARCHIVED").length, [workspaces]);

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);
    const displayName = String(formData.get("display_name") || "").trim();
    const description = String(formData.get("description") || "").trim();
    const tenantId = String(formData.get("tenant_id") || defaultTenant).trim();
    if (!displayName) {
      setError("Workspace name is required.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const workspace = await createSelfStudyWorkspace({
        display_name: displayName,
        description,
        ...(tenantId ? { tenant_id: tenantId } : {}),
        idempotency_key: `workspace:${tenantId}:${displayName.toLowerCase()}`,
      });
      router.push(`/dashboard/self-study/${workspace.id}`);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unable to create a self-study workspace.");
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "loading" || (status === "authenticated" && loading)) {
    return <LoadingState message="Opening your self-study dashboard..." />;
  }

  if (status === "unauthenticated") {
    return <ErrorState title="Please log in" message="Log in to create or resume a self-study workspace." />;
  }

  return (
    <section className="space-y-8">
      <div className="grid gap-6 lg:grid-cols-[1.15fr,0.85fr]">
        <section className={`${panelClassName} space-y-4`}>
          <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
            Self-study
          </p>
          <h1 className="text-3xl font-semibold text-[var(--color-foreground)] sm:text-4xl">
            Create a study workspace
          </h1>
          <p className="max-w-2xl text-sm text-[var(--color-muted-foreground)] sm:text-base">
            A workspace is your learner-owned doorway into Abbot. It can hold your goals and materials,
            but it does not create a syllabus or override governed curriculum authority.
          </p>
          <dl className="grid gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Workspaces</dt>
              <dd className="mt-1 text-[var(--color-muted-foreground)]">{workspaces.length}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Active</dt>
              <dd className="mt-1 text-[var(--color-muted-foreground)]">{activeCount}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Next step</dt>
              <dd className="mt-1 text-[var(--color-muted-foreground)]">Open a workspace to see the backend-authoritative next action.</dd>
            </div>
          </dl>
          {error ? <ErrorState title="Self-study workspace issue" message={error} /> : null}
        </section>

        <aside className={panelClassName}>
          <form className="space-y-4" onSubmit={(event) => void handleCreate(event)}>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-[var(--color-foreground)]">New workspace</h2>
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Learners can call this a subject. It is a display name until a governed curriculum is resolved.
              </p>
            </div>
            {tenantOptions.length > 1 ? (
              <label className="block space-y-2">
                <span className="text-sm font-medium text-[var(--color-foreground)]">Learning account</span>
                <select className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" name="tenant_id" defaultValue={defaultTenant}>
                  {tenantOptions.map((tenant) => (
                    <option key={tenant.id} value={tenant.id}>{tenant.name}</option>
                  ))}
                </select>
              </label>
            ) : null}
            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">What do you want to study?</span>
              <input className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" name="display_name" placeholder="Organic chemistry" required />
            </label>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Notes for yourself</span>
              <textarea className="min-h-24 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" name="description" placeholder="I want to prepare for my midterm using my lecture notes." />
            </label>
            <button className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-60" disabled={submitting} type="submit">
              {submitting ? "Creating..." : "Create workspace"}
            </button>
          </form>
        </aside>
      </div>

      <section className={`${panelClassName} space-y-4`}>
        <h2 className="text-xl font-semibold text-[var(--color-foreground)]">Your self-study workspaces</h2>
        {workspaces.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {workspaces.map((workspace) => (
              <Link className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 transition hover:border-[var(--color-primary)]" href={`/dashboard/self-study/${workspace.id}`} key={workspace.id}>
                <p className="text-lg font-semibold text-[var(--color-foreground)]">{workspace.display_name}</p>
                <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">{workspace.description || "No description yet."}</p>
                <p className="mt-4 text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">{workspaceStatusLabel(workspace.status)}</p>
              </Link>
            ))}
          </div>
        ) : (
          <EmptyState title="No self-study workspaces yet" description="Create a learner-owned workspace to answer intent questions, add materials, and launch a diagnostic when the governed backend allows it." />
        )}
      </section>
    </section>
  );
}
