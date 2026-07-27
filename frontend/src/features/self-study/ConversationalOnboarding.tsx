"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, type ReactNode, useEffect, useMemo, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth";
import {
  completeConversationalOnboarding,
  getConversationalOnboarding,
  getSelfStudyWorkspace,
  listConversationalOnboardingCandidates,
  resolveConversationalOnboardingCurriculum,
  selectConversationalOnboardingCurriculum,
  startConversationalOnboarding,
  updateConversationalOnboarding,
  type CurriculumCandidate,
  type OnboardingIntentChoice,
  type SelfStudyOnboardingSession,
  type SelfStudyWorkspace,
} from "@/services/self-study";
import { workspaceStatusLabel } from "./workspaceViewModel";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

const intentLabels = {
  EXAM: "I want to study to sit for an exam",
  LEARN_NEW: "I want to learn something new",
  MASTER_SUBJECT: "I want to learn and master a subject",
} satisfies Record<OnboardingIntentChoice, string>;

function message(author: "Abbot" | "You", children: ReactNode) {
  return (
    <article className={`max-w-3xl rounded-[var(--radius-lg)] border p-4 ${author === "Abbot" ? "border-[var(--color-border)] bg-[var(--color-muted)]/20" : "ml-auto border-[var(--color-primary)]/40"}`}>
      <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-muted-foreground)]">{author}</p>
      <div className="mt-2 text-sm text-[var(--color-foreground)]">{children}</div>
    </article>
  );
}

export function ConversationalOnboarding({ workspaceId }: { workspaceId: string }) {
  const router = useRouter();
  const { status } = useAuth();
  const [workspace, setWorkspace] = useState<SelfStudyWorkspace | null>(null);
  const [onboarding, setOnboarding] = useState<SelfStudyOnboardingSession | null>(null);
  const [candidates, setCandidates] = useState<CurriculumCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace(`/login?next=/dashboard/self-study/${workspaceId}/intent`);
    }
  }, [router, status, workspaceId]);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    const controller = new AbortController();
    async function load() {
      try {
        const [nextWorkspace, nextOnboarding] = await Promise.all([
          getSelfStudyWorkspace(workspaceId, controller.signal),
          getConversationalOnboarding(workspaceId, controller.signal),
        ]);
        if (!active) return;
        setWorkspace(nextWorkspace);
        setOnboarding("id" in nextOnboarding ? nextOnboarding : null);
        setError(null);
      } catch (loadError) {
        if (!active || controller.signal.aborted) return;
        setError(loadError instanceof Error ? loadError.message : "Unable to open onboarding.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
      controller.abort();
    };
  }, [status, workspaceId]);

  useEffect(() => {
    if (!onboarding || !["AWAITING_CURRICULUM_SELECTION", "REVIEWING_SUMMARY"].includes(onboarding.status)) return;
    const controller = new AbortController();
    listConversationalOnboardingCandidates(workspaceId, controller.signal)
      .then(setCandidates)
      .catch((candidateError) => setError(candidateError instanceof Error ? candidateError.message : "Unable to load curriculum candidates."));
    return () => controller.abort();
  }, [onboarding, workspaceId]);

  const selectedIntentLabel = onboarding?.study_intent ? intentLabels[onboarding.study_intent] : "";
  const weeklyHours = useMemo(() => {
    if (!onboarding?.weekly_study_minutes) return "";
    return `${Math.round((onboarding.weekly_study_minutes / 60) * 10) / 10} hours/week`;
  }, [onboarding?.weekly_study_minutes]);

  async function start() {
    setBusy("start");
    setError(null);
    try {
      const next = await startConversationalOnboarding(workspaceId, `onboarding:${workspaceId}`);
      setOnboarding(next);
    } catch (startError) {
      setError(startError instanceof Error ? startError.message : "Unable to start onboarding.");
    } finally {
      setBusy(null);
    }
  }

  async function submitContext(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!onboarding) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    const weeklyHoursValue = String(formData.get("weekly_hours") || "").trim();
    setBusy("context");
    setError(null);
    try {
      const next = await updateConversationalOnboarding(workspaceId, {
        expected_version: onboarding.version,
        topic_query: String(formData.get("topic_query") || onboarding.topic_query || "").trim(),
        study_intent: String(formData.get("study_intent") || onboarding.study_intent || "") as OnboardingIntentChoice,
        qualification_query: String(formData.get("qualification_query") || onboarding.qualification_query || "").trim(),
        awarding_body_query: String(formData.get("awarding_body_query") || onboarding.awarding_body_query || "").trim(),
        jurisdiction_query: String(formData.get("jurisdiction_query") || onboarding.jurisdiction_query || "").trim(),
        level_query: String(formData.get("level_query") || onboarding.level_query || "").trim(),
        target_description: String(formData.get("target_description") || onboarding.target_description || "").trim(),
        target_date_known: Boolean(formData.get("target_date_known")),
        target_date: String(formData.get("target_date") || "") || null,
        weekly_study_minutes: weeklyHoursValue ? Math.round(Number(weeklyHoursValue) * 60) : onboarding.weekly_study_minutes,
      });
      setOnboarding(next);
    } catch (contextError) {
      setError(contextError instanceof Error ? contextError.message : "Unable to save those answers.");
    } finally {
      setBusy(null);
    }
  }

  async function resolve() {
    if (!onboarding) return;
    setBusy("resolve");
    setError(null);
    try {
      const next = await resolveConversationalOnboardingCurriculum(workspaceId, onboarding.version);
      setOnboarding(next);
      setCandidates(await listConversationalOnboardingCandidates(workspaceId));
    } catch (resolveError) {
      setError(resolveError instanceof Error ? resolveError.message : "Unable to resolve governed curriculum options.");
    } finally {
      setBusy(null);
    }
  }

  async function selectCandidate(candidate: CurriculumCandidate) {
    if (!onboarding) return;
    setBusy(candidate.candidate_id);
    setError(null);
    try {
      setOnboarding(await selectConversationalOnboardingCurriculum(workspaceId, onboarding.version, candidate.candidate_id));
    } catch (selectError) {
      setError(selectError instanceof Error ? selectError.message : "Unable to select that curriculum.");
    } finally {
      setBusy(null);
    }
  }

  async function complete() {
    if (!onboarding) return;
    setBusy("complete");
    setError(null);
    try {
      const next = await completeConversationalOnboarding(workspaceId, onboarding.version);
      setOnboarding(next);
    } catch (completeError) {
      setError(completeError instanceof Error ? completeError.message : "Unable to complete onboarding.");
    } finally {
      setBusy(null);
    }
  }

  if (status === "loading" || (status === "authenticated" && loading)) {
    return <LoadingState message="Opening conversational onboarding..." />;
  }
  if (status === "unauthenticated") {
    return <ErrorState title="Please log in" message="Log in to continue onboarding." />;
  }
  if (!workspace) {
    return <ErrorState title="Workspace unavailable" message={error ?? "This workspace could not be opened."} />;
  }

  return (
    <section className="space-y-6">
      <Link className="text-sm font-medium text-[var(--color-primary)] hover:underline" href={`/dashboard/self-study/${workspace.id}`}>
        Back to workspace
      </Link>
      <header className={`${panelClassName} space-y-3`}>
        <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">Conversational onboarding</p>
        <h1 className="text-3xl font-semibold text-[var(--color-foreground)]">Let’s find the right governed curriculum</h1>
        <p className="max-w-3xl text-sm text-[var(--color-muted-foreground)]">
          Tell Abbot what you want to study. We’ll use verified curriculum records for authority; your words help discovery but never create a syllabus.
        </p>
      </header>
      {error ? <ErrorState title="Onboarding issue" message={error} /> : null}
      {!onboarding ? (
        <section className={`${panelClassName} space-y-4`}>
          {message("Abbot", <p>What would you like to study? I’ll guide you through a few short questions, then show verified curriculum options.</p>)}
          <button className="inline-flex min-h-11 items-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)] disabled:opacity-60" disabled={busy === "start"} onClick={() => void start()} type="button">
            {busy === "start" ? "Starting..." : "Start onboarding"}
          </button>
        </section>
      ) : (
        <>
          <section className={`${panelClassName} space-y-4`} aria-live="polite">
            {message("Abbot", <p>Current stage: {workspaceStatusLabel(onboarding.current_stage)}. Status: {workspaceStatusLabel(onboarding.status)}.</p>)}
            {onboarding.topic_query ? message("You", <p>I want to study {onboarding.topic_query}. {selectedIntentLabel}</p>) : null}
            {onboarding.selected_curriculum ? message("Abbot", <p>Selected governed curriculum: {onboarding.selected_curriculum.title} from {onboarding.selected_curriculum.authority}.</p>) : null}
          </section>

          {onboarding.status !== "COMPLETED" ? (
            <form className={`${panelClassName} space-y-4`} onSubmit={(event) => void submitContext(event)}>
              <label className="block space-y-2">
                <span className="text-sm font-medium">What would you like to study?</span>
                <input className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" defaultValue={onboarding.topic_query} name="topic_query" placeholder="Biology, economics, calculus..." />
              </label>
              <fieldset className="space-y-2">
                <legend className="text-sm font-medium">Why are you studying it?</legend>
                <div className="grid gap-2 md:grid-cols-3">
                  {(Object.keys(intentLabels) as OnboardingIntentChoice[]).map((choice) => (
                    <label className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-3 text-sm" key={choice}>
                      <input className="mr-2" defaultChecked={onboarding.study_intent === choice} name="study_intent" type="radio" value={choice} />
                      {intentLabels[choice]}
                    </label>
                  ))}
                </div>
              </fieldset>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-sm font-medium">Exam, qualification, or curriculum</span>
                  <input className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" defaultValue={onboarding.qualification_query} name="qualification_query" placeholder="Cambridge International A Level" />
                </label>
                <label className="block space-y-2">
                  <span className="text-sm font-medium">Awarding body</span>
                  <input className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" defaultValue={onboarding.awarding_body_query} name="awarding_body_query" placeholder="Cambridge, IB, local board..." />
                </label>
                <label className="block space-y-2">
                  <span className="text-sm font-medium">Jurisdiction</span>
                  <input className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" defaultValue={onboarding.jurisdiction_query} name="jurisdiction_query" placeholder="UK, South Africa, international..." />
                </label>
                <label className="block space-y-2">
                  <span className="text-sm font-medium">Level</span>
                  <input className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" defaultValue={onboarding.level_query} name="level_query" placeholder="A Level, Grade 12, beginner..." />
                </label>
              </div>
              <label className="block space-y-2">
                <span className="text-sm font-medium">Target or outcome</span>
                <textarea className="min-h-20 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" defaultValue={onboarding.target_description} name="target_description" placeholder="I want to prepare for my exam in November..." />
              </label>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="block space-y-2">
                  <span className="text-sm font-medium">Target date, if known</span>
                  <input className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" defaultValue={onboarding.target_date ?? ""} name="target_date" type="date" />
                </label>
                <label className="block space-y-2">
                  <span className="text-sm font-medium">Weekly study time</span>
                  <select className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm" defaultValue={onboarding.weekly_study_minutes ? String(onboarding.weekly_study_minutes / 60) : ""} name="weekly_hours">
                    <option value="">Choose approximate time</option>
                    <option value="1">About 1 hour/week</option>
                    <option value="3">About 3 hours/week</option>
                    <option value="5">About 5 hours/week</option>
                    <option value="10">About 10 hours/week</option>
                  </select>
                </label>
              </div>
              <div className="flex flex-wrap gap-3">
                <button className="inline-flex min-h-10 items-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium disabled:opacity-60" disabled={busy === "context"} type="submit">
                  {busy === "context" ? "Saving..." : "Save answers"}
                </button>
                <button className="inline-flex min-h-10 items-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)] disabled:opacity-60" disabled={Boolean(busy) || !onboarding.topic_query || !onboarding.study_intent} onClick={() => void resolve()} type="button">
                  {busy === "resolve" ? "Finding curricula..." : "Find governed curricula"}
                </button>
              </div>
            </form>
          ) : null}

          {candidates.length ? (
            <section className={`${panelClassName} space-y-4`}>
              {message("Abbot", <p>I found these verified curriculum options. Choose the one you are following; I won’t invent a curriculum if none fits.</p>)}
              <div className="grid gap-3">
                {candidates.map((candidate) => (
                  <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4" key={candidate.candidate_id}>
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-[0.08em] text-[var(--color-muted-foreground)]">Rank {candidate.rank}</p>
                        <h2 className="mt-1 text-lg font-semibold">{candidate.title}</h2>
                        <p className="text-sm text-[var(--color-muted-foreground)]">{candidate.authority} · {candidate.level || "Level not specified"} · {candidate.jurisdiction || "Global/unspecified"}</p>
                        <p className="mt-2 text-sm">{candidate.match_explanation}</p>
                      </div>
                      <button className="inline-flex min-h-10 items-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium disabled:opacity-60" disabled={!candidate.selectable || Boolean(busy)} onClick={() => void selectCandidate(candidate)} type="button">
                        {busy === candidate.candidate_id ? "Selecting..." : onboarding.selected_curriculum?.candidate_id === candidate.candidate_id ? "Selected" : "Select curriculum"}
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ) : onboarding.status === "AWAITING_CURRICULUM_SELECTION" ? (
            <EmptyState title="No governed curriculum match yet" description="Try adding an awarding body, level, jurisdiction, or broader topic. Abbot will not create an unverified syllabus." />
          ) : null}

          {onboarding.selected_curriculum ? (
            <section className={`${panelClassName} space-y-4`}>
              <h2 className="text-xl font-semibold">Onboarding summary</h2>
              <dl className="grid gap-3 text-sm md:grid-cols-2">
                <div><dt className="font-medium">Study topic</dt><dd>{onboarding.topic_query}</dd></div>
                <div><dt className="font-medium">Study intent</dt><dd>{selectedIntentLabel}</dd></div>
                <div><dt className="font-medium">Governed curriculum</dt><dd>{onboarding.selected_curriculum.title}</dd></div>
                <div><dt className="font-medium">Weekly availability</dt><dd>{weeklyHours || "Not set"}</dd></div>
              </dl>
              <p className="text-sm text-[var(--color-muted-foreground)]">This is not a grade, mastery decision, or exam-success prediction.</p>
              {onboarding.status === "COMPLETED" ? (
                <Link className="inline-flex min-h-10 items-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)]" href={onboarding.next_action.target_route}>
                  {onboarding.next_action.primary_cta_label}
                </Link>
              ) : (
                <button className="inline-flex min-h-10 items-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)] disabled:opacity-60" disabled={Boolean(busy) || onboarding.weekly_study_minutes === null} onClick={() => void complete()} type="button">
                  {busy === "complete" ? "Completing..." : "Complete onboarding"}
                </button>
              )}
            </section>
          ) : null}
        </>
      )}
    </section>
  );
}
