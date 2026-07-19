"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { createSubject, listSubjects, type Subject } from "@/services/academic";

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

export function SubjectDashboard() {
  const createFormRef = useRef<HTMLFormElement | null>(null);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function loadSubjects() {
    setLoading(true);
    setError(null);

    try {
      const nextSubjects = await listSubjects();
      setSubjects(nextSubjects);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load subjects right now.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSubjects();
  }, []);

  async function handleCreateSubject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = createFormRef.current ?? event.currentTarget;
    const formData = new FormData(form);
    const name = String(formData.get("name") || "").trim();
    const code = String(formData.get("code") || "").trim().toUpperCase();
    const description = String(formData.get("description") || "").trim();

    if (!name || !code) {
      setError("Subject name and code are required.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const subject = await createSubject({ name, code, description });
      form.reset();
      window.location.assign(`/dashboard/subjects/${subject.id}`);
    } catch (createError) {
      setError(createError instanceof Error ? createError.message : "Unable to create subject right now.");
    } finally {
      setSubmitting(false);
    }
  }

  const activeSubjects = subjects.filter((subject) => subject.is_active).length;

  return (
    <section className="space-y-8">
      <div className="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
        <section className={`${panelClassName} space-y-4`}>
          <div className="space-y-2">
            <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
              Subject dashboard
            </p>
            <h1 className="text-3xl font-semibold text-[var(--color-foreground)] sm:text-4xl">
              Organize your study spaces
            </h1>
            <p className="max-w-2xl text-sm text-[var(--color-muted-foreground)] sm:text-base">
              Create subjects, open them, and attach source material that the platform can process into
              structured learning content.
            </p>
          </div>

          <dl className="grid gap-3 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-3">
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Subjects</dt>
              <dd className="mt-1">{subjects.length}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Active</dt>
              <dd className="mt-1">{activeSubjects}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Next step</dt>
              <dd className="mt-1">Create or open a subject to upload a PDF or DOCX.</dd>
            </div>
          </dl>

          {error ? <ErrorState title="Subject dashboard issue" message={error} /> : null}
        </section>

        <aside className={panelClassName}>
          <form className="space-y-4" onSubmit={(event) => void handleCreateSubject(event)} ref={createFormRef}>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Create a subject</h2>
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Start with a short code and a plain-language title. After creation, we&apos;ll take you
                straight into the subject workspace.
              </p>
            </div>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Subject name</span>
              <input
                className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm"
                name="name"
                placeholder="Biology"
                required
                type="text"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Subject code</span>
              <input
                className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm uppercase"
                maxLength={12}
                name="code"
                placeholder="BIO101"
                required
                type="text"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Description</span>
              <textarea
                className="min-h-28 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm"
                name="description"
                placeholder="A place for notes, textbooks, and study resources."
              />
            </label>

            <button
              className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
              disabled={submitting}
              type="submit"
            >
              {submitting ? "Creating subject..." : "Create subject"}
            </button>
          </form>
        </aside>
      </div>

      <section className={panelClassName}>
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Your subjects</h2>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Open a subject to upload resources and track import status.
            </p>
          </div>
        </div>

        {loading ? (
          <LoadingState message="Loading subjects..." />
        ) : subjects.length === 0 ? (
          <EmptyState
            title="No subjects yet"
            description="Create your first subject, open it, and upload a PDF or DOCX resource to begin the first smoke-test flow."
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {subjects.map((subject) => (
              <Link
                className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-5 transition hover:border-[var(--color-primary)] hover:bg-[var(--color-accent)]/20"
                href={`/dashboard/subjects/${subject.id}`}
                key={subject.id}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
                      {subject.code}
                    </p>
                    <h3 className="mt-2 text-lg font-semibold text-[var(--color-foreground)]">{subject.name}</h3>
                  </div>
                  <span className="rounded-full border border-[var(--color-border)] px-2 py-1 text-xs text-[var(--color-muted-foreground)]">
                    {subject.is_active ? "Active" : "Archived"}
                  </span>
                </div>
                <p className="mt-3 text-sm text-[var(--color-muted-foreground)]">
                  {subject.description || "Open this subject to add source material and follow import progress."}
                </p>
              </Link>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}
