"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { OperationIdempotency } from "@/lib/idempotency";
import { pollOperation } from "@/lib/polling";
import { normalizeApiProblem, type ApiProblem } from "@/services/api";
import { GovernedWorkflowTimeline, mapGovernedWorkflow } from "@/features/governed-workflow";
import { teachingReadinessApi } from "@/features/teaching-readiness/api";
import { groupReadinessChecks, readinessLabel, type ReadinessCheckFilter } from "@/features/teaching-readiness/readinessViewModel";
import type { TeachingReadinessEvaluation, TeachingReadinessStatusResponse } from "@/features/teaching-readiness/types";
import { retrievalSynchronizationApi } from "./api";
import type { RetrievalSynchronizationReadiness, RetrievalSynchronizationRun } from "./types";

const panel = "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-5 shadow-[var(--shadow-card)]";
const control = "rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)] disabled:cursor-not-allowed disabled:opacity-60";

type OperationsState = {
  retrieval: RetrievalSynchronizationReadiness;
  run: RetrievalSynchronizationRun | null;
  readiness: TeachingReadinessStatusResponse;
  evaluation: TeachingReadinessEvaluation | null;
};

function requireResponse<T>(value: T | undefined, operation: string): T {
  if (value === undefined) throw new Error(`${operation} returned no response body.`);
  return value;
}

async function acquireOperations(populationRunId: string, resourceId: string, signal?: AbortSignal): Promise<OperationsState> {
  const retrieval = requireResponse(
    await retrievalSynchronizationApi.readiness(populationRunId, signal),
    "Retrieval readiness",
  );
  const run = retrieval.existing_synchronization_run_id
    ? requireResponse(
      await retrievalSynchronizationApi.get(retrieval.existing_synchronization_run_id, signal),
      "Synchronization run",
    )
    : null;
  const readiness = requireResponse(
    await teachingReadinessApi.status(resourceId, signal),
    "Teaching-readiness status",
  );
  const evaluation = readiness.latest_evaluation_id
    ? requireResponse(
      await teachingReadinessApi.get(readiness.latest_evaluation_id, signal),
      "Teaching-readiness evaluation",
    )
    : null;
  return { retrieval, run, readiness, evaluation };
}

function Dialog({ title, label, busy, children, cancel, confirm }: {
  title: string; label: string; busy: boolean; children: ReactNode; cancel: () => void; confirm: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { ref.current?.showModal(); }, []);
  return (
    <dialog aria-labelledby="operations-dialog-title" className="m-auto max-w-lg rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] p-6 text-[var(--color-foreground)] backdrop:bg-black/50" onCancel={cancel} ref={ref}>
      <h2 className="text-xl font-semibold" id="operations-dialog-title">{title}</h2>
      <div className="mt-3 space-y-2 text-sm">{children}</div>
      <div className="mt-6 flex justify-end gap-3">
        <button className={control} disabled={busy} onClick={cancel} type="button">Cancel</button>
        <button className={control} disabled={busy} onClick={confirm} type="button">{busy ? "Working…" : label}</button>
      </div>
    </dialog>
  );
}

export function RetrievalTeachingOperations({ populationRunId, resourceId, resourceTitle, projectionId }: {
  populationRunId: string; resourceId: string; resourceTitle: string; projectionId: string;
}) {
  const keys = useRef(new OperationIdempotency());
  const [state, setState] = useState<OperationsState | null>(null);
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const [busy, setBusy] = useState<"refresh" | "synchronize" | "evaluate" | null>(null);
  const [dialog, setDialog] = useState<"synchronize" | "evaluate" | null>(null);
  const [syncReason, setSyncReason] = useState("");
  const [evaluationReason, setEvaluationReason] = useState("");
  const [filter, setFilter] = useState<ReadinessCheckFilter>("all");

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      try {
        const result = await acquireOperations(populationRunId, resourceId, controller.signal);
        if (!controller.signal.aborted) setState(result);
      } catch (error) {
        if (!controller.signal.aborted) setProblem(normalizeApiProblem(error));
      }
    }
    void load();
    return () => controller.abort();
  }, [populationRunId, resourceId]);

  const refresh = async () => {
    if (busy) return;
    setBusy("refresh");
    setProblem(null);
    try { setState(await acquireOperations(populationRunId, resourceId)); }
    catch (error) { setProblem(normalizeApiProblem(error)); }
    finally { setBusy(null); }
  };

  const synchronize = async () => {
    if (!state?.retrieval.ready || busy) return;
    setBusy("synchronize");
    setProblem(null);
    const action = state.run?.status === "failed" ? "synchronization-retry" : "synchronization";
    try {
      let run = requireResponse(await retrievalSynchronizationApi.synchronize(
        populationRunId, state.retrieval.source_fingerprint,
        keys.current.key(populationRunId, action), syncReason.trim(),
      ), "Synchronization command");
      setState((current) => current ? { ...current, run } : current);
      if (run.status === "planned" || run.status === "synchronizing") {
        run = await pollOperation({
          request: async (signal) => requireResponse(
            await retrievalSynchronizationApi.get(run.id, signal),
            "Synchronization run",
          ),
          isSuccess: (value) => value.status === "synchronized",
          isFailure: (value) => value.status === "failed",
          onValue: (value) => setState((current) => current ? { ...current, run: value } : current),
        });
      }
      if (run.status === "synchronized") keys.current.retire(populationRunId, action);
      setDialog(null);
      setState(await acquireOperations(populationRunId, resourceId));
    } catch (error) {
      const nextProblem = normalizeApiProblem(error);
      setProblem(nextProblem);
      if (nextProblem.status === 401 || nextProblem.status === 403) setDialog(null);
    } finally {
      setBusy(null);
    }
  };

  const evaluate = async () => {
    if (!state || busy) return;
    const permitted = state.readiness.latest_evaluation_id ? state.readiness.can_reevaluate : state.readiness.can_evaluate;
    if (!permitted || state.run?.status !== "synchronized") return;
    setBusy("evaluate");
    setProblem(null);
    const action = state.readiness.latest_evaluation_id ? "reevaluation" : "evaluation";
    try {
      const evaluation = requireResponse(await teachingReadinessApi.evaluate(
        resourceId, keys.current.key(resourceId, action),
        state.readiness.status === "stale" ? "" : state.readiness.lineage_fingerprint ?? "",
        evaluationReason.trim(),
      ), "Teaching-readiness evaluation");
      keys.current.retire(resourceId, action);
      const readiness = requireResponse(
        await teachingReadinessApi.status(resourceId),
        "Teaching-readiness status",
      );
      setState((current) => current ? { ...current, evaluation, readiness } : current);
      setDialog(null);
    } catch (error) {
      const nextProblem = normalizeApiProblem(error);
      setProblem(nextProblem);
      if (nextProblem.status === 401 || nextProblem.status === 403) setDialog(null);
    } finally {
      setBusy(null);
    }
  };

  if (!state && !problem) return <section aria-busy="true" className={panel}><h2 className="text-xl font-semibold">4. Retrieval synchronization</h2><p className="mt-2 text-sm">Loading backend operational state…</p></section>;
  if (!state) return <section className={panel}><h2 className="text-xl font-semibold">Operations unavailable</h2><p className="mt-2 text-sm">{problem?.message}</p><button className={`${control} mt-3`} onClick={() => void refresh()} type="button">Retry loading</button></section>;

  const { retrieval, run, readiness, evaluation } = state;
  const synchronized = run?.status === "synchronized";
  const groups = groupReadinessChecks(evaluation?.checks ?? [], filter);
  const workflow = mapGovernedWorkflow({
    resourceExists: true,
    processingStatus: "ready_for_review",
    reviewStatus: "approved",
    projectionStatus: "populated",
    populationStatus: "populated",
    retrievalReady: retrieval.ready,
    retrievalStatus: run?.status,
    retrievalBlockers: retrieval.blockers.length,
    retrievalWarnings: retrieval.warnings.length,
    readinessStatus: readiness.status,
    readinessDecision: readiness.decision,
    readinessBlockers: readiness.blocker_count ?? 0,
    readinessWarnings: readiness.warning_count ?? 0,
  });

  return (
    <>
      <GovernedWorkflowTimeline workflow={workflow} />

      {problem ? <section aria-live="assertive" className="rounded-md border border-[var(--color-danger)] p-4"><h2 className="font-semibold">{problem.status === 0 ? "Outcome not yet confirmed" : problem.code ?? "Operation failed"}</h2><p className="mt-1 text-sm">{problem.message}</p>{problem.status === 0 ? <p className="mt-2 text-sm">The operation key has been preserved. Refresh authoritative status before recovering the same operation.</p> : null}{problem.correlationId ? <p className="mt-1 break-all text-xs">Correlation: {problem.correlationId}</p> : null}</section> : null}
      <section className={panel}>
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-xl font-semibold">4. Retrieval synchronization</h2><p className="mt-1 text-sm">Backend synchronization readiness: {retrieval.ready ? "Ready for synchronization" : "Blocked"}.</p></div><button className={control} disabled={busy !== null} onClick={() => void refresh()} type="button">Refresh operations</button></div>
        <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
          <div><dt>Population run</dt><dd className="break-all">{populationRunId}</dd></div>
          <div><dt>Approved projection</dt><dd className="break-all">{projectionId}</dd></div>
          <div><dt>Resource</dt><dd>{resourceTitle}</dd></div>
          <div><dt>Expected scope</dt><dd>{retrieval.expected_section_count} sections; {retrieval.expected_concept_count} concepts</dd></div>
          <div><dt>Source fingerprint</dt><dd className="break-all">{retrieval.source_fingerprint || "Unavailable"}</dd></div>
          <div><dt>Active generation</dt><dd className="break-all">{retrieval.active_generation_id ?? "None"}</dd></div>
        </dl>
        {retrieval.blockers.length ? <div className="mt-4"><h3 className="font-semibold">Synchronization blockers</h3><ul className="mt-2 list-disc pl-5 text-sm">{retrieval.blockers.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
        {retrieval.warnings.length ? <div className="mt-4"><h3 className="font-semibold">Warnings</h3><ul className="mt-2 list-disc pl-5 text-sm">{retrieval.warnings.map((item) => <li key={item}>{item}</li>)}</ul></div> : null}
        {!run ? <button className={`${control} mt-4`} disabled={!retrieval.ready || busy !== null} onClick={() => setDialog("synchronize")} type="button">Synchronize retrieval</button> : null}
        {run ? <div aria-live={run.status === "planned" || run.status === "synchronizing" ? "polite" : "off"} className="mt-5 rounded border p-4">
          <h3 className="font-semibold">Synchronization run</h3>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
            <div><dt>Status</dt><dd>{run.status}</dd></div><div><dt>Run</dt><dd className="break-all">{run.id}</dd></div>
            <div><dt>Generation</dt><dd className="break-all">{run.retrieval_generation_id ?? "Not created"}</dd></div>
            <div><dt>Chunks</dt><dd>{run.indexed_chunk_count} / {run.planned_chunk_count}</dd></div>
            <div><dt>Keyword indexed</dt><dd>{run.keyword_indexed_count}</dd></div><div><dt>Vector indexed</dt><dd>{run.vector_indexed_count}</dd></div>
            <div><dt>Failed chunks</dt><dd>{run.failed_chunk_count}</dd></div><div><dt>Citation coverage</dt><dd>{Math.round(run.citation_coverage * 100)}%</dd></div>
            <div className="sm:col-span-2"><dt>Manifest fingerprint</dt><dd className="break-all">{run.manifest_fingerprint}</dd></div>
          </dl>
          {run.status === "failed" ? <div className="mt-3 text-sm"><p>{run.failure_code}: {run.failure_message}</p>{run.retry_eligible && retrieval.ready ? <button className={`${control} mt-3`} disabled={busy !== null} onClick={() => setDialog("synchronize")} type="button">Retry synchronization</button> : null}</div> : null}
          {synchronized ? <p className="mt-3 text-sm font-medium">Retrieval is synchronized. This does not grant teaching readiness.</p> : null}
        </div> : null}
      </section>

      <section className={panel}>
        <h2 className="text-xl font-semibold">5. Teaching readiness</h2>
        <p className="mt-2 text-lg font-semibold">{readinessLabel(readiness)}</p>
        <p className="mt-1 text-sm">This is backend-authoritative. Synchronization alone never changes it.</p>
        <dl aria-label="Teaching readiness summary" className="mt-4 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><dt>Evaluation</dt><dd className="break-all">{readiness.latest_evaluation_id ?? "Not evaluated"}</dd></div><div><dt>Decision</dt><dd>{readiness.decision ?? "None"}</dd></div>
          <div><dt>Passed</dt><dd>{readiness.checks_passed ?? 0}</dd></div><div><dt>Failed</dt><dd>{readiness.checks_failed ?? 0}</dd></div>
          <div><dt>Blockers</dt><dd>{readiness.blocker_count ?? 0}</dd></div><div><dt>Warnings</dt><dd>{readiness.warning_count ?? 0}</dd></div>
          <div><dt>Policy</dt><dd>{readiness.policy_version ?? "Not evaluated"}</dd></div><div><dt>Lineage</dt><dd className="break-all">{readiness.lineage_fingerprint ?? "Not evaluated"}</dd></div>
        </dl>
        {readiness.status === "stale" ? <p className="mt-4 border-l-4 border-[var(--color-warning)] pl-3 text-sm">Current readiness is STALE. {evaluation?.invalidation_reason || "Authoritative lineage changed."}</p> : null}
        {readiness.status === "ready_for_teaching" && readiness.decision === "ready" ? <p className="mt-4 font-medium">The teaching pipeline may consume this resource. This does not mean it is learner-published.</p> : null}
        <button className={`${control} mt-4`} disabled={!synchronized || !(readiness.latest_evaluation_id ? readiness.can_reevaluate : readiness.can_evaluate) || busy !== null} onClick={() => setDialog("evaluate")} type="button">{readiness.latest_evaluation_id ? "Reevaluate teaching readiness" : "Evaluate teaching readiness"}</button>
        {evaluation ? <div className="mt-6">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Readiness check filters">{(["all", "blockers", "warnings", "passed"] as const).map((value) => <button aria-pressed={filter === value} className={control} key={value} onClick={() => setFilter(value)} type="button">{value[0].toUpperCase() + value.slice(1)}</button>)}</div>
          <div className="mt-4 space-y-3">{groups.map((group) => <details key={group.category} open={filter !== "all" || group.checks.some((check) => !check.passed)}><summary className="cursor-pointer font-semibold capitalize">{group.category} ({group.checks.length})</summary><ul className="mt-2 space-y-2">{group.checks.map((check) => <li className="rounded border p-3 text-sm" key={check.code}><p className="font-medium">{check.code} — {check.passed ? "Passed" : check.severity.toUpperCase()}</p><p className="mt-1">{check.explanation}</p><p className="mt-1">Expected: {JSON.stringify(check.expected)}; observed: {JSON.stringify(check.observed)}</p>{check.related_ids.length ? <p className="mt-1 break-all">Related: {check.related_ids.join(", ")}</p> : null}</li>)}</ul></details>)}{!groups.length ? <p className="text-sm">No checks match this filter.</p> : null}</div>
        </div> : <p className="mt-4 text-sm">No teaching-readiness evaluation exists yet.</p>}
      </section>

      {dialog === "synchronize" ? <Dialog busy={busy === "synchronize"} cancel={() => setDialog(null)} confirm={() => void synchronize()} label={run?.status === "failed" ? "Retry synchronization" : "Start synchronization"} title="Synchronize grounded retrieval?"><p>This builds grounded retrieval material from official Academic content.</p><p>It does not mark the resource ready for teaching.</p><p className="break-all">Source fingerprint: {retrieval.source_fingerprint}</p><label className="block font-medium" htmlFor="sync-reason">Reason (optional)</label><textarea className={`${control} w-full`} id="sync-reason" onChange={(event) => setSyncReason(event.target.value)} value={syncReason} /></Dialog> : null}
      {dialog === "evaluate" ? <Dialog busy={busy === "evaluate"} cancel={() => setDialog(null)} confirm={() => void evaluate()} label={readiness.latest_evaluation_id ? "Request reevaluation" : "Request evaluation"} title="Evaluate teaching readiness?"><p>The backend verifies source, processing, review, approval, Academic population, retrieval, provenance, and policy.</p><p>You are not selecting the outcome; BLOCKED is a valid evaluation result.</p><p>Active generation: {retrieval.active_generation_id ?? run?.retrieval_generation_id ?? "Unavailable"}</p><label className="block font-medium" htmlFor="evaluation-reason">Reason (optional)</label><textarea className={`${control} w-full`} id="evaluation-reason" onChange={(event) => setEvaluationReason(event.target.value)} value={evaluationReason} /></Dialog> : null}
    </>
  );
}
