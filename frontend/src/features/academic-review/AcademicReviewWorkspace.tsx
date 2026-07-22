"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth/AuthProvider";
import { GovernedWorkflowTimeline, mapGovernedWorkflow } from "@/features/governed-workflow";
import { normalizeApiProblem, type ApiProblem } from "@/services/api";
import {
  decideItem,
  editItem,
  getEvidence,
  getReview,
  listFindings,
  listOutline,
  resolveFinding,
  startReview,
  submitReview,
  type ReviewEvidence,
  type ReviewFinding,
  type ReviewItem,
  type ReviewSession,
} from "@/services/academic-review";
import {
  completionSummary,
  orderedItems,
  reviewCounts,
  reviewLifecycle,
  severityLabel,
  unresolvedFindings,
} from "./reviewViewModel";

const panel = "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-5 shadow-[var(--shadow-card)]";
const control = "rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]";
const identifierPattern = /^[A-Za-z0-9-]{1,128}$/;

type Workspace = {
  session: ReviewSession;
  items: ReviewItem[];
  findings: ReviewFinding[];
};

async function acquireReviewWorkspace(
  proposalId: string,
  signal?: AbortSignal,
  knownSessionId?: string,
): Promise<Workspace> {
  const session = knownSessionId
    ? await getReview(knownSessionId, signal)
    : await startReview(proposalId, signal);
  const [outline, findings] = await Promise.all([
    listOutline(session.id, signal),
    listFindings(session.id, signal),
  ]);
  return { session, items: outline.results, findings };
}

function problemTitle(problem: ApiProblem) {
  if (problem.status === 403) return "Review workspace unavailable";
  if (problem.status === 404) return "Review workspace not found";
  if (problem.status === 409) return "Review state changed";
  if (problem.status === 0) return "Network connection failed";
  return "Unable to load academic review";
}

function ItemEditor({
  item,
  editable,
  busy,
  onDirtyChange,
  onSaveDecision,
  onSaveEdit,
}: {
  item: ReviewItem;
  editable: boolean;
  busy: boolean;
  onDirtyChange: (dirty: boolean) => void;
  onSaveDecision: (decision: "accepted" | "rejected", reason: string) => Promise<void>;
  onSaveEdit: (payload: { title: string; ordering?: number; reason: string }) => Promise<void>;
}) {
  const initialTitle = item.edit?.title || item.title;
  const initialOrdering = item.edit?.ordering?.toString() ?? "";
  const [title, setTitle] = useState(initialTitle);
  const [ordering, setOrdering] = useState(initialOrdering);
  const [reason, setReason] = useState(item.reason);
  const dirty = title !== initialTitle || ordering !== initialOrdering || reason !== item.reason;

  useEffect(() => {
    onDirtyChange(dirty);
    return () => onDirtyChange(false);
  }, [dirty, onDirtyChange]);

  const saveEdit = async () => {
    const parsed = ordering ? Number(ordering) : undefined;
    if (parsed !== undefined && (!Number.isInteger(parsed) || parsed < 1)) return;
    await onSaveEdit({ title, ordering: parsed, reason });
  };

  return (
    <section aria-labelledby="item-editor-title" className="space-y-4">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted-foreground)]">
          {item.item_type} · {item.decision}
        </p>
        <h2 className="mt-1 text-xl font-semibold" id="item-editor-title">{initialTitle}</h2>
        <p className="mt-1 text-sm">Proposal confidence: {(item.confidence * 100).toFixed(0)}%</p>
      </div>
      {!editable ? <p className="rounded-md border p-3 text-sm">This review is read-only.</p> : (
        <>
          <div>
            <label className="text-sm font-medium" htmlFor={`title-${item.id}`}>Reviewed title</label>
            <input className={`${control} mt-1 w-full`} disabled={busy} id={`title-${item.id}`} maxLength={255} onChange={(event) => setTitle(event.target.value)} value={title} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="text-sm font-medium" htmlFor={`ordering-${item.id}`}>Reviewed order</label>
              <input className={`${control} mt-1 w-full`} disabled={busy} id={`ordering-${item.id}`} min="1" onChange={(event) => setOrdering(event.target.value)} type="number" value={ordering} />
            </div>
            <div>
              <label className="text-sm font-medium" htmlFor={`reason-${item.id}`}>Review note</label>
              <input className={`${control} mt-1 w-full`} disabled={busy} id={`reason-${item.id}`} onChange={(event) => setReason(event.target.value)} value={reason} />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button className={control} disabled={busy || title !== initialTitle || ordering !== initialOrdering} onClick={() => void onSaveDecision("accepted", reason)} type="button">Include item</button>
            <button className={control} disabled={busy || title !== initialTitle || ordering !== initialOrdering} onClick={() => void onSaveDecision("rejected", reason)} type="button">Exclude item</button>
            <button className={control} disabled={busy || !dirty || !title.trim()} onClick={() => void saveEdit()} type="button">
              {busy ? "Saving…" : "Save edits"}
            </button>
            <span aria-live="polite" className="self-center text-sm">{dirty ? "Unsaved changes" : "All changes saved"}</span>
          </div>
        </>
      )}
    </section>
  );
}

function CompletionDialog({
  session,
  findings,
  busy,
  onCancel,
  onConfirm,
}: {
  session: ReviewSession;
  findings: ReviewFinding[];
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const summary = completionSummary(session, findings);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog aria-labelledby="complete-review-title" className="m-auto max-w-lg rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] p-6 text-[var(--color-foreground)] backdrop:bg-black/50" onCancel={onCancel} ref={ref}>
      <h2 className="text-xl font-semibold" id="complete-review-title">Complete human review?</h2>
      <p className="mt-2 text-sm">Completion ends editing and advances this proposal to a later approval step. It does not approve or populate content.</p>
      <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
        <dt>Included sections</dt><dd>{summary.sections.included}</dd>
        <dt>Excluded sections</dt><dd>{summary.sections.excluded}</dd>
        <dt>Included concepts</dt><dd>{summary.concepts.included}</dd>
        <dt>Excluded concepts</dt><dd>{summary.concepts.excluded}</dd>
        <dt>Unresolved blockers</dt><dd>{summary.blockerCount}</dd>
        <dt>Unresolved warnings</dt><dd>{summary.warningCount}</dd>
        <dt>Review version</dt><dd>{session.version}</dd>
      </dl>
      <div className="mt-6 flex justify-end gap-3">
        <button className={control} disabled={busy} onClick={onCancel} type="button">Keep reviewing</button>
        <button className={control} disabled={busy} onClick={onConfirm} type="button">{busy ? "Completing…" : "Complete review"}</button>
      </div>
    </dialog>
  );
}

export function AcademicReviewWorkspace({ proposalId }: { proposalId: string }) {
  const { status: authStatus } = useAuth();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [evidence, setEvidence] = useState<ReviewEvidence[]>([]);
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const [notice, setNotice] = useState("");
  const [findingFilter, setFindingFilter] = useState<"unresolved" | "all" | ReviewFinding["severity"]>("unresolved");
  const [resolutionNotes, setResolutionNotes] = useState<Record<number, string>>({});
  const [showCompletion, setShowCompletion] = useState(false);

  const routeProblem = useMemo<ApiProblem | null>(() => {
    if (authStatus === "loading") return null;
    if (authStatus !== "authenticated") {
      return {
        status: 403,
        code: "REVIEW_AUTHENTICATION_REQUIRED",
        message: "Sign in with reviewer access to open this workspace.",
      };
    }
    if (!identifierPattern.test(proposalId)) {
      return {
        status: 400,
        code: "INVALID_REVIEW_ROUTE",
        message: "The proposal identifier is malformed.",
      };
    }
    return null;
  }, [authStatus, proposalId]);

  useEffect(() => {
    if (authStatus !== "authenticated" || !identifierPattern.test(proposalId)) return;
    const controller = new AbortController();
    async function synchronize() {
      try {
        const result = await acquireReviewWorkspace(proposalId, controller.signal);
        if (controller.signal.aborted) return;
        setWorkspace(result);
        setSelectedId((current) => result.items.some((item) => item.id === current) ? current : result.items[0]?.id ?? null);
      } catch (error) {
        if (!controller.signal.aborted) setProblem(normalizeApiProblem(error));
      }
    }
    void synchronize();
    return () => controller.abort();
  }, [authStatus, proposalId]);

  const selected = workspace?.items.find((item) => item.id === selectedId) ?? null;
  useEffect(() => {
    if (!workspace || !selected) {
      return;
    }
    const controller = new AbortController();
    void getEvidence(workspace.session.id, selected.id, controller.signal)
      .then(setEvidence)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setProblem(normalizeApiProblem(error));
      });
    return () => controller.abort();
  }, [selected, workspace]);

  const refresh = async (discardDirty = false) => {
    if (!workspace || busy) return;
    if (dirty && !discardDirty && !window.confirm("Discard unsaved changes and refresh from the server?")) return;
    setBusy(true);
    setProblem(null);
    try {
      const result = await acquireReviewWorkspace(proposalId, undefined, workspace.session.id);
      setWorkspace(result);
      setSelectedId((current) => result.items.some((item) => item.id === current) ? current : result.items[0]?.id ?? null);
      setDirty(false);
      setNotice("Workspace refreshed from the server.");
    } catch (error) {
      setProblem(normalizeApiProblem(error));
    } finally {
      setBusy(false);
    }
  };

  const runCommand = async (command: () => Promise<unknown>, success: string) => {
    if (!workspace || busy) return;
    setBusy(true);
    setProblem(null);
    try {
      await command();
      const result = await acquireReviewWorkspace(proposalId, undefined, workspace.session.id);
      setWorkspace(result);
      setSelectedId((current) => result.items.some((item) => item.id === current) ? current : result.items[0]?.id ?? null);
      setDirty(false);
      setNotice(success);
    } catch (error) {
      setProblem(normalizeApiProblem(error));
    } finally {
      setBusy(false);
    }
  };

  const choose = (item: ReviewItem) => {
    if (dirty && !window.confirm("Discard unsaved edits and inspect another proposal item?")) return;
    setSelectedId(item.id);
    setDirty(false);
  };

  const filteredFindings = useMemo(() => {
    if (!workspace) return [];
    if (findingFilter === "all") return workspace.findings;
    if (findingFilter === "unresolved") return unresolvedFindings(workspace.findings);
    return workspace.findings.filter((finding) => finding.severity === findingFilter);
  }, [findingFilter, workspace]);

  const loading = authStatus === "loading" || (!routeProblem && !workspace && !problem);
  if (loading) return <LoadingState message="Opening academic proposal review…" />;
  if (routeProblem) return <ErrorState title={problemTitle(routeProblem)} message={routeProblem.message} />;
  if (problem && !workspace) return <ErrorState title={problemTitle(problem)} message={problem.message} />;
  if (!workspace) return <ErrorState title="Review workspace unavailable" message="No authoritative review session was returned." />;

  const { session, items, findings } = workspace;
  const lifecycle = reviewLifecycle(session.status);
  const counts = reviewCounts(session);
  const completion = completionSummary(session, findings);
  const workflow = mapGovernedWorkflow({
    resourceExists: true,
    processingStatus: "ready_for_review",
    reviewStatus: session.status,
    reviewBlockers: session.summary.blocking_findings,
    hrefs: {
      processing: `/dashboard/resources/${session.resource.id}`,
      review: `/dashboard/academic-review/${session.proposal}`,
      approval: `/dashboard/academic-review/${session.proposal}/governance?session=${session.id}`,
    },
  });

  return (
    <main className="space-y-6">
      <header className={panel}>
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-[var(--color-primary)]">Academic proposal review</p>
            <h1 className="mt-2 text-3xl font-semibold">{session.resource.title}</h1>
            <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">Source: {session.resource.source_label || "Not supplied"}</p>
          </div>
          <div className="flex gap-2">
            <Link className={control} href={`/dashboard/resources/${session.resource.id}`}>Back to resource</Link>
            <button className={control} disabled={busy} onClick={() => void refresh()} type="button">Refresh</button>
          </div>
        </div>
        <div className="mt-5 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <p><strong>Status:</strong> {lifecycle.label}</p>
          <p><strong>Review version:</strong> {session.version}</p>
          <p><strong>Proposal version:</strong> {session.proposal_version}</p>
          <p><strong>Confidence:</strong> {(session.confidence * 100).toFixed(1)}%</p>
          <p><strong>Sections:</strong> {counts.sections.included} included, {counts.sections.excluded} excluded, {counts.sections.pending} pending</p>
          <p><strong>Concepts:</strong> {counts.concepts.included} included, {counts.concepts.excluded} excluded, {counts.concepts.pending} pending</p>
          <p><strong>Unresolved findings:</strong> {session.summary.outstanding_findings}</p>
          <p><strong>Updated:</strong> {new Date(session.updated_at).toLocaleString()}</p>
        </div>
        <p className="mt-4 rounded-md border p-3 text-sm">{lifecycle.explanation}</p>
      </header>

      <GovernedWorkflowTimeline workflow={workflow} />

      {problem ? (
        <section aria-live="assertive" className="rounded-md border border-[var(--color-danger)] p-4">
          <h2 className="font-semibold">{problemTitle(problem)}</h2>
          <p className="mt-1 text-sm">{problem.message}</p>
          {problem.fieldErrors ? <ul className="mt-2 list-disc pl-5 text-sm">{Object.entries(problem.fieldErrors).flatMap(([field, messages]) => messages.map((message) => <li key={`${field}-${message}`}>{field}: {message}</li>))}</ul> : null}
          {problem.status === 409 ? <p className="mt-1 text-sm">Your local input has been preserved. Refresh deliberately before sending another command.</p> : null}
        </section>
      ) : null}
      <p aria-live="polite" className="sr-only">{notice}</p>

      {items.length === 0 ? <EmptyState title="Empty proposal" description="The backend returned no proposed sections or concepts for this review." /> : (
        <div className="grid gap-6 lg:grid-cols-[minmax(16rem,0.8fr)_minmax(0,1.4fr)]">
          <nav aria-label="Proposal items" className={panel}>
            <h2 className="text-lg font-semibold">Proposal outline</h2>
            <ul className="mt-4 max-h-[42rem] space-y-2 overflow-y-auto">
              {orderedItems(items).map(({ item, backendOrder }) => (
                <li key={item.id}>
                  <button aria-current={item.id === selectedId ? "true" : undefined} className={`${control} w-full text-left ${item.id === selectedId ? "border-[var(--color-primary)]" : ""}`} onClick={() => choose(item)} type="button">
                    <span className="block text-xs uppercase">{backendOrder}. {item.item_type} · {item.decision}</span>
                    <span className="block font-medium">{item.edit?.title || item.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          </nav>

          <div className="space-y-6">
            <section className={panel}>
              {selected ? (
                <ItemEditor
                  busy={busy}
                  editable={lifecycle.editable}
                  item={selected}
                  key={selected.id}
                  onDirtyChange={setDirty}
                  onSaveDecision={(decision, reason) => runCommand(() => decideItem(session.id, selected.id, decision, reason), `${selected.item_type} decision saved.`)}
                  onSaveEdit={(payload) => runCommand(() => editItem(session.id, selected.id, payload), `${selected.item_type} edits saved.`)}
                />
              ) : <p>Select a proposal item.</p>}
            </section>

            <section aria-labelledby="evidence-title" className={panel}>
              <h2 className="text-xl font-semibold" id="evidence-title">Source evidence</h2>
              {!selected ? <p className="mt-2 text-sm">Select an item to inspect its evidence.</p> : evidence.length === 0 ? <p className="mt-2 text-sm">No source evidence was returned for this item.</p> : (
                <div className="mt-4 space-y-3">
                  {evidence.map((row) => (
                    <details className="rounded-md border p-3" key={row.id}>
                      <summary className="cursor-pointer text-sm font-medium">Pages {row.page_start ?? "unknown"}–{row.page_end ?? row.page_start ?? "unknown"} · {row.evidence_strength} · {(row.confidence * 100).toFixed(0)}%</summary>
                      <p className="mt-2 text-sm"><strong>Hierarchy:</strong> {row.hierarchy || "Not supplied"}</p>
                      <p className="mt-2 whitespace-pre-wrap break-words text-sm">{row.supporting_text || "No excerpt supplied."}</p>
                      <p className="mt-2 text-xs text-[var(--color-muted-foreground)]">Evidence reference {row.id}</p>
                    </details>
                  ))}
                </div>
              )}
            </section>
          </div>
        </div>
      )}

      <section aria-labelledby="findings-title" className={panel}>
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div><h2 className="text-xl font-semibold" id="findings-title">Findings</h2><p className="mt-1 text-sm">Only the backend can mark a finding resolved.</p></div>
          <label className="text-sm">Finding filter
            <select className={`${control} ml-2`} onChange={(event) => setFindingFilter(event.target.value as typeof findingFilter)} value={findingFilter}>
              <option value="unresolved">Unresolved only</option><option value="all">All findings</option><option value="blocking">Blockers</option><option value="warning">Warnings</option><option value="info">Information</option>
            </select>
          </label>
        </div>
        <ul className="mt-4 space-y-3">
          {filteredFindings.map((finding) => (
            <li className="rounded-md border p-4" key={finding.id}>
              <p className="font-semibold">{severityLabel(finding.severity)} · {finding.resolved || finding.passed ? "Resolved" : "Unresolved"}</p>
              <p className="mt-1 text-sm">{finding.message}</p>
              {!finding.resolved && !finding.passed && lifecycle.editable ? (
                <div className="mt-3 grid gap-2 sm:grid-cols-[1fr_auto]">
                  <label className="text-sm" htmlFor={`finding-note-${finding.id}`}>Resolution note
                    <input className={`${control} mt-1 w-full`} id={`finding-note-${finding.id}`} onChange={(event) => setResolutionNotes((current) => ({ ...current, [finding.id]: event.target.value }))} value={resolutionNotes[finding.id] ?? ""} />
                  </label>
                  <button className={`${control} self-end`} disabled={busy || !selected || !(resolutionNotes[finding.id] ?? "").trim()} onClick={() => {
                    if (!selected) return;
                    const resolution_type = selected.decision === "rejected" ? "rejection" : selected.decision === "moved" ? "move" : "edit";
                    void runCommand(() => resolveFinding(session.id, { validation_id: finding.id, resolution_type, item_decision_id: selected.id, note: resolutionNotes[finding.id] }), "Finding resolution saved by the backend.");
                  }} type="button">Resolve with selected item</button>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      </section>

      <section className={panel}>
        <h2 className="text-xl font-semibold">Complete review</h2>
        <p className="mt-2 text-sm">Backend readiness: {session.summary.ready ? "completion allowed" : "completion blocked"}. The frontend does not recalculate this decision.</p>
        {!completion.allowed ? <p className="mt-2 text-sm">Resolve all backend-reported pending items and blocking findings before completion.</p> : null}
        <button aria-describedby="completion-explanation" className={`${control} mt-4`} disabled={busy || !completion.allowed || dirty} onClick={() => setShowCompletion(true)} type="button">Complete human review</button>
        <p className="mt-2 text-xs" id="completion-explanation">Completion advances to ready for approval; it does not approve, reject, populate, synchronize, or evaluate teaching readiness.</p>
        {session.status === "ready_for_approval" || session.status === "approved" || session.status === "approved_with_edits" || session.status === "rejected" ? (
          <Link className={`${control} mt-4 inline-block`} href={`/dashboard/academic-review/${proposalId}/governance?session=${session.id}`}>Open approval and population governance</Link>
        ) : null}
      </section>

      {showCompletion ? (
        <CompletionDialog
          busy={busy}
          findings={findings}
          onCancel={() => setShowCompletion(false)}
          onConfirm={() => {
            void runCommand(async () => {
              const next = await submitReview(session.id);
              if (next) setWorkspace((current) => current ? { ...current, session: next } : current);
              setShowCompletion(false);
            }, "Human review completed. This workspace is now read-only.");
          }}
          session={session}
        />
      ) : null}
    </main>
  );
}
