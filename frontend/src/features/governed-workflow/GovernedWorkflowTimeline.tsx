import Link from "next/link";
import type { GovernedWorkflow } from "./workflowViewModel";

const statusLabel = {
  not_started: "Not started", available: "Available", in_progress: "In progress",
  completed: "Completed", blocked: "Blocked", failed: "Failed", stale: "Stale",
  superseded: "Superseded", not_applicable: "Not applicable",
} as const;

export function GovernedWorkflowTimeline({ workflow, compact = false }: {
  workflow: GovernedWorkflow;
  compact?: boolean;
}) {
  return (
    <nav aria-label="Governed content workflow" className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-4 shadow-[var(--shadow-card)]">
      <h2 className="text-lg font-semibold">Governed workflow</h2>
      <p className="mt-1 text-sm">Current stage: {workflow.stages.find((item) => item.key === workflow.currentStage)?.label ?? "Unknown"}.</p>
      <ol className={`mt-4 grid gap-3 ${compact ? "sm:grid-cols-2 lg:grid-cols-4" : "md:grid-cols-2 xl:grid-cols-4"}`}>
        {workflow.stages.map((item) => {
          const current = item.key === workflow.currentStage;
          const content = (
            <>
              <span className="font-semibold">{item.label}</span>
              <span className="block text-xs">{statusLabel[item.status]}</span>
              {!compact ? <span className="mt-1 block text-xs">{item.description}</span> : null}
              {item.blockerCount ? <span className="mt-1 block text-xs">{item.blockerCount} blocker{item.blockerCount === 1 ? "" : "s"}</span> : null}
              {item.warningCount ? <span className="mt-1 block text-xs">{item.warningCount} warning{item.warningCount === 1 ? "" : "s"}</span> : null}
            </>
          );
          const className = `block min-h-11 rounded-md border p-3 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] ${current ? "border-[var(--color-primary)]" : "border-[var(--color-border)]"}`;
          return <li aria-current={current ? "step" : undefined} key={item.key}>{item.href ? <Link className={className} href={item.href}>{content}</Link> : <div className={className}>{content}</div>}</li>;
        })}
      </ol>
    </nav>
  );
}
