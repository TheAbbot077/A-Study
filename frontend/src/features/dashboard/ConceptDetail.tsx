"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { ErrorState, LoadingState } from "@/components/feedback";
import {
  getContentConcept,
  getContentSection,
  getLearningResource,
  getSubject,
  type ContentConcept,
  type ContentSection,
  type LearningResource,
  type Subject,
} from "@/services/academic";
import {
  askSessionQuestion,
  getSessionConversation,
  listConceptBrowserStates,
  startOrResumeConcept,
  teachSession,
  type ConceptBrowserStatus,
  type ConversationTurn,
  type LearningConversationState,
} from "@/services/learning";

type ConceptDetailProps = {
  conceptId: string;
};

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

function labelForStatus(status: ConceptBrowserStatus["status"]) {
  switch (status) {
    case "available":
      return "Available";
    case "in_progress":
      return "In progress";
    case "mastered":
      return "Mastered";
    case "needs_remediation":
      return "Needs remediation";
    default:
      return "Locked";
  }
}

function turnBubbleClassName(turn: ConversationTurn) {
  if (turn.sender_type === "abbot") {
    return "border-[var(--color-primary)]/35 bg-[var(--color-primary)]/8";
  }
  if (turn.sender_type === "learner") {
    return "border-[var(--color-border)] bg-[var(--color-accent)]/20";
  }
  return "border-[var(--color-border)] bg-transparent";
}

function turnLabel(turn: ConversationTurn) {
  if (turn.sender_type === "abbot") {
    return "The Abbot";
  }
  if (turn.sender_type === "learner") {
    return "You";
  }
  return turn.sender_type;
}

export function ConceptDetail({ conceptId }: ConceptDetailProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [concept, setConcept] = useState<ContentConcept | null>(null);
  const [section, setSection] = useState<ContentSection | null>(null);
  const [resource, setResource] = useState<LearningResource | null>(null);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [state, setState] = useState<ConceptBrowserStatus | null>(null);
  const [conversation, setConversation] = useState<LearningConversationState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [teaching, setTeaching] = useState(false);
  const [asking, setAsking] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadLearningScreen() {
      setLoading(true);
      setError(null);

      try {
        const nextConcept = await getContentConcept(conceptId);
        const nextSection = await getContentSection(nextConcept.content_section);
        const nextResource = await getLearningResource(nextSection.learning_resource);
        const [nextSubject, nextStates] = await Promise.all([
          getSubject(nextResource.subject),
          listConceptBrowserStates(nextResource.id),
        ]);

        const nextState = nextStates.find((item) => item.concept_id === conceptId) ?? null;
        let sessionId = searchParams.get("session") || nextState?.session_id || null;
        let nextConversation: LearningConversationState | null = null;

        if (!sessionId && nextState?.can_start_or_resume) {
          const session = await startOrResumeConcept(conceptId);
          sessionId = session.id;
          router.replace(`/dashboard/concepts/${conceptId}?session=${encodeURIComponent(session.id)}`);
        }

        if (sessionId) {
          nextConversation = await getSessionConversation(sessionId);
          if (nextConversation.turns.length === 0) {
            const teachingEnvelope = await teachSession(sessionId);
            nextConversation = teachingEnvelope.conversation;
          }
        }

        if (!isMounted) {
          return;
        }

        setConcept(nextConcept);
        setSection(nextSection);
        setResource(nextResource);
        setSubject(nextSubject);
        setState(
          nextState && sessionId
            ? {
                ...nextState,
                status: nextConversation?.turns.length ? "in_progress" : nextState.status,
                session_id: sessionId,
              }
            : nextState,
        );
        setConversation(nextConversation);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Unable to load this concept right now.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void loadLearningScreen();

    return () => {
      isMounted = false;
    };
  }, [conceptId, router, searchParams]);

  const sessionId = conversation?.session.id || searchParams.get("session") || state?.session_id || null;

  const canStartOrResume = Boolean(state?.can_start_or_resume && !sessionId);
  const canAskQuestion = Boolean(sessionId && conversation);
  const turns = conversation?.turns ?? [];

  const progressLabel = useMemo(() => {
    if (asking) {
      return conversation?.streaming_supported ? "The Abbot is responding..." : "The Abbot is preparing a response...";
    }
    if (teaching) {
      return conversation?.streaming_supported ? "The Abbot is teaching..." : "The Abbot is preparing the lesson...";
    }
    return null;
  }, [asking, conversation?.streaming_supported, teaching]);

  async function handleStartOrResume() {
    setStarting(true);
    setError(null);

    try {
      const session = await startOrResumeConcept(conceptId);
      router.replace(`/dashboard/concepts/${conceptId}?session=${encodeURIComponent(session.id)}`);

      let nextConversation = await getSessionConversation(session.id);
      if (nextConversation.turns.length === 0) {
        setTeaching(true);
        const teachingEnvelope = await teachSession(session.id);
        nextConversation = teachingEnvelope.conversation;
      }

      setConversation(nextConversation);
      setState((current) =>
        current
          ? {
              ...current,
              status: "in_progress",
              session_id: session.id,
              session_status: session.status,
              can_start_or_resume: true,
              action_label: session.status === "paused" ? "Resume concept" : "Continue concept",
            }
          : current,
      );
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Unable to open this concept right now.");
    } finally {
      setTeaching(false);
      setStarting(false);
    }
  }

  async function handleSubmitQuestion(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!sessionId) {
      setError("Start the concept first so the conversation can begin.");
      return;
    }

    const form = event.currentTarget;
    const formData = new FormData(form);
    const question = String(formData.get("question") || "").trim();
    if (!question) {
      setError("Ask a question so The Abbot has something to respond to.");
      return;
    }

    setAsking(true);
    setError(null);

    try {
      const envelope = await askSessionQuestion(sessionId, question);
      setConversation(envelope.conversation);
      setState((current) =>
        current
          ? {
              ...current,
              status: "in_progress",
              session_id: envelope.conversation.session.id,
              session_status: envelope.conversation.session.status,
            }
          : current,
      );
      form.reset();
    } catch (questionError) {
      setError(questionError instanceof Error ? questionError.message : "Unable to send that question right now.");
    } finally {
      setAsking(false);
    }
  }

  if (loading) {
    return <LoadingState message="Loading concept learning screen..." />;
  }

  if (error && !concept) {
    return <ErrorState title="Concept unavailable" message={error} />;
  }

  if (!concept || !section || !resource) {
    return <ErrorState title="Concept unavailable" message="We couldn't find this concept." />;
  }

  return (
    <section className="space-y-8">
      <div className="flex flex-wrap items-center gap-3 text-sm text-[var(--color-muted-foreground)]">
        <Link className="hover:text-[var(--color-foreground)]" href="/dashboard">
          Dashboard
        </Link>
        <span>/</span>
        {subject ? (
          <Link className="hover:text-[var(--color-foreground)]" href={`/dashboard/subjects/${subject.id}`}>
            {subject.name}
          </Link>
        ) : null}
        <span>/</span>
        <Link className="hover:text-[var(--color-foreground)]" href={`/dashboard/resources/${resource.id}`}>
          {resource.title}
        </Link>
        <span>/</span>
        <span className="text-[var(--color-foreground)]">{concept.title}</span>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <section className={`${panelClassName} space-y-4`}>
          <div className="space-y-2">
            <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">{section.title}</p>
            <h1 className="text-3xl font-semibold text-[var(--color-foreground)] sm:text-4xl">{concept.title}</h1>
            <p className="max-w-3xl text-sm text-[var(--color-muted-foreground)] sm:text-base">
              {concept.description || "The Abbot will teach this concept from the grounded academic source."}
            </p>
          </div>

          <dl className="grid gap-4 text-sm text-[var(--color-muted-foreground)] md:grid-cols-3">
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Concept status</dt>
              <dd className="mt-1">{state ? labelForStatus(state.status) : "Unknown"}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Learning objective</dt>
              <dd className="mt-1">{concept.learning_objective || "Objective will be refined in later learning steps."}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Session</dt>
              <dd className="mt-1">{sessionId ?? "Not started yet"}</dd>
            </div>
          </dl>

          {error ? <ErrorState title="Learning screen issue" message={error} /> : null}
        </section>

        <aside className={`${panelClassName} space-y-4`}>
          <div className="space-y-2">
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Next step</h2>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Move into teaching here, then continue to a mastery check when you're ready.
            </p>
          </div>

          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 text-sm text-[var(--color-muted-foreground)]">
            {sessionId
              ? "Your pedagogical session is active. Ask a question when something feels fuzzy, then continue to the mastery check."
              : "Open the concept to let The Abbot start the teaching session before you move into assessment."}
          </div>

          {canStartOrResume ? (
            <button
              className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
              disabled={starting}
              onClick={() => void handleStartOrResume()}
              type="button"
            >
              {starting ? "Opening lesson..." : (state?.action_label ?? "Start concept")}
            </button>
          ) : null}

          <Link
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
            href={`/dashboard/resources/${resource.id}`}
          >
            Back to resource outline
          </Link>

          <Link
            className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
            href={`/dashboard/concepts/${concept.id}/assessment${sessionId ? `?session=${encodeURIComponent(sessionId)}` : ""}`}
          >
            Proceed to mastery check
          </Link>

          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 text-sm text-[var(--color-muted-foreground)]">
            {conversation?.streaming_supported
              ? "This concept supports streaming responses."
              : "Responses arrive after The Abbot finishes preparing them. Live token streaming is not enabled yet."}
          </div>
        </aside>
      </div>

      <section className={panelClassName}>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Learn with The Abbot</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            The teaching flow is grounded in the backend pedagogical services and conversation orchestration.
          </p>
        </div>

        {!sessionId ? (
          <div className="rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] p-6 text-sm text-[var(--color-muted-foreground)]">
            Start or resume this concept to receive the first Abbot lesson and begin the conversation.
          </div>
        ) : (
          <div className="space-y-4">
            {turns.length === 0 ? (
              <div className="rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] p-6 text-sm text-[var(--color-muted-foreground)]">
                The Abbot is preparing the opening lesson for this concept.
              </div>
            ) : (
              <div className="space-y-4">
                {turns.map((turn) => (
                  <article
                    className={`rounded-[var(--radius-md)] border p-4 ${turnBubbleClassName(turn)}`.trim()}
                    key={`${turn.sequence_number}-${turn.sender_type}`}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-[var(--color-foreground)]">{turnLabel(turn)}</p>
                      <p className="text-xs uppercase tracking-[0.08em] text-[var(--color-muted-foreground)]">
                        {turn.message_type.replace(/_/g, " ")}
                      </p>
                    </div>
                    <div className="mt-3 whitespace-pre-line text-sm leading-6 text-[var(--color-foreground)]">{turn.content}</div>
                  </article>
                ))}
              </div>
            )}

            {progressLabel ? (
              <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 text-sm text-[var(--color-muted-foreground)]">
                {progressLabel}
              </div>
            ) : null}

            <form className="space-y-3" onSubmit={(event) => void handleSubmitQuestion(event)}>
              <label className="block space-y-2">
                <span className="text-sm font-medium text-[var(--color-foreground)]">Ask The Abbot a question</span>
                <textarea
                  className="min-h-28 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm"
                  disabled={!canAskQuestion || asking}
                  name="question"
                  placeholder="What part of this concept would you like clarified?"
                  required
                />
              </label>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  {conversation?.next_expected_interaction
                    ? `Next expected interaction: ${conversation.next_expected_interaction.replace(/_/g, " ")}`
                    : "The backend will determine the next pedagogical interaction."}
                </p>
                <button
                  className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
                  disabled={!canAskQuestion || asking}
                  type="submit"
                >
                  {asking ? "Sending question..." : "Ask The Abbot"}
                </button>
              </div>
            </form>

            <div className="flex flex-col gap-3 border-t border-[var(--color-border)] pt-4 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-sm text-[var(--color-muted-foreground)]">
                When the explanation feels clear enough, move on to the mastery check for this concept.
              </p>
              <Link
                className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105"
                href={`/dashboard/concepts/${concept.id}/assessment${sessionId ? `?session=${encodeURIComponent(sessionId)}` : ""}`}
              >
                Continue to mastery check
              </Link>
            </div>
          </div>
        )}
      </section>
    </section>
  );
}
