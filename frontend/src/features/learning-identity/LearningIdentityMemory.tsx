"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { useAuth } from "@/features/auth";
import {
  getLearningIdentitySummary,
  getLearningIdentityTimeline,
  listLearningIdentityProfiles,
  setLearningPreference,
  type LearningIdentitySummary,
  type LearningTimeline,
} from "@/services/learning-identity";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

const preferenceOptions = [
  { key: "EXPLANATION_MODE", label: "Explanation style", values: ["step_by_step", "examples_first", "concise", "story_based"] },
  { key: "TEACHING_PACE", label: "Teaching pace", values: ["gentle", "standard", "fast"] },
  { key: "SESSION_LENGTH", label: "Session length", values: [15, 25, 45, 60] },
];

function friendlyValue(value: string) {
  return value.replaceAll("_", " ");
}

export function LearningIdentityMemory() {
  const { status } = useAuth();
  const [profileId, setProfileId] = useState<string | null>(null);
  const [summary, setSummary] = useState<LearningIdentitySummary | null>(null);
  const [timeline, setTimeline] = useState<LearningTimeline | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingPreference, setSavingPreference] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status !== "authenticated") return;
    let active = true;
    const controller = new AbortController();
    async function load() {
      try {
        const profiles = await listLearningIdentityProfiles(controller.signal);
        if (!active) return;
        const currentProfileId = profiles[0]?.profile_id ?? null;
        setProfileId(currentProfileId);
        if (!currentProfileId) {
          setSummary(null);
          setTimeline(null);
          setLoading(false);
          return;
        }
        const [nextSummary, nextTimeline] = await Promise.all([
          getLearningIdentitySummary(currentProfileId, controller.signal),
          getLearningIdentityTimeline(currentProfileId, controller.signal),
        ]);
        if (!active) return;
        setSummary(nextSummary);
        setTimeline(nextTimeline);
        setError(null);
      } catch (loadError) {
        if (!active || controller.signal.aborted) return;
        setError(loadError instanceof Error ? loadError.message : "Unable to load what Abbot remembers.");
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => {
      active = false;
      controller.abort();
    };
  }, [status]);

  async function handlePreference(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!summary || !profileId) return;
    const form = event.currentTarget;
    const formData = new FormData(form);
    const preferenceKey = String(formData.get("preference_key") || "");
    const rawValue = String(formData.get("value") || "");
    const numeric = Number(rawValue);
    const value = Number.isFinite(numeric) && rawValue.trim() !== "" ? numeric : rawValue;
    setSavingPreference(true);
    setError(null);
    setNotice(null);
    try {
      await setLearningPreference(profileId, {
        expected_profile_version: summary.profile_version,
        preference_key: preferenceKey,
        value,
        idempotency_key: `preference:${profileId}:${preferenceKey}:${rawValue}`,
      });
      const [nextSummary, nextTimeline] = await Promise.all([getLearningIdentitySummary(profileId), getLearningIdentityTimeline(profileId)]);
      setSummary(nextSummary);
      setTimeline(nextTimeline);
      setNotice("Preference updated. Abbot will use it only where policy allows.");
      form.reset();
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Unable to update preference.");
    } finally {
      setSavingPreference(false);
    }
  }

  if (status !== "authenticated" || loading) {
    return <LoadingState message="Loading what Abbot remembers..." />;
  }

  if (error) {
    return <ErrorState title="We could not load your learning memory" message={error} />;
  }

  if (!summary) {
    return (
      <div className="space-y-4">
        <EmptyState
          title="Abbot does not have a learning profile yet"
          description="Create a self-study workspace and complete onboarding so Abbot can remember your learner-controlled study details."
        />
        <Link className="inline-flex rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-2 text-sm font-semibold text-white" href="/dashboard/self-study">Open self-study</Link>
      </div>
    );
  }

  return (
    <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6 lg:px-8">
      <header className={panelClassName}>
        <p className="text-sm font-semibold uppercase tracking-wide text-[var(--color-primary)]">Learning Identity</p>
        <h1 className="mt-2 text-3xl font-semibold text-[var(--color-foreground)]">What Abbot remembers</h1>
        <p className="mt-3 max-w-3xl text-sm text-[var(--color-muted-foreground)]">
          This is the learner-safe memory Abbot can use to personalize your self-study experience. It is not a grade,
          mastery record, transcript, or hidden diagnostic report.
        </p>
        <p className="mt-2 text-xs text-[var(--color-muted-foreground)]">Profile version {summary.profile_version}</p>
      </header>

      {notice ? <div className="rounded-[var(--radius-md)] border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">{notice}</div> : null}

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className={panelClassName}>
          <h2 className="text-xl font-semibold">Current learner-controlled details</h2>
          <div className="mt-4 grid gap-3">
            {summary.what_abbot_remembers.length ? (
              summary.what_abbot_remembers.map((item) => <MemoryCard key={item.id} item={item} />)
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">No current declarations are available yet.</p>
            )}
          </div>
        </div>

        <div className={panelClassName}>
          <h2 className="text-xl font-semibold">Study preferences</h2>
          <div className="mt-4 grid gap-3">
            {summary.study_preferences.length ? (
              summary.study_preferences.map((item) => <MemoryCard key={item.id} item={item} />)
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">Choose a preference when you want Abbot to adapt the experience.</p>
            )}
          </div>
          <form className="mt-5 grid gap-3" onSubmit={handlePreference}>
            <label className="text-sm font-medium" htmlFor="preference_key">Update a preference</label>
            <select className="rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2" id="preference_key" name="preference_key">
              {preferenceOptions.map((option) => (
                <option key={option.key} value={option.key}>{option.label}</option>
              ))}
            </select>
            <label className="text-sm font-medium" htmlFor="preference_value">Value</label>
            <select className="rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 py-2" id="preference_value" name="value">
              {preferenceOptions.flatMap((option) =>
                option.values.map((value) => (
                  <option key={`${option.key}:${value}`} value={String(value)}>
                    {option.label}: {friendlyValue(String(value))}
                  </option>
                )),
              )}
            </select>
            <button className="rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60" disabled={savingPreference} type="submit">
              {savingPreference ? "Saving preference..." : "Update preference"}
            </button>
            <p className="text-xs text-[var(--color-muted-foreground)]">Defaults stay separate from choices you explicitly make. Preferences are not facts about you.</p>
          </form>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className={panelClassName}>
          <h2 className="text-xl font-semibold">Recent learning activity</h2>
          <div className="mt-4 grid gap-3">
            {summary.recent_learning_activity.length ? (
              summary.recent_learning_activity.map((item) => <MemoryCard key={item.id} item={item} />)
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">No eligible activity has been added to Abbot’s memory yet.</p>
            )}
          </div>
        </div>
        <div className={panelClassName}>
          <h2 className="text-xl font-semibold">Your journey</h2>
          <ol className="mt-4 grid gap-3">
            {(timeline?.entries ?? []).length ? (
              timeline!.entries.map((entry) => (
                <li key={entry.timeline_id} className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
                  <p className="text-sm font-semibold">{entry.title}</p>
                  <p className="mt-1 text-sm text-[var(--color-muted-foreground)]">{entry.description}</p>
                  <p className="mt-2 text-xs text-[var(--color-muted-foreground)]">{entry.source_summary}</p>
                </li>
              ))
            ) : (
              <p className="text-sm text-[var(--color-muted-foreground)]">Your timeline will appear as Abbot records governed, learner-safe changes.</p>
            )}
          </ol>
        </div>
      </section>
    </main>
  );
}

function MemoryCard({ item }: { item: LearningIdentitySummary["what_abbot_remembers"][number] }) {
  return (
    <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold">{item.label}</h3>
          <p className="mt-1 text-sm capitalize text-[var(--color-foreground)]">{friendlyValue(item.value)}</p>
          <p className="mt-2 text-xs text-[var(--color-muted-foreground)]">{item.source_summary}</p>
        </div>
        <span className="rounded-full bg-[var(--color-accent)] px-3 py-1 text-xs font-medium text-[var(--color-accent-foreground)]">
          {item.currently_used ? "Used by Abbot" : item.status.toLowerCase()}
        </span>
      </div>
    </article>
  );
}
