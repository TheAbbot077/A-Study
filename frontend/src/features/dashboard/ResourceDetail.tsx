"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import {
  getLearningResource,
  getSubject,
  listConceptsForResource,
  listSectionsForResource,
  type ContentConcept,
  type ContentSection,
  type LearningResource,
  type Subject,
} from "@/services/academic";
import { deleteImportJob, listImportJobsForResource, type ContentImportJob } from "@/services/content-intelligence";
import { listConceptBrowserStates, startOrResumeConcept, type ConceptBrowserStatus } from "@/services/learning";

type ResourceDetailProps = {
  resourceId: string;
};

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

function latestJob(jobs: ContentImportJob[]) {
  return jobs[0] ?? null;
}

function isLowConfidenceImport(job: ContentImportJob | null) {
  if (!job) {
    return false;
  }

  const values = [
    job.extraction_confidence,
    job.structural_confidence,
    job.section_confidence,
    job.concept_confidence,
  ].filter((value): value is number => typeof value === "number");

  return values.some((value) => value < 0.8);
}

function presentConceptStatus(status: ConceptBrowserStatus["status"]) {
  switch (status) {
    case "available":
      return { label: "Available", tone: "available" as const };
    case "in_progress":
      return { label: "In progress", tone: "progress" as const };
    case "mastered":
      return { label: "Mastered", tone: "mastered" as const };
    case "needs_remediation":
      return { label: "Needs remediation", tone: "warning" as const };
    default:
      return { label: "Locked", tone: "locked" as const };
  }
}

function statusBadgeClassName(tone: "available" | "progress" | "mastered" | "warning" | "locked") {
  switch (tone) {
    case "available":
      return "border-[var(--color-primary)] text-[var(--color-primary)]";
    case "progress":
      return "border-[var(--color-warning)] text-[var(--color-warning)]";
    case "mastered":
      return "border-[var(--color-success)] text-[var(--color-success)]";
    case "warning":
      return "border-[var(--color-danger)] text-[var(--color-danger)]";
    default:
      return "border-[var(--color-border)] text-[var(--color-muted-foreground)]";
  }
}

export function ResourceDetail({ resourceId }: ResourceDetailProps) {
  const router = useRouter();
  const [resource, setResource] = useState<LearningResource | null>(null);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [sections, setSections] = useState<ContentSection[]>([]);
  const [concepts, setConcepts] = useState<ContentConcept[]>([]);
  const [conceptStates, setConceptStates] = useState<Record<string, ConceptBrowserStatus>>({});
  const [importJob, setImportJob] = useState<ContentImportJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingConceptId, setStartingConceptId] = useState<string | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function loadResourceData() {
      setLoading(true);
      setError(null);

      try {
        const nextResource = await getLearningResource(resourceId);
        const [nextSubject, nextSections, nextConcepts, nextStates, nextJobs] = await Promise.all([
          getSubject(nextResource.subject),
          listSectionsForResource(resourceId),
          listConceptsForResource(resourceId),
          listConceptBrowserStates(resourceId),
          listImportJobsForResource(resourceId),
        ]);

        if (!isMounted) {
          return;
        }

        setResource(nextResource);
        setSubject(nextSubject);
        setSections(nextSections);
        setConcepts(nextConcepts);
        setConceptStates(Object.fromEntries(nextStates.map((state) => [state.concept_id, state])));
        setImportJob(latestJob(nextJobs));
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : "Unable to load this resource right now.");
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    }

    void loadResourceData();

    return () => {
      isMounted = false;
    };
  }, [resourceId]);

  const conceptsBySection = useMemo(() => {
    const grouped = new Map<string, ContentConcept[]>();
    for (const concept of concepts) {
      const current = grouped.get(concept.content_section) ?? [];
      current.push(concept);
      grouped.set(concept.content_section, current);
    }
    return grouped;
  }, [concepts]);

  const firstAvailableConcept = useMemo(() => {
    return concepts.find((concept) => conceptStates[concept.id]?.can_start_or_resume) ?? null;
  }, [conceptStates, concepts]);

  const conceptProgressSummary = useMemo(() => {
    const summary = {
      available: 0,
      in_progress: 0,
      mastered: 0,
      needs_remediation: 0,
      locked: 0,
    };

    for (const concept of concepts) {
      const status = conceptStates[concept.id]?.status ?? "locked";
      summary[status] += 1;
    }

    return summary;
  }, [conceptStates, concepts]);

  async function handleStartOrResume(conceptId: string) {
    setStartingConceptId(conceptId);
    setError(null);

    try {
      const session = await startOrResumeConcept(conceptId);
      router.push(`/dashboard/concepts/${conceptId}?session=${encodeURIComponent(session.id)}`);
    } catch (actionError) {
      setError(actionError instanceof Error ? actionError.message : "Unable to open this concept right now.");
    } finally {
      setStartingConceptId(null);
    }
  }

  async function handleDeleteImport() {
    if (!importJob || !subject) {
      return;
    }

    setDeleting(true);
    setError(null);
    try {
      await deleteImportJob(importJob.id);
      router.push(`/dashboard/subjects/${subject.id}`);
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Unable to delete this document right now.");
    } finally {
      setDeleting(false);
    }
  }

  if (loading) {
    return <LoadingState message="Loading resource outline..." />;
  }

  if (error && !resource) {
    return <ErrorState title="Resource unavailable" message={error} />;
  }

  if (!resource) {
    return <ErrorState title="Resource unavailable" message="We couldn't find this resource." />;
  }

  const lowConfidence = isLowConfidenceImport(importJob);
  const readyForLearning = resource.resource_ready_for_learning || importJob?.resource_ready_for_learning;

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
        ) : (
          <span>Subject</span>
        )}
        <span>/</span>
        <span className="text-[var(--color-foreground)]">{resource.title}</span>
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.2fr,0.8fr]">
        <section className={`${panelClassName} space-y-4`}>
          <div className="space-y-2">
            <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
              {resource.resource_type}
            </p>
            <h1 className="text-3xl font-semibold text-[var(--color-foreground)] sm:text-4xl">{resource.title}</h1>
            <p className="max-w-3xl text-sm text-[var(--color-muted-foreground)] sm:text-base">
              {resource.description || resource.source_label || "Browse the imported outline and move into the next concept from here."}
            </p>
          </div>

          <dl className="grid gap-4 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-3">
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Sections</dt>
              <dd className="mt-1">{sections.length}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Concepts</dt>
              <dd className="mt-1">{concepts.length}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Import status</dt>
              <dd className="mt-1 capitalize">{importJob?.status ?? "unknown"}</dd>
            </div>
          </dl>

          {importJob && importJob.status !== "pending" && importJob.status !== "processing" ? (
            <div className="flex flex-wrap gap-3">
              <button
                className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-danger)]/60 px-4 text-sm font-medium text-[var(--color-danger)] transition hover:bg-[var(--color-danger)]/10"
                onClick={() => setShowDeleteConfirm((current) => !current)}
                type="button"
              >
                {importJob.status === "failed" || importJob.status === "cancelled" ? "Delete failed upload" : "Delete document"}
              </button>
            </div>
          ) : null}

          <dl className="grid gap-3 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-2 xl:grid-cols-5">
            <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <dt className="font-medium text-[var(--color-foreground)]">Available</dt>
              <dd className="mt-1">{conceptProgressSummary.available}</dd>
            </div>
            <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <dt className="font-medium text-[var(--color-foreground)]">In progress</dt>
              <dd className="mt-1">{conceptProgressSummary.in_progress}</dd>
            </div>
            <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <dt className="font-medium text-[var(--color-foreground)]">Mastered</dt>
              <dd className="mt-1">{conceptProgressSummary.mastered}</dd>
            </div>
            <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <dt className="font-medium text-[var(--color-foreground)]">Needs remediation</dt>
              <dd className="mt-1">{conceptProgressSummary.needs_remediation}</dd>
            </div>
            <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <dt className="font-medium text-[var(--color-foreground)]">Locked</dt>
              <dd className="mt-1">{conceptProgressSummary.locked}</dd>
            </div>
          </dl>

          {error ? <ErrorState title="Resource action issue" message={error} /> : null}
          {showDeleteConfirm && importJob ? (
            <div className="rounded-[var(--radius-md)] border border-[var(--color-danger)]/50 p-4">
              <div className="space-y-3">
                <h2 className="text-base font-semibold text-[var(--color-foreground)]">
                  {importJob.status === "failed" || importJob.status === "cancelled" ? "Delete failed upload" : "Delete document"}
                </h2>
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  This removes the uploaded file, processing history, and generated outline for {resource.title}.
                </p>
                <div className="flex flex-wrap gap-3">
                  <button
                    className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-danger)] px-4 text-sm font-semibold text-white transition hover:brightness-105 disabled:opacity-70"
                    disabled={deleting}
                    onClick={() => void handleDeleteImport()}
                    type="button"
                  >
                    {deleting ? "Deleting..." : "Confirm deletion"}
                  </button>
                  <button
                    className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
                    onClick={() => setShowDeleteConfirm(false)}
                    type="button"
                  >
                    Keep document
                  </button>
                </div>
              </div>
            </div>
          ) : null}
        </section>

        <aside className={`${panelClassName} space-y-4`}>
          <div className="space-y-2">
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Next available concept</h2>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Start with the first concept the backend currently marks as available for study.
            </p>
          </div>

          {firstAvailableConcept ? (
            <div className="space-y-4 rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
              <div>
                <p className="text-sm text-[var(--color-muted-foreground)]">Recommended next concept</p>
                <h3 className="mt-1 text-lg font-semibold text-[var(--color-foreground)]">{firstAvailableConcept.title}</h3>
              </div>
              <button
                className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
                disabled={startingConceptId === firstAvailableConcept.id}
                onClick={() => void handleStartOrResume(firstAvailableConcept.id)}
                type="button"
              >
                {startingConceptId === firstAvailableConcept.id
                  ? "Opening concept..."
                  : (conceptStates[firstAvailableConcept.id]?.action_label ?? "Open concept")}
              </button>
            </div>
          ) : (
            <EmptyState
              title="No concept ready yet"
              description={
                importJob?.status === "pending" || importJob?.status === "processing"
                  ? "Import is still processing. Come back once sections and concepts finish loading."
                  : "This resource does not currently have an available concept to begin from this screen."
              }
            />
          )}
        </aside>
      </div>

      {lowConfidence ? (
        <section className="rounded-[var(--radius-lg)] border border-[var(--color-warning)]/70 bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]">
          <div className="space-y-2">
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Low-confidence import warning</h2>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              This outline was imported with lower confidence signals. Treat section boundaries and concept extraction as provisional, and compare what you see here against the source document during the smoke test.
            </p>
          </div>
          <dl className="mt-4 grid gap-3 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-2 xl:grid-cols-4">
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Extraction</dt>
              <dd className="mt-1">{importJob?.extraction_confidence?.toFixed(2) ?? "n/a"}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Structure</dt>
              <dd className="mt-1">{importJob?.structural_confidence?.toFixed(2) ?? "n/a"}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Sections</dt>
              <dd className="mt-1">{importJob?.section_confidence?.toFixed(2) ?? "n/a"}</dd>
            </div>
            <div>
              <dt className="font-medium text-[var(--color-foreground)]">Concepts</dt>
              <dd className="mt-1">{importJob?.concept_confidence?.toFixed(2) ?? "n/a"}</dd>
            </div>
          </dl>
        </section>
      ) : null}

      {importJob?.validation_findings?.length ? (
        <section className={panelClassName}>
          <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Import warnings</h2>
          <ul className="mt-4 space-y-2 text-sm text-[var(--color-muted-foreground)]">
            {importJob.validation_findings.map((finding) => (
              <li key={finding.id}>
                <span className="font-medium capitalize text-[var(--color-foreground)]">{finding.severity}:</span>{" "}
                {finding.message}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className={panelClassName}>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Resource outline</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Sections and concepts are shown in backend sequence order.
          </p>
        </div>

        {!readyForLearning ? (
          <EmptyState
            title="Resource not ready for learning yet"
            description={
              importJob?.status === "failed"
                ? "This upload failed before a learning-ready outline could be created. Return to the subject page to retry or delete it."
                : importJob?.status === "pending" || importJob?.status === "processing"
                  ? "Import is still running. This outline will unlock when the backend marks the resource ready for learning."
                  : "The backend has not marked this resource ready for learning yet."
            }
          />
        ) : sections.length === 0 || concepts.length === 0 ? (
          <EmptyState
            title="No concepts available yet"
            description={
              importJob?.status === "failed"
                ? "This import failed before a browsable outline could be created. Return to the subject page to retry and review the failure details."
                : importJob?.status === "pending" || importJob?.status === "processing"
                  ? "This resource is still being processed. Refresh after processing completes to browse sections and concepts."
                  : "This resource has not produced a browsable concept outline yet. Review the source file and import warnings."
            }
          />
        ) : (
          <div className="space-y-4">
            {sections.map((section) => {
              const sectionConcepts = conceptsBySection.get(section.id) ?? [];

              return (
                <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-5" key={section.id}>
                  <div className="space-y-1">
                    <p className="text-sm font-medium text-[var(--color-primary)]">Section {section.sequence_number}</p>
                    <h3 className="text-xl font-semibold text-[var(--color-foreground)]">{section.title}</h3>
                    <p className="text-sm text-[var(--color-muted-foreground)]">
                      {section.description || "Imported chapter or section content."}
                    </p>
                  </div>

                  {sectionConcepts.length === 0 ? (
                    <div className="mt-4 rounded-[var(--radius-md)] border border-dashed border-[var(--color-border)] p-4">
                      <EmptyState
                        title="No concepts in this section"
                        description="This section was imported without concept extraction results."
                      />
                    </div>
                  ) : (
                    <div className="mt-5 space-y-3">
                      {sectionConcepts.map((concept) => {
                        const state = conceptStates[concept.id] ?? {
                          concept_id: concept.id,
                          status: "locked" as const,
                          can_start_or_resume: false,
                        };
                        const presentation = presentConceptStatus(state.status);

                        return (
                          <div
                            className="flex flex-col gap-4 rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 lg:flex-row lg:items-start lg:justify-between"
                            id={`concept-${concept.id}`}
                            key={concept.id}
                          >
                            <div className="space-y-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-sm font-medium text-[var(--color-primary)]">
                                  Concept {concept.sequence_number}
                                </span>
                                <span
                                  className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${statusBadgeClassName(presentation.tone)}`.trim()}
                                >
                                  {presentation.label}
                                </span>
                              </div>
                              <h4 className="text-lg font-semibold text-[var(--color-foreground)]">{concept.title}</h4>
                              <p className="text-sm text-[var(--color-muted-foreground)]">
                                {concept.description || concept.learning_objective || "Imported concept awaiting deeper learning interaction."}
                              </p>
                            </div>

                            <div className="flex shrink-0 flex-wrap items-center gap-3">
                              <Link
                                className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
                                href={`/dashboard/concepts/${concept.id}`}
                              >
                                View concept
                              </Link>

                              {state.can_start_or_resume ? (
                                <button
                                  className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
                                  disabled={startingConceptId === concept.id}
                                  onClick={() => void handleStartOrResume(concept.id)}
                                  type="button"
                                >
                                  {startingConceptId === concept.id ? "Opening..." : (state.action_label ?? "Open concept")}
                                </button>
                              ) : null}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </section>
  );
}
