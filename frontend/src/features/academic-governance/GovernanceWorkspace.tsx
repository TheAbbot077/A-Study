"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth/AuthProvider";
import { academicPopulationApi } from "@/features/academic-population/api";
import type { AcademicPopulationRun } from "@/features/academic-population/types";
import { GovernedWorkflowTimeline, mapGovernedWorkflow } from "@/features/governed-workflow";
import { RetrievalTeachingOperations } from "@/features/retrieval/RetrievalTeachingOperations";
import { OperationIdempotency } from "@/lib/idempotency";
import { normalizeApiProblem, type ApiProblem } from "@/services/api";
import {
  approveReview,
  evaluateApprovalReadiness,
  getApprovedProjection,
  getPopulationReadiness,
  getReview,
  populateApprovedProjection,
  rejectReview,
  startReview,
  type ApprovedProjection,
  type ApprovalReadinessSnapshot,
  type PopulationReadiness,
  type PopulationResult,
  type ReviewSession,
} from "@/services/academic-review";
import {
  approvalAllowed,
  governanceStage,
  orderedProjection,
  populationAllowed,
} from "./governanceViewModel";

const panel = "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-5 shadow-[var(--shadow-card)]";
const control = "rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]";
const identifierPattern = /^[A-Za-z0-9-]{1,128}$/;

type GovernanceState = {
  session: ReviewSession;
  readiness: ApprovalReadinessSnapshot | null;
  projection: ApprovedProjection | null;
  populationReadiness: PopulationReadiness | null;
  populationRun: AcademicPopulationRun | null;
};

async function acquireGovernanceWorkspace({
  proposalId,
  routeSessionId,
  knownSessionId,
  signal,
}: {
  proposalId: string;
  routeSessionId?: string;
  knownSessionId?: string;
  signal?: AbortSignal;
}): Promise<GovernanceState> {
  const authoritativeSessionId = knownSessionId ?? routeSessionId;
  const session = authoritativeSessionId
    ? await getReview(authoritativeSessionId, signal)
    : await startReview(proposalId, signal);
  let readiness: ApprovalReadinessSnapshot | null = null;
  let projection: ApprovedProjection | null = null;
  let populationReadiness: PopulationReadiness | null = null;
  let populationRun: AcademicPopulationRun | null = null;

  if (session.status === "ready_for_approval") {
    readiness = await evaluateApprovalReadiness(session.id, session.version, signal) ?? null;
  }
  if ((session.status === "approved" || session.status === "approved_with_edits") && session.approved_projection_id) {
    projection = await getApprovedProjection(session.approved_projection_id, signal) ?? null;
    if (projection) {
      const fetchedReadiness = await getPopulationReadiness(projection.id, signal) ?? null;
      if (fetchedReadiness) {
        populationReadiness = fetchedReadiness;
        const existingRunId = fetchedReadiness.existing_population_run_id;
        if (existingRunId) {
          populationRun = await academicPopulationApi.get(existingRunId, signal) ?? null;
        }
      }
    }
  }
  return { session, readiness, projection, populationReadiness, populationRun };
}

function GovernanceDialog({
  title,
  children,
  confirmLabel,
  busy,
  confirmDisabled,
  onCancel,
  onConfirm,
}: {
  title: string;
  children: ReactNode;
  confirmLabel: string;
  busy: boolean;
  confirmDisabled?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog aria-labelledby="governance-dialog-title" className="m-auto max-w-lg rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] p-6 text-[var(--color-foreground)] backdrop:bg-black/50" onCancel={onCancel} ref={ref}>
      <h2 className="text-xl font-semibold" id="governance-dialog-title">{title}</h2>
      <div className="mt-3 text-sm">{children}</div>
      <div className="mt-6 flex justify-end gap-3">
        <button className={control} disabled={busy} onClick={onCancel} type="button">Cancel</button>
        <button className={control} disabled={busy || confirmDisabled} onClick={onConfirm} type="button">{busy ? "Working…" : confirmLabel}</button>
      </div>
    </dialog>
  );
}

export function GovernanceWorkspace({ proposalId, sessionId }: { proposalId: string; sessionId?: string }) {
  const { status: authStatus } = useAuth();
  const keys = useRef(new OperationIdempotency());
  const [state, setState] = useState<GovernanceState | null>(null);
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const [busy, setBusy] = useState<"approval" | "rejection" | "population" | "refresh" | null>(null);
  const [dialog, setDialog] = useState<"approve" | "reject" | "populate" | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");
  const [populationResult, setPopulationResult] = useState<PopulationResult | null>(null);
  const [selectedSectionId, setSelectedSectionId] = useState<number | null>(null);

  const routeProblem = useMemo<ApiProblem | null>(() => {
    if (authStatus === "loading") return null;
    if (authStatus !== "authenticated") return { status: 403, code: "GOVERNANCE_AUTHENTICATION_REQUIRED", message: "Sign in with authorized governance access." };
    if (!identifierPattern.test(proposalId) || (sessionId !== undefined && !identifierPattern.test(sessionId))) {
      return { status: 400, code: "INVALID_GOVERNANCE_ROUTE", message: "The proposal or review-session identifier is malformed." };
    }
    return null;
  }, [authStatus, proposalId, sessionId]);

  useEffect(() => {
    if (
      authStatus !== "authenticated" ||
      !identifierPattern.test(proposalId) ||
      (sessionId !== undefined && !identifierPattern.test(sessionId))
    ) return;
    const controller = new AbortController();
    async function synchronize() {
      try {
        const result = await acquireGovernanceWorkspace({
          proposalId,
          routeSessionId: sessionId,
          signal: controller.signal,
        });
        if (controller.signal.aborted) return;
        setState(result);
        setSelectedSectionId((current) => result.projection?.sections.some((section) => section.id === current) ? current : result.projection?.sections[0]?.id ?? null);
      } catch (error) {
        if (!controller.signal.aborted) setProblem(normalizeApiProblem(error));
      }
    }
    void synchronize();
    return () => controller.abort();
  }, [authStatus, proposalId, sessionId]);

  const reload = async (knownSessionId: string) => {
    const result = await acquireGovernanceWorkspace({
      proposalId,
      routeSessionId: sessionId,
      knownSessionId,
    });
    setState(result);
    setSelectedSectionId((current) => result.projection?.sections.some((section) => section.id === current) ? current : result.projection?.sections[0]?.id ?? null);
  };

  const run = async (
    operation: "approval" | "rejection" | "population" | "refresh",
    command: () => Promise<void>,
  ) => {
    if (busy) return;
    setBusy(operation);
    setProblem(null);
    try {
      await command();
    } catch (error) {
      const nextProblem = normalizeApiProblem(error);
      setProblem(nextProblem);
      if (nextProblem.status === 401 || nextProblem.status === 403) setDialog(null);
    } finally {
      setBusy(null);
    }
  };

  const refresh = () => {
    if (!state) return;
    void run("refresh", async () => reload(state.session.id));
  };

  const approve = () => {
    if (!state?.readiness || !approvalAllowed(state.session, state.readiness)) return;
    const session = state.session;
    const readiness = state.readiness;
    void run("approval", async () => {
      const result = await approveReview(session.id, readiness.id, session.version, keys.current.key(session.id, "approve"));
      if (!result) return;
      keys.current.retire(session.id, "approve");
      setDialog(null);
      await reload(session.id);
    });
  };

  const reject = () => {
    if (!state || !rejectionReason.trim()) return;
    const session = state.session;
    void run("rejection", async () => {
      const result = await rejectReview(session.id, rejectionReason.trim(), session.version, keys.current.key(session.id, "reject"));
      if (!result) return;
      keys.current.retire(session.id, "reject");
      setDialog(null);
      await reload(session.id);
    });
  };

  const populate = () => {
    if (!state?.projection || !populationAllowed(state.populationReadiness)) return;
    const projection = state.projection;
    void run("population", async () => {
      const result = await populateApprovedProjection(projection.id, projection.checksum, keys.current.key(projection.id, "populate"));
      if (!result) return;
      keys.current.retire(projection.id, "populate");
      setPopulationResult(result);
      setDialog(null);
      await reload(state.session.id);
    });
  };

  if (authStatus === "loading" || (!routeProblem && !state && !problem)) return <LoadingState message="Loading governance workspace…" />;
  if (routeProblem) return <ErrorState title="Governance unavailable" message={routeProblem.message} />;
  if (problem && !state) return <ErrorState title="Governance unavailable" message={problem.message} />;
  if (!state) return <ErrorState title="Governance unavailable" message="No authoritative governance state was returned." />;

  const { session, readiness, projection, populationReadiness, populationRun } = state;
  const stage = governanceStage(session);
  const ordered = projection ? orderedProjection(projection) : null;
  const selectedSection = ordered?.sections.find((section) => section.id === selectedSectionId) ?? null;
  const populatedRunId =
    populationRun?.status === "populated"
      ? populationRun.id
      : populationResult?.status === "populated"
        ? populationResult.population_run_id
        : null;
  const workflow = mapGovernedWorkflow({
    resourceExists: true,
    processingStatus: "ready_for_review",
    reviewStatus: session.status,
    approvalReady: readiness?.ready,
    approvalBlockers: readiness?.reasons.length ?? 0,
    projectionStatus: projection?.status,
    populationStatus: populationResult?.status ?? populationRun?.status ?? populationReadiness?.status,
    populationBlockers: populationReadiness?.blockers.length ?? 0,
    hrefs: {
      processing: `/dashboard/resources/${session.resource.id}`,
      review: `/dashboard/academic-review/${proposalId}`,
      approval: `/dashboard/academic-review/${proposalId}/governance?session=${session.id}`,
      population: `/dashboard/academic-review/${proposalId}/governance?session=${session.id}`,
      retrieval: `/dashboard/academic-review/${proposalId}/governance?session=${session.id}`,
      teaching_readiness: `/dashboard/academic-review/${proposalId}/governance?session=${session.id}`,
    },
  });

  return (
    <main className="space-y-6">
      <header className={panel}>
        <p className="text-sm font-semibold uppercase tracking-wide text-[var(--color-primary)]">Academic governance</p>
        <h1 className="mt-2 text-3xl font-semibold">{session.resource.title}</h1>
        <p className="mt-2 text-sm">Review → approval → population → retrieval → teaching readiness</p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link className={control} href={`/dashboard/academic-review/${proposalId}`}>Back to completed review</Link>
          <Link className={control} href={`/dashboard/resources/${session.resource.id}`}>Back to resource</Link>
          <button className={control} disabled={busy !== null} onClick={refresh} type="button">Refresh</button>
        </div>
      </header>

      {!populatedRunId ? <GovernedWorkflowTimeline workflow={workflow} /> : null}

      {problem ? <section aria-live="assertive" className="rounded-md border border-[var(--color-danger)] p-4"><h2 className="font-semibold">{problem.status === 0 ? "Outcome not yet confirmed" : problem.code ?? "Governance operation failed"}</h2><p className="mt-1 text-sm">{problem.message}</p>{problem.status === 0 ? <p className="mt-2 text-sm">The operation key has been preserved. Refresh authoritative status before deciding whether to recover the same operation.</p> : null}</section> : null}

      <section className={panel}>
        <h2 className="text-xl font-semibold">Governance summary</h2>
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-4">
          <div><dt>Review status</dt><dd>{session.status.replaceAll("_", " ")}</dd></div>
          <div><dt>Review version</dt><dd>{session.version}</dd></div>
          <div><dt>Sections</dt><dd>{session.summary.section_accepted} included / {session.summary.section_rejected} excluded</dd></div>
          <div><dt>Concepts</dt><dd>{session.summary.concept_accepted} included / {session.summary.concept_rejected} excluded</dd></div>
          <div><dt>Approval stage</dt><dd>{stage.replaceAll("_", " ")}</dd></div>
          <div><dt>Projection</dt><dd className="break-all">{projection?.id ?? "Not available"}</dd></div>
          <div><dt>Population</dt><dd>{populationResult?.status ?? populationRun?.status ?? populationReadiness?.status ?? "Not available"}</dd></div>
        </dl>
      </section>

      <section className={panel}>
        <h2 className="text-xl font-semibold">1. Approval decision</h2>
        {stage === "review_incomplete" ? <p className="mt-2 text-sm">Complete the human review before governance operations become available.</p> : null}
        {stage === "rejected" ? <p className="mt-2 font-medium">The backend rejected this proposal. Projection and population operations are unavailable.</p> : null}
        {readiness ? (
          <>
            <p className="mt-2 text-sm">Backend approval readiness: {readiness.ready ? "Ready for approval" : "Blocked"}.</p>
            <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-3">
              <div><dt>Snapshot</dt><dd className="break-all">{readiness.id}</dd></div>
              <div><dt>Accepted sections</dt><dd>{readiness.accepted_sections}</dd></div>
              <div><dt>Accepted concepts</dt><dd>{readiness.accepted_concepts}</dd></div>
              <div><dt>Blocking findings</dt><dd>{readiness.blocking_findings}</dd></div>
              <div><dt>Policy</dt><dd>{readiness.policy_version}</dd></div>
            </dl>
            {readiness.reasons.length ? <ul className="mt-3 list-disc pl-5 text-sm">{readiness.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul> : null}
            <div className="mt-4 flex gap-2">
              <button className={control} disabled={!approvalAllowed(session, readiness) || busy !== null} onClick={() => setDialog("approve")} type="button">Approve proposal</button>
              <button className={control} disabled={session.status !== "ready_for_approval" || busy !== null} onClick={() => setDialog("reject")} type="button">Reject proposal</button>
            </div>
          </>
        ) : stage === "approved" ? <p className="mt-2 font-medium">Approved. The immutable projection is authoritative for the next stage.</p> : null}
      </section>

      <section className={panel}>
        <h2 className="text-xl font-semibold">2. Immutable approved projection</h2>
        {!projection || !ordered ? <p className="mt-2 text-sm">Not available until backend approval creates a projection.</p> : (
          <>
            <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
              <p>Projection version: {projection.projection_version}</p><p>Status: {projection.status.replaceAll("_", " ")}</p>
              <p className="break-all sm:col-span-2">Fingerprint: {projection.checksum}</p>
            </div>
            <div className="mt-4 grid gap-4 md:grid-cols-[0.8fr_1.2fr]">
              <nav aria-label="Approved projection sections"><ul className="space-y-2">{ordered.sections.map((section) => <li key={section.id}><button aria-current={section.id === selectedSectionId ? "true" : undefined} className={`${control} w-full text-left`} onClick={() => setSelectedSectionId(section.id)} type="button">{section.ordinal}. {section.final_title}</button></li>)}</ul></nav>
              <div>{selectedSection ? <><h3 className="font-semibold">{selectedSection.final_title}</h3><p className="mt-2 text-sm">Depth {selectedSection.depth}; source pages {selectedSection.page_range.start ?? "unknown"}–{selectedSection.page_range.end ?? "unknown"}.</p><ul className="mt-3 space-y-2 text-sm">{ordered.concepts.filter((concept) => concept.approved_section_id === selectedSection.id).map((concept) => <li className="rounded border p-2" key={concept.id}>{concept.ordinal}. {concept.final_title}</li>)}</ul></> : <p>Select an approved section.</p>}</div>
            </div>
          </>
        )}
      </section>

      <section className={panel}>
        <h2 className="text-xl font-semibold">3. Academic population</h2>
        {!populationReadiness ? <p className="mt-2 text-sm">Not available until an approved projection exists.</p> : (
          <>
            <p className="mt-2 text-sm">Backend population readiness: {populationReadiness.ready ? "Ready for population" : "Blocked"}.</p>
            <p className="mt-2 text-sm">Expected: {populationReadiness.expected_section_count} sections and {populationReadiness.expected_concept_count} concepts.</p>
            {populationReadiness.blockers.length ? <ul className="mt-3 list-disc pl-5 text-sm">{populationReadiness.blockers.map((blocker) => <li key={blocker.code}>{blocker.code}: {blocker.message}</li>)}</ul> : null}
            {populationRun || populationResult ? (
              <div className="mt-4 rounded border p-3 text-sm" aria-live="polite">
                <p>Status: {populationResult?.status ?? populationRun?.status}</p>
                <p>Run: {populationResult?.population_run_id ?? populationRun?.id}</p>
                <p>Sections: {populationResult?.created_sections ?? populationRun?.created_section_count ?? 0} created, {populationResult?.matched_sections ?? populationRun?.matched_section_count ?? 0} matched.</p>
                <p>Concepts: {populationResult?.created_concepts ?? populationRun?.created_concept_count ?? 0} created, {populationResult?.matched_concepts ?? populationRun?.matched_concept_count ?? 0} matched.</p>
                <p className="mt-2">Retrieval synchronization remains pending. Population does not make this resource ready for teaching.</p>
                <Link className={`${control} mt-3 inline-block`} href={`/dashboard/resources/${session.resource.id}`}>View Academic resource</Link>
              </div>
            ) : <button className={`${control} mt-4`} disabled={!populationAllowed(populationReadiness) || busy !== null} onClick={() => setDialog("populate")} type="button">Populate Academic Platform</button>}
          </>
        )}
      </section>

      {populatedRunId && projection ? (
        <RetrievalTeachingOperations populationRunId={populatedRunId} projectionId={projection.id} resourceId={session.resource.id} resourceTitle={session.resource.title} />
      ) : (
        <section className={panel}>
          <h2 className="text-xl font-semibold">4. Retrieval and teaching readiness</h2>
          <p className="mt-2 text-sm">Complete authoritative Academic population before retrieval synchronization becomes available.</p>
        </section>
      )}

      {dialog === "approve" && readiness ? <GovernanceDialog busy={busy === "approval"} confirmLabel="Confirm approval" onCancel={() => setDialog(null)} onConfirm={approve} title="Approve reviewed proposal?"><p>This creates an immutable approved projection from review version {session.version}. It does not populate Academic content.</p><p className="mt-2">{readiness.accepted_sections} sections and {readiness.accepted_concepts} concepts will be projected.</p></GovernanceDialog> : null}
      {dialog === "reject" ? <GovernanceDialog busy={busy === "rejection"} confirmDisabled={!rejectionReason.trim()} confirmLabel="Confirm rejection" onCancel={() => setDialog(null)} onConfirm={reject} title="Reject reviewed proposal?"><label className="font-medium" htmlFor="rejection-reason">Rejection reason</label><textarea aria-describedby="rejection-help" className={`${control} mt-1 w-full`} id="rejection-reason" onChange={(event) => setRejectionReason(event.target.value)} value={rejectionReason} /><p className="mt-1" id="rejection-help">A nonblank reason is required and will be submitted exactly.</p></GovernanceDialog> : null}
      {dialog === "populate" && projection && populationReadiness ? <GovernanceDialog busy={busy === "population"} confirmLabel="Create official Academic content" onCancel={() => setDialog(null)} onConfirm={populate} title="Populate the Academic Platform?"><p>This operation creates official Academic Platform sections and concepts.</p><p className="mt-2">It does not synchronize retrieval and does not make the resource ready for teaching.</p><p className="mt-2 break-all">Projection: {projection.id}</p><p>{populationReadiness.expected_section_count} sections; {populationReadiness.expected_concept_count} concepts.</p></GovernanceDialog> : null}
    </main>
  );
}
