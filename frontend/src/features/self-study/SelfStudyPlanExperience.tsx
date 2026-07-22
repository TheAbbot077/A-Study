"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth";
import {
  getWorkspacePlanExperience,
  listWorkspacePlanFindings,
  listWorkspacePlanNodes,
  startWorkspaceLearning,
  type SelfStudyPlanExperience as PlanExperience,
  type SelfStudyPlanFinding,
  type SelfStudyPlanNodeSummary,
} from "@/services/self-study";
import { coverageMeaning, planNodeTone, planReadinessLabel } from "./experienceViewModel";
import { workspaceStatusLabel } from "./workspaceViewModel";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

export function SelfStudyPlanExperience({ workspaceId }: { workspaceId: string }) {
  const router = useRouter();
  const { status } = useAuth();
  const [plan, setPlan] = useState<PlanExperience | null>(null);
  const [nodes, setNodes] = useState<SelfStudyPlanNodeSummary[]>([]);
  const [findings, setFindings] = useState<SelfStudyPlanFinding[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=/dashboard/self-study/${workspaceId}/plan`);
    }
  }, [router, status, workspaceId]);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    const controller = new AbortController();
    async function synchronize() {
      try {
        const [nextPlan, nextNodes, nextFindings] = await Promise.all([
          getWorkspacePlanExperience(workspaceId, controller.signal),
          listWorkspacePlanNodes(workspaceId, controller.signal),
          listWorkspacePlanFindings(workspaceId, controller.signal),
        ]);
        if (!active) return;
        setPlan(nextPlan);
        setNodes(nextNodes);
        setFindings(nextFindings);
        setError(null);
      } catch (loadError) {
        if (!active || controller.signal.aborted) return;
        setError(loadError instanceof Error ? loadError.message : "Unable to load the study plan.");
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

  async function handleStartLearning() {
    setSubmitting(true);
    setError(null);
    try {
      const launch = await startWorkspaceLearning(workspaceId);
      router.push(launch.target_route);
    } catch (launchError) {
      setError(launchError instanceof Error ? launchError.message : "Learning cannot start from this plan yet.");
    } finally {
      setSubmitting(false);
    }
  }

  if (status === "loading" || (status === "authenticated" && loading)) {
    return <LoadingState message="Loading your governed study plan..." />;
  }

  if (status === "unauthenticated") {
    return <ErrorState title="Please log in" message="Log in to review this study plan." />;
  }

  if (error && !plan) {
    return <ErrorState title="Study plan unavailable" message={error} />;
  }

  if (!plan) {
    return <EmptyState title="Study plan unavailable" description="Abbot could not find a governed study plan for this workspace." />;
  }

  return (
    <section className="space-y-6">
      <Link className="text-sm font-medium text-[var(--color-primary)] hover:underline" href={`/dashboard/self-study/${workspaceId}`}>
        Back to workspace
      </Link>

      {error ? <ErrorState title="Study plan issue" message={error} /> : null}

      <header className={`${panelClassName} space-y-4`}>
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">Study plan</p>
        <h1 className="text-3xl font-semibold text-[var(--color-foreground)]">{planReadinessLabel(plan)}</h1>
        <p className="max-w-3xl text-sm text-[var(--color-muted-foreground)]">
          This learner-facing study plan reads the governed bridge plan. It follows the published curriculum graph and does not award mastery.
        </p>
        <dl className="grid gap-3 text-sm sm:grid-cols-4">
          <Metric label="Required" value={plan.required_node_count} />
          <Metric label="Optional" value={plan.optional_node_count} />
          <Metric label="Ready" value={plan.ready_node_count} />
          <Metric label="Blocked" value={plan.blocked_node_count} />
        </dl>
      </header>

      {plan.blocker_codes.length ? (
        <section className={`${panelClassName} space-y-3 border-l-4 border-l-[var(--color-danger)]`}>
          <h2 className="text-xl font-semibold text-[var(--color-foreground)]">What needs attention</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Some parts need more material or governed preparation before Abbot can teach them well.
          </p>
          <ul className="grid gap-2 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-2">
            {plan.blocker_codes.map((code) => (
              <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2" key={code}>
                {code}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className={`${panelClassName} flex flex-wrap gap-3`}>
        <button
          className="inline-flex min-h-11 items-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)] disabled:opacity-60"
          disabled={!plan.can_start_learning || submitting}
          onClick={() => void handleStartLearning()}
          type="button"
        >
          {submitting ? "Starting..." : "Start learning with Abbot"}
        </button>
        <Link className="inline-flex min-h-11 items-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium" href={`/dashboard/self-study/${workspaceId}/diagnostic/summary`}>
          Review diagnostic summary
        </Link>
      </section>

      <section className={`${panelClassName} space-y-4`} aria-label="Ordered study plan nodes">
        <h2 className="text-2xl font-semibold text-[var(--color-foreground)]">Your learning path</h2>
        {nodes.length ? (
          <ol className="space-y-3">
            {nodes.map((node) => (
              <PlanNodeCard key={node.plan_node_id} node={node} />
            ))}
          </ol>
        ) : (
          <EmptyState title="No plan nodes yet" description="The governed bridge plan has not produced learner-visible plan nodes for this workspace." />
        )}
      </section>

      {findings.length ? (
        <section className={`${panelClassName} space-y-3`} aria-label="Study plan findings">
          <h2 className="text-xl font-semibold text-[var(--color-foreground)]">Governed findings</h2>
          <ul className="space-y-2 text-sm text-[var(--color-muted-foreground)]">
            {findings.map((finding) => (
              <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3" key={finding.id}>
                <span className="font-medium text-[var(--color-foreground)]">{finding.code}</span> - {finding.severity}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3">
      <dt className="text-[var(--color-muted-foreground)]">{label}</dt>
      <dd className="mt-1 text-xl font-semibold text-[var(--color-foreground)]">{value}</dd>
    </div>
  );
}

function PlanNodeCard({ node }: { node: SelfStudyPlanNodeSummary }) {
  const tone = planNodeTone(node);
  return (
    <li
      className={`rounded-[var(--radius-md)] border p-4 ${
        tone === "blocked" ? "border-[var(--color-danger)]" : tone === "ready" ? "border-[var(--color-primary)]" : "border-[var(--color-border)]"
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            {node.sequence_index}. {workspaceStatusLabel(node.node_type)}
          </p>
          <h3 className="mt-1 text-lg font-semibold text-[var(--color-foreground)]">{node.title}</h3>
        </div>
        <span className="rounded-full border border-[var(--color-border)] px-3 py-1 text-xs text-[var(--color-muted-foreground)]">
          {node.dependency_summary.required ? "Required" : "Optional"}
        </span>
      </div>
      <p className="mt-3 text-sm text-[var(--color-muted-foreground)]">{coverageMeaning(node.coverage_state)}</p>
      <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
        Material status: {workspaceStatusLabel(node.material_status)} - Dependencies: {node.dependency_summary.dependency_count}
      </p>
      {node.blocker_codes.length ? (
        <p className="mt-2 text-sm text-[var(--color-danger)]">{node.blocker_codes.join(", ")}</p>
      ) : null}
    </li>
  );
}
