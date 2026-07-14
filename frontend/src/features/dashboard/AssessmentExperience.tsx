"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { type FormEvent, useEffect, useMemo, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
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
  completeMasteryCheck,
  getMasteryCheck,
  startMasteryCheck,
  submitAssessmentAnswer,
  type AssessmentQuestion,
  type MasteryCheckSnapshot,
} from "@/services/assessments";
import { startRemediationPlan } from "@/services/remediation";

type AssessmentExperienceProps = {
  conceptId: string;
};

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

function decisionLabel(decision?: string | null) {
  return decision?.replace(/_/g, " ") ?? "No decision yet";
}

function currentQuestion(snapshot: MasteryCheckSnapshot | null): AssessmentQuestion | null {
  if (!snapshot) {
    return null;
  }
  const firstUnsubmitted = snapshot.questions.find((question) => !question.submitted) ?? null;
  if (snapshot.current_question_id) {
    const current = snapshot.questions.find((question) => question.id === snapshot.current_question_id) ?? null;
    if (current && !current.submitted) {
      return current;
    }
  }
  return firstUnsubmitted;
}

function initialResponseValue(question: AssessmentQuestion | null) {
  if (!question?.response_data) {
    return "";
  }
  const answer = question.response_data.answer;
  return typeof answer === "string" ? answer : "";
}

export function AssessmentExperience({ conceptId }: AssessmentExperienceProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [concept, setConcept] = useState<ContentConcept | null>(null);
  const [section, setSection] = useState<ContentSection | null>(null);
  const [resource, setResource] = useState<LearningResource | null>(null);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [snapshot, setSnapshot] = useState<MasteryCheckSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [startingRemediation, setStartingRemediation] = useState(false);
  const [responseValue, setResponseValue] = useState("");

  useEffect(() => {
    let isMounted = true;

    async function loadAssessmentScreen() {
      setLoading(true);
      setError(null);

      try {
        const nextConcept = await getContentConcept(conceptId);
        const nextSection = await getContentSection(nextConcept.content_section);
        const nextResource = await getLearningResource(nextSection.learning_resource);
        const [nextSubject, nextSnapshot] = await Promise.all([
          getSubject(nextResource.subject),
          getMasteryCheck(conceptId),
        ]);

        if (!isMounted) {
          return;
        }

        setConcept(nextConcept);
        setSection(nextSection);
        setResource(nextResource);
        setSubject(nextSubject);
        setSnapshot(nextSnapshot);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Unable to load this mastery check right now.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void loadAssessmentScreen();

    return () => {
      isMounted = false;
    };
  }, [conceptId]);

  const activeQuestion = useMemo(() => currentQuestion(snapshot), [snapshot]);

  useEffect(() => {
    setResponseValue(initialResponseValue(activeQuestion));
  }, [activeQuestion]);

  async function handleStart() {
    setStarting(true);
    setError(null);

    try {
      const nextSnapshot = await startMasteryCheck(conceptId);
      setSnapshot(nextSnapshot);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Unable to start the mastery check right now.");
    } finally {
      setStarting(false);
    }
  }

  async function handleSubmitAnswer(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!snapshot?.delivery_session || !activeQuestion) {
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const nextSnapshot = await submitAssessmentAnswer(snapshot.delivery_session.id, activeQuestion.id, {
        answer: responseValue,
      });
      setSnapshot(nextSnapshot);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to submit this answer right now.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleComplete() {
    if (!snapshot?.delivery_session) {
      return;
    }

    setCompleting(true);
    setError(null);

    try {
      const nextSnapshot = await completeMasteryCheck(snapshot.delivery_session.id);
      setSnapshot(nextSnapshot);
    } catch (completeError) {
      setError(completeError instanceof Error ? completeError.message : "Unable to complete the mastery check right now.");
    } finally {
      setCompleting(false);
    }
  }

  async function handleStartRemediation() {
    if (!snapshot?.remediation_plan) {
      return;
    }

    setStartingRemediation(true);
    setError(null);

    try {
      await startRemediationPlan(snapshot.remediation_plan.id);
      const refreshed = await getMasteryCheck(conceptId);
      setSnapshot(refreshed);
    } catch (remediationError) {
      setError(remediationError instanceof Error ? remediationError.message : "Unable to start remediation right now.");
    } finally {
      setStartingRemediation(false);
    }
  }

  if (loading) {
    return <LoadingState message="Loading mastery check..." />;
  }

  if (error && !concept) {
    return <ErrorState title="Mastery check unavailable" message={error} />;
  }

  if (!concept || !section || !resource) {
    return <ErrorState title="Mastery check unavailable" message="We couldn't find this concept." />;
  }

  const sessionId = searchParams.get("session");
  const passed = snapshot?.result?.passed === true || snapshot?.mastery_profile?.current_decision === "mastered";
  const needsRemediation = Boolean(snapshot?.remediation_plan);
  const allQuestionsSubmitted = Boolean(snapshot?.questions.length) && Boolean(snapshot?.questions.every((question) => question.submitted));
  const submittedCount = snapshot?.questions.filter((question) => question.submitted).length ?? 0;

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
        <Link className="hover:text-[var(--color-foreground)]" href={`/dashboard/concepts/${concept.id}${sessionId ? `?session=${encodeURIComponent(sessionId)}` : ""}`}>
          {concept.title}
        </Link>
        <span>/</span>
        <span className="text-[var(--color-foreground)]">Mastery check</span>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.15fr,0.85fr]">
        <section className={`${panelClassName} space-y-4`}>
          <div className="space-y-2">
            <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">Mastery check</p>
            <h1 className="text-3xl font-semibold text-[var(--color-foreground)] sm:text-4xl">{concept.title}</h1>
            <p className="max-w-3xl text-sm text-[var(--color-muted-foreground)] sm:text-base">
              Complete this check to record evidence of learning and receive the backend mastery decision for the current concept.
            </p>
          </div>

          <dl className="grid gap-4 text-sm text-[var(--color-muted-foreground)] md:grid-cols-3">
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Assessment</dt>
              <dd className="mt-1">{snapshot?.assessment?.title ?? "No assessment available"}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Decision</dt>
              <dd className="mt-1 capitalize">{decisionLabel(snapshot?.mastery_profile?.current_decision)}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Evidence count</dt>
              <dd className="mt-1">{snapshot?.mastery_profile?.evidence_count ?? snapshot?.evidence.length ?? 0}</dd>
            </div>
          </dl>

          {error ? <ErrorState title="Assessment issue" message={error} /> : null}
        </section>

        <aside className={`${panelClassName} space-y-4`}>
          <div className="space-y-2">
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Outcome path</h2>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              The backend decides mastery, evidence updates, and remediation. This screen just renders the result.
            </p>
          </div>

          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 text-sm text-[var(--color-muted-foreground)]">
            {snapshot?.delivery_session
              ? `Question progress: ${submittedCount} of ${snapshot.questions.length} submitted.`
              : "Start the mastery check when you are ready to turn this concept into evidence of learning."}
          </div>

          {passed ? (
            <div className="rounded-[var(--radius-md)] border border-[var(--color-success)]/60 p-4">
              <h3 className="text-base font-semibold text-[var(--color-foreground)]">Mastery success</h3>
              <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
                You passed this mastery check. Continue to the next available concept when you're ready.
              </p>
              <div className="mt-4 flex flex-wrap gap-3">
                {snapshot?.next_available_concept_id ? (
                  <Link
                    className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105"
                    href={`/dashboard/concepts/${snapshot.next_available_concept_id}`}
                  >
                    Next concept{snapshot.next_available_concept_title ? `: ${snapshot.next_available_concept_title}` : ""}
                  </Link>
                ) : null}
                <Link
                  className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
                  href={`/dashboard/resources/${resource.id}`}
                >
                  Back to resource
                </Link>
              </div>
            </div>
          ) : needsRemediation ? (
            <div className="rounded-[var(--radius-md)] border border-[var(--color-warning)]/60 p-4">
              <h3 className="text-base font-semibold text-[var(--color-foreground)]">Remediation available</h3>
              <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
                The backend produced a remediation plan for this concept. Start it to continue the support path without leaving the current learning flow.
              </p>
              <button
                className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
                disabled={startingRemediation}
                onClick={() => void handleStartRemediation()}
                type="button"
              >
                {startingRemediation ? "Starting remediation..." : "Start remediation"}
              </button>
            </div>
          ) : (
            <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 text-sm text-[var(--color-muted-foreground)]">
              Complete the mastery check to see whether the next step is progression or remediation.
            </div>
          )}
        </aside>
      </div>

      {!snapshot?.assessment ? (
        <section className={panelClassName}>
          <EmptyState
            title="No mastery check available yet"
            description="This concept does not currently have an assessment configured in the backend. Return to the concept page to keep learning, or choose another concept from the resource outline."
          />
          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
              href={`/dashboard/concepts/${concept.id}${sessionId ? `?session=${encodeURIComponent(sessionId)}` : ""}`}
            >
              Back to concept
            </Link>
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
              href={`/dashboard/resources/${resource.id}`}
            >
              Back to resource
            </Link>
          </div>
        </section>
      ) : null}

      {snapshot?.assessment ? (
        <section className={panelClassName}>
          <div className="mb-4">
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Assessment</h2>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Answer the current item, submit it to the backend, then complete the mastery check for grading and mastery evaluation.
            </p>
          </div>

          {!snapshot.delivery_session && snapshot.can_start ? (
            <button
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
              disabled={starting}
              onClick={() => void handleStart()}
              type="button"
            >
              {starting ? "Starting mastery check..." : "Start mastery check"}
            </button>
          ) : null}

          {snapshot.delivery_session && activeQuestion ? (
            <form className="space-y-5" onSubmit={(event) => void handleSubmitAnswer(event)}>
              <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-5">
                <div className="space-y-2">
                  <p className="text-sm font-medium text-[var(--color-primary)]">Question {activeQuestion.sequence_number}</p>
                  <h3 className="text-lg font-semibold text-[var(--color-foreground)]">{activeQuestion.prompt}</h3>
                </div>

                {activeQuestion.item_type === "multiple_choice" || activeQuestion.item_type === "true_false" ? (
                  <div className="mt-4 space-y-3">
                    {(activeQuestion.options ?? []).map((option) => (
                      <label
                        className="flex cursor-pointer items-start gap-3 rounded-[var(--radius-md)] border border-[var(--color-border)] p-4"
                        key={option.id}
                      >
                        <input
                          checked={responseValue === option.label}
                          className="mt-1"
                          name="answer"
                          onChange={() => setResponseValue(option.label)}
                          type="radio"
                        />
                        <div className="space-y-1">
                          <p className="text-sm font-semibold text-[var(--color-foreground)]">{option.label}</p>
                          <p className="text-sm text-[var(--color-muted-foreground)]">{option.content}</p>
                        </div>
                      </label>
                    ))}
                  </div>
                ) : (
                  <label className="mt-4 block space-y-2">
                    <span className="text-sm font-medium text-[var(--color-foreground)]">Your answer</span>
                    <textarea
                      className="min-h-28 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm"
                      onChange={(event) => setResponseValue(event.target.value)}
                      placeholder="Write your answer here."
                      value={responseValue}
                    />
                  </label>
                )}
              </div>

              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  {submittedCount} of {snapshot.questions.length} question(s) submitted
                </p>
                <button
                  className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
                  disabled={submitting || !responseValue.trim()}
                  type="submit"
                >
                  {submitting ? "Submitting answer..." : "Submit answer"}
                </button>
              </div>
            </form>
          ) : null}

          {snapshot.delivery_session && !activeQuestion && snapshot.questions.length > 0 ? (
            <div className="space-y-4">
              <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-5 text-sm text-[var(--color-muted-foreground)]">
                All current questions have been answered. Complete the mastery check to receive grading, evidence updates, and the mastery decision.
              </div>
              <button
                className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-5 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
                disabled={completing || !allQuestionsSubmitted}
                onClick={() => void handleComplete()}
                type="button"
              >
                {completing ? "Completing mastery check..." : "Complete mastery check"}
              </button>
            </div>
          ) : null}
        </section>
      ) : null}

      {snapshot?.result ? (
        <section className={panelClassName}>
          <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Results</h2>
          <dl className="mt-4 grid gap-4 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-3">
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Score</dt>
              <dd className="mt-1">
                {snapshot.result.total_score} / {snapshot.result.max_score}
              </dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Percentage</dt>
              <dd className="mt-1">{snapshot.result.percentage ?? "n/a"}%</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Passed</dt>
              <dd className="mt-1">{snapshot.result.passed ? "Yes" : "No"}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      {snapshot?.mastery_profile ? (
        <section className={panelClassName}>
          <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Evidence and progress</h2>
          <dl className="mt-4 grid gap-4 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-3">
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Current decision</dt>
              <dd className="mt-1 capitalize">{decisionLabel(snapshot.mastery_profile.current_decision)}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Confidence</dt>
              <dd className="mt-1">{snapshot.mastery_profile.confidence}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Evidence count</dt>
              <dd className="mt-1">{snapshot.mastery_profile.evidence_count}</dd>
            </div>
          </dl>

          {snapshot.evidence.length ? (
            <div className="mt-4 space-y-3">
              {snapshot.evidence.map((evidence) => (
                <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4" key={evidence.id}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-[var(--color-foreground)]">{evidence.evidence_type.replace(/_/g, " ")}</p>
                    <p className="text-xs uppercase tracking-[0.08em] text-[var(--color-muted-foreground)]">
                      confidence {evidence.confidence}
                    </p>
                  </div>
                  <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">
                    Source: {evidence.source_type.replace(/_/g, " ")}
                    {typeof evidence.score === "number" ? ` | Score: ${evidence.score}` : ""}
                  </p>
                </article>
              ))}
            </div>
          ) : null}
        </section>
      ) : null}

      {snapshot?.remediation_plan ? (
        <section className={panelClassName}>
          <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Remediation plan</h2>
          <p className="mt-2 text-sm text-[var(--color-muted-foreground)]">{snapshot.remediation_plan.rationale}</p>

          {snapshot.remediation_plan.recommendations.length ? (
            <div className="mt-4 space-y-3">
              {snapshot.remediation_plan.recommendations.map((recommendation) => (
                <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4" key={recommendation.id}>
                  <p className="text-sm font-semibold text-[var(--color-foreground)]">{recommendation.title}</p>
                  <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">{recommendation.rationale}</p>
                </article>
              ))}
            </div>
          ) : null}

          {snapshot.remediation_plan.activities.length ? (
            <div className="mt-4 space-y-3">
              {snapshot.remediation_plan.activities.map((activity) => (
                <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4" key={activity.id}>
                  <p className="text-sm font-semibold text-[var(--color-foreground)]">{activity.title}</p>
                  <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">{activity.instructions || activity.activity_type.replace(/_/g, " ")}</p>
                </article>
              ))}
            </div>
          ) : null}

          <div className="mt-4 flex flex-wrap gap-3">
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
              href={`/dashboard/concepts/${concept.id}${sessionId ? `?session=${encodeURIComponent(sessionId)}` : ""}`}
            >
              Return to concept
            </Link>
            <Link
              className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 py-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
              href={`/dashboard/resources/${resource.id}`}
            >
              Back to resource
            </Link>
          </div>
        </section>
      ) : null}
    </section>
  );
}
