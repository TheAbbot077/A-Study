"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth";
import { OperationIdempotency } from "@/lib/idempotency";
import {
  getLearningStudioCurrentNode,
  getLearningStudioExperience,
  listLearningStudioCitations,
  listLearningStudioTurns,
  pauseLearningStudio,
  requestLearningStudioNextTurn,
  requestLearningStudioRecap,
  requestLearningStudioReview,
  resumeLearningStudio,
  startLearningStudio,
  submitLearningStudioTurn,
  type LearningStudioCitation,
  type LearningStudioExperience,
  type LearningStudioNodeSummary,
  type LearningStudioTurn,
} from "@/services/self-study";
import { coverageMeaning } from "./experienceViewModel";
import { canSubmitLearnerMessage, studioProgressLabel, studioStatusTitle, turnActionLabel, turnAuthorLabel } from "./learningStudioViewModel";
import { workspaceStatusLabel } from "./workspaceViewModel";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

export function AbbotLearningStudio({ workspaceId }: { workspaceId: string }) {
  const router = useRouter();
  const { status } = useAuth();
  const idempotency = useRef(new OperationIdempotency());
  const [experience, setExperience] = useState<LearningStudioExperience | null>(null);
  const [currentNode, setCurrentNode] = useState<LearningStudioNodeSummary | null>(null);
  const [turns, setTurns] = useState<LearningStudioTurn[]>([]);
  const [citations, setCitations] = useState<LearningStudioCitation[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=/dashboard/self-study/${workspaceId}/learn`);
    }
  }, [router, status, workspaceId]);

  const loadStudioState = useCallback(async (signal?: AbortSignal) => {
    const nextExperience = await getLearningStudioExperience(workspaceId, signal);
    const [nextTurns, nextCitations, nextNode] = await Promise.all([
      nextExperience.teaching_session_id ? listLearningStudioTurns(workspaceId, signal) : Promise.resolve([]),
      nextExperience.teaching_session_id ? listLearningStudioCitations(workspaceId, signal) : Promise.resolve([]),
      nextExperience.current_plan_node_id ? getLearningStudioCurrentNode(workspaceId, signal).catch(() => null) : Promise.resolve(null),
    ]);
    return { nextCitations, nextExperience, nextNode, nextTurns };
  }, [workspaceId]);

  const applyStudioState = useCallback((state: Awaited<ReturnType<typeof loadStudioState>>) => {
    setExperience(state.nextExperience);
    setTurns(state.nextTurns);
    setCitations(state.nextCitations);
    setCurrentNode(state.nextNode);
  }, []);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    const controller = new AbortController();
    async function loadStudio() {
      try {
        const nextState = await loadStudioState(controller.signal);
        if (!active) return;
        applyStudioState(nextState);
        setError(null);
      } catch (loadError) {
        if (!active || controller.signal.aborted) return;
        setError(loadError instanceof Error ? loadError.message : "Unable to open the Learning Studio.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadStudio();
    return () => {
      active = false;
      controller.abort();
    };
  }, [applyStudioState, loadStudioState, status]);

  const canSend = useMemo(() => (experience ? canSubmitLearnerMessage(experience, pending, message) : false), [experience, message, pending]);

  async function runCommand(command: () => Promise<unknown>) {
    setPending(true);
    setError(null);
    try {
      await command();
      const nextState = await loadStudioState();
      applyStudioState(nextState);
    } catch (commandError) {
      setError(commandError instanceof Error ? commandError.message : "Unable to update the Learning Studio.");
    } finally {
      setPending(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const currentExperience = experience;
    if (!currentExperience || !canSend) return;
    const text = message.trim();
    setMessage("");
    const key = idempotency.current.key(workspaceId, "learning-studio-turn");
    const expectedVersion = currentExperience.session_version;
    await runCommand(async () => {
      await submitLearningStudioTurn(workspaceId, text, key, expectedVersion);
      idempotency.current.retire(workspaceId, "learning-studio-turn");
    });
  }

  if (status === "loading" || (status === "authenticated" && loading)) {
    return <LoadingState message="Opening Abbot’s study room..." />;
  }

  if (status === "unauthenticated") {
    return <ErrorState title="Please log in" message="Log in to learn with Abbot." />;
  }

  if (error && !experience) {
    return <ErrorState title="Learning Studio unavailable" message={error} />;
  }

  if (!experience) {
    return <EmptyState title="Learning Studio unavailable" description="Abbot could not find a governed learning state for this workspace." />;
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link className="text-sm font-medium text-[var(--color-primary)] hover:underline" href={`/dashboard/self-study/${workspaceId}/plan`}>
          Back to study plan
        </Link>
        <span className="text-sm text-[var(--color-muted-foreground)]">{studioProgressLabel(experience)}</span>
      </div>

      {error ? <ErrorState title="Learning Studio issue" message={error} /> : null}

      <header className={`${panelClassName} space-y-4`}>
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">Learning Studio</p>
        <h1 className="text-3xl font-semibold text-[var(--color-foreground)]">{studioStatusTitle(experience)}</h1>
        <p className="max-w-3xl text-sm text-[var(--color-muted-foreground)]">
          Abbot teaches from the governed teaching session. Teaching segment completion is not mastery, certification, or a grade.
        </p>
        {currentNode ? (
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
            <p className="text-sm text-[var(--color-muted-foreground)]">Current concept</p>
            <h2 className="mt-1 text-2xl font-semibold text-[var(--color-foreground)]">{currentNode.title}</h2>
            <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">{currentNode.learning_objective || coverageMeaning(currentNode.coverage_state)}</p>
            <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
              {workspaceStatusLabel(currentNode.node_type)} · Segment {currentNode.sequence_index} of {currentNode.total_sequence_count}
            </p>
          </div>
        ) : null}
      </header>

      {experience.blocker_codes.length ? (
        <section className={`${panelClassName} space-y-3 border-l-4 border-l-[var(--color-danger)]`}>
          <h2 className="text-xl font-semibold text-[var(--color-foreground)]">Learning is blocked</h2>
          <ul className="grid gap-2 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-2">
            {experience.blocker_codes.map((code) => (
              <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2" key={code}>{code}</li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr),360px]">
        <div className={`${panelClassName} space-y-4`} aria-label="Abbot teaching stream">
          <div className="flex flex-wrap gap-3">
            {experience.can_start ? <StudioButton disabled={pending} label="Start learning" onClick={() => void runCommand(() => startLearningStudio(workspaceId))} /> : null}
            {experience.can_resume ? <StudioButton disabled={pending} label="Resume" onClick={() => void runCommand(() => resumeLearningStudio(workspaceId))} /> : null}
            {experience.can_pause ? <StudioButton disabled={pending} label="Pause" onClick={() => void runCommand(() => pauseLearningStudio(workspaceId))} secondary /> : null}
            {experience.teaching_session_id && !turns.length ? <StudioButton disabled={pending} label="Continue" onClick={() => void runCommand(() => requestLearningStudioNextTurn(workspaceId))} secondary /> : null}
            {experience.can_request_recap ? <StudioButton disabled={pending} label="Request recap" onClick={() => void runCommand(() => requestLearningStudioRecap(workspaceId))} secondary /> : null}
            {experience.can_request_recap ? <StudioButton disabled={pending} label="Explain more simply" onClick={() => void runCommand(() => requestLearningStudioReview(workspaceId))} secondary /> : null}
            {experience.can_start_concept_check ? (
              <Link className="inline-flex min-h-11 items-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium" href={`/dashboard/self-study/${workspaceId}/learn#concept-check`}>
                Ready for concept check
              </Link>
            ) : null}
          </div>

          {turns.length ? (
            <ol className="space-y-3">
              {turns.map((turn) => <TurnCard key={turn.turn_id} turn={turn} />)}
            </ol>
          ) : (
            <EmptyState title="No teaching turns yet" description="Start learning to ask Abbot for the first teaching segment." />
          )}

          <form className="space-y-3" onSubmit={(event) => void handleSubmit(event)}>
            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Respond to Abbot</span>
              <textarea
                className="min-h-28 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm"
                disabled={!experience.can_send_message || pending}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Ask a question, answer a prompt, or request help."
                value={message}
              />
            </label>
            <button
              className="inline-flex min-h-11 items-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)] disabled:opacity-60"
              disabled={!canSend}
              type="submit"
            >
              {pending ? "Sending..." : "Send response"}
            </button>
          </form>
        </div>

        <aside className={`${panelClassName} space-y-4`} aria-label="Sources">
          <h2 className="text-xl font-semibold text-[var(--color-foreground)]">Sources</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">Citations stay attached to grounded teaching turns. Unsafe or retired sources are not shown as active teaching support.</p>
          {citations.length ? (
            <ul className="space-y-3 text-sm">
              {citations.map((citation) => (
                <li className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3" key={citation.citation_id}>
                  <p className="font-medium text-[var(--color-foreground)]">{citation.resource_title || citation.resource_id}</p>
                  <p className="mt-1 text-[var(--color-muted-foreground)]">
                    Page {citation.page || "unknown"} · {citation.segment || "source segment"}
                  </p>
                  {citation.excerpt ? <p className="mt-2 text-[var(--color-muted-foreground)]">{citation.excerpt}</p> : null}
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No citations yet" description="Sources will appear after Abbot creates grounded teaching turns." />
          )}
        </aside>
      </section>

      <section id="concept-check" className={`${panelClassName} space-y-2`}>
        <h2 className="text-xl font-semibold text-[var(--color-foreground)]">Concept-check handoff</h2>
        <p className="text-sm text-[var(--color-muted-foreground)]">
          When a teaching segment is complete, Abbot can hand you to the formal concept check. That checkpoint arrives in PI-6F.12 and does not imply mastery here.
        </p>
      </section>
    </section>
  );
}

function StudioButton({ disabled, label, onClick, secondary = false }: { disabled: boolean; label: string; onClick: () => void; secondary?: boolean }) {
  return (
    <button
      className={`inline-flex min-h-11 items-center rounded-[var(--radius-md)] px-4 text-sm font-semibold disabled:opacity-60 ${
        secondary ? "border border-[var(--color-border)] text-[var(--color-foreground)]" : "bg-[var(--color-primary)] text-[var(--color-primary-foreground)]"
      }`}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {label}
    </button>
  );
}

function TurnCard({ turn }: { turn: LearningStudioTurn }) {
  const isAbbot = turn.role === "ABBOT";
  return (
    <li className={`rounded-[var(--radius-md)] border p-4 ${isAbbot ? "border-[var(--color-primary)]" : "border-[var(--color-border)]"}`}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="font-semibold text-[var(--color-foreground)]">{turnAuthorLabel(turn)}</p>
        <p className="text-xs uppercase tracking-[0.08em] text-[var(--color-muted-foreground)]">{turnActionLabel(turn.action_type)}</p>
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm text-[var(--color-muted-foreground)]">{turn.content}</p>
      {turn.citations.length ? <p className="mt-3 text-xs text-[var(--color-primary)]">{turn.citations.length} source citation{turn.citations.length === 1 ? "" : "s"}</p> : null}
    </li>
  );
}
