"use client";

import Link from "next/link";
import { type FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { EmptyState, ErrorState, LoadingState } from "@/components/feedback";
import { createLearningResource, getSubject, listResourcesForSubject, listSubjects, type LearningResource, type Subject } from "@/services/academic";
import {
  createImportJob,
  deleteImportJob,
  getImportJob,
  authoritativeProcessingStatus,
  isActivelyProcessing,
  isPollingTerminal,
  isProcessingFailed,
  isReadyForTeaching,
  isReviewRequired,
  listImportJobsForResource,
  processingStatusLabel,
  retryImportJob,
  type ContentImportJob,
} from "@/services/content-intelligence";
import { uploadStoredFile } from "@/services/storage";

type SubjectDetailProps = {
  subjectId: string;
};

type ImportStatusTone = "processing" | "review" | "completed" | "warning" | "failed" | "cancelled";

type ImportPresentation = {
  label: string;
  tone: ImportStatusTone;
};

type PendingDelete = {
  jobId: string;
  resourceId: string;
  resourceTitle: string;
  label: string;
};

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

function getLatestImportJob(jobs: ContentImportJob[]): ContentImportJob | null {
  return jobs[0] ?? null;
}

function presentImportStatus(job: ContentImportJob | null): ImportPresentation {
  if (!job) {
    return { label: "Awaiting import", tone: "processing" };
  }

  if (isReviewRequired(job)) {
    return { label: "Ready for review", tone: "review" };
  }

  if (isActivelyProcessing(job)) {
    return { label: processingStatusLabel(job), tone: "processing" };
  }

  if (isProcessingFailed(job)) {
    return { label: "Processing failed", tone: "failed" };
  }

  if (isReadyForTeaching(job)) {
    return { label: "Ready for teaching", tone: "completed" };
  }

  const authoritativeStatus = authoritativeProcessingStatus(job);
  if (authoritativeStatus === "cancelled" || authoritativeStatus === "deleted") {
    return { label: processingStatusLabel(job), tone: "cancelled" };
  }

  const status = job.status_detail ?? job.status;

  if (status === "completed_with_warnings" || (status === "completed" && (job.validation_findings?.length ?? 0) > 0)) {
    return { label: "Completed with warnings", tone: "warning" };
  }

  if (status === "completed") {
    return { label: "Completed", tone: "completed" };
  }

  if (status === "cancelled") {
    return { label: "Processing cancelled", tone: "cancelled" };
  }

  return { label: "Failed", tone: "failed" };
}

function processingStageLabel(job: ContentImportJob | null) {
  if (!job) {
    return null;
  }
  return processingStatusLabel(job);
}

function failureReason(job: ContentImportJob | null) {
  if (!job) {
    return null;
  }
  const details = job.failure_details;
  if (details && typeof details.failure_reason === "string" && details.failure_reason.trim()) {
    return details.failure_reason;
  }
  return job.error_message || null;
}

function statusBadgeClassName(tone: ImportStatusTone) {
  switch (tone) {
    case "completed":
      return "border-[var(--color-success)] text-[var(--color-success)]";
    case "warning":
      return "border-[var(--color-warning)] text-[var(--color-warning)]";
    case "review":
      return "border-[var(--color-primary)] text-[var(--color-primary)]";
    case "cancelled":
      return "border-[var(--color-border)] text-[var(--color-muted-foreground)]";
    case "failed":
      return "border-[var(--color-danger)] text-[var(--color-danger)]";
    default:
      return "border-[var(--color-border)] text-[var(--color-muted-foreground)]";
  }
}

export function SubjectDetail({ subjectId }: SubjectDetailProps) {
  const uploadFormRef = useRef<HTMLFormElement | null>(null);
  const [subject, setSubject] = useState<Subject | null>(null);
  const [resources, setResources] = useState<LearningResource[]>([]);
  const [jobsByResource, setJobsByResource] = useState<Record<string, ContentImportJob | null>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null);

  async function loadSubjectData() {
    setLoading(true);
    setError(null);

    try {
      let nextSubject: Subject | null = null;
      try {
        nextSubject = await getSubject(subjectId);
      } catch (loadSubjectError) {
        if (loadSubjectError instanceof Error && "status" in loadSubjectError && (loadSubjectError as { status?: number }).status === 404) {
          const subjects = await listSubjects();
          nextSubject = subjects.find((item) => item.id === subjectId) ?? null;
          if (!nextSubject) {
            throw loadSubjectError;
          }
        } else {
          throw loadSubjectError;
        }
      }

      setSubject(nextSubject);
      const nextResources = await listResourcesForSubject(subjectId);
      setResources(nextResources);

      const settledJobEntries = await Promise.allSettled(
        nextResources.map(async (resource) => {
          const jobs = await listImportJobsForResource(resource.id);
          return [resource.id, getLatestImportJob(jobs)] as const;
        }),
      );
      const jobEntries = settledJobEntries
        .filter((result): result is PromiseFulfilledResult<readonly [string, ContentImportJob | null]> => result.status === "fulfilled")
        .map((result) => result.value);
      const failedJobLoads = settledJobEntries.some((result) => result.status === "rejected");

      setJobsByResource(Object.fromEntries(jobEntries));
      if (failedJobLoads) {
        setError("The subject loaded, but some import status details could not be retrieved right now.");
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Unable to load this subject right now.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSubjectData();
  }, [subjectId]);

  async function pollImportJob(importJobId: string, resourceId: string) {
    let nextJob = await getImportJob(importJobId);

    while (!isPollingTerminal(nextJob)) {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      nextJob = await getImportJob(importJobId);
    }

    setJobsByResource((current) => ({
      ...current,
      [resourceId]: nextJob,
    }));
  }

  async function handleUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = uploadFormRef.current ?? event.currentTarget;
    const formData = new FormData(form);
    const title = String(formData.get("title") || "").trim();
    const description = String(formData.get("description") || "").trim();
    const file = formData.get("file");

    if (!(file instanceof File) || file.size === 0) {
      setError("Please choose a PDF or DOCX file to upload.");
      return;
    }

    const filename = file.name.toLowerCase();
    if (!filename.endsWith(".pdf") && !filename.endsWith(".docx")) {
      setError("Only PDF and DOCX files are supported right now.");
      return;
    }

    setUploading(true);
    setError(null);

    try {
      const storedFile = await uploadStoredFile(file);
      const resource = await createLearningResource({
        subject: subjectId,
        stored_file: storedFile.id,
        title: title || file.name.replace(/\.(pdf|docx)$/i, ""),
        description,
        resource_type: "notes",
        source_label: file.name,
      });
      const job = await createImportJob(resource.id);

      setResources((current) => [resource, ...current]);
      setJobsByResource((current) => ({
        ...current,
        [resource.id]: job,
      }));
      form.reset();

      if (isActivelyProcessing(job)) {
        await pollImportJob(job.id, resource.id);
      } else {
        await loadSubjectData();
      }
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Unable to upload this resource right now.");
    } finally {
      setUploading(false);
    }
  }

  async function handleRetry(resourceId: string, jobId: string) {
    setError(null);

    try {
      const retriedJob = await retryImportJob(jobId);
      setJobsByResource((current) => ({
        ...current,
        [resourceId]: retriedJob,
      }));
      await pollImportJob(retriedJob.id, resourceId);
      await loadSubjectData();
    } catch (retryError) {
      setError(retryError instanceof Error ? retryError.message : "Unable to retry this import right now.");
    }
  }

  async function handleDeleteImport() {
    if (!pendingDelete) {
      return;
    }

    setDeletingJobId(pendingDelete.jobId);
    setError(null);

    try {
      await deleteImportJob(pendingDelete.jobId);
      setPendingDelete(null);
      await loadSubjectData();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Unable to delete this upload right now.");
    } finally {
      setDeletingJobId(null);
    }
  }

  const resourceCards = useMemo(
    () =>
      resources.map((resource) => {
        const job = jobsByResource[resource.id] ?? null;
        const presentation = presentImportStatus(job);
        const authoritativeStatus = authoritativeProcessingStatus(job);
        const reviewRequired = isReviewRequired(job);
        const readyForLearning = isReadyForTeaching(job) || (!authoritativeStatus && Boolean(resource.resource_ready_for_learning || job?.resource_ready_for_learning));
        const canDelete = Boolean(job && !isActivelyProcessing(job));
        const hasFailedImportAction = isProcessingFailed(job);
        const deleteLabel = job?.status === "failed" || job?.status === "cancelled" ? "Delete failed upload" : "Delete document";
        const failure = failureReason(job);
        const activeStageLabel = processingStageLabel(job);
        const progress = typeof job?.processing_progress === "number" ? job.processing_progress : null;
        const attempt = typeof job?.processing_attempt === "number" ? job.processing_attempt : null;

        return (
          <article className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-5" key={resource.id}>
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-[var(--color-foreground)]">{resource.title}</h3>
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  {resource.source_label || resource.description || "Source material uploaded for content processing."}
                </p>
              </div>
              <span
                className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium ${statusBadgeClassName(presentation.tone)}`.trim()}
              >
                {presentation.label}
              </span>
            </div>

            <dl className="mt-4 grid gap-3 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-3">
              <div>
                <dt className="font-medium text-[var(--color-foreground)]">Resource status</dt>
                <dd className="mt-1 capitalize">{resource.status}</dd>
              </div>
              <div>
                <dt className="font-medium text-[var(--color-foreground)]">Import format</dt>
                <dd className="mt-1 uppercase">{job?.format_type ?? "Pending"}</dd>
              </div>
              <div>
                <dt className="font-medium text-[var(--color-foreground)]">Warnings</dt>
                <dd className="mt-1">{job?.processing_warning_count ?? job?.validation_findings?.length ?? 0}</dd>
              </div>
            </dl>

            {activeStageLabel ? (
              <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 text-sm text-[var(--color-muted-foreground)]">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <p>
                    <span className="font-medium text-[var(--color-foreground)]">Current stage:</span>{" "}
                    {activeStageLabel}
                  </p>
                  {attempt ? (
                    <p>
                      <span className="font-medium text-[var(--color-foreground)]">Attempt:</span> {attempt}
                    </p>
                  ) : null}
                </div>
                {progress !== null ? (
                  <div className="mt-3 space-y-2">
                    <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--color-accent)]/30">
                      <div
                        aria-hidden="true"
                        className="h-full rounded-full bg-[var(--color-primary)] transition-[width]"
                        style={{ width: `${Math.max(0, Math.min(progress, 100))}%` }}
                      />
                    </div>
                    <p>{reviewRequired ? `${progress}% complete — publication pending review` : `${progress}% complete`}</p>
                  </div>
                ) : null}
              </div>
            ) : null}

            {reviewRequired ? (
              <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-primary)]/50 p-4 text-sm">
                <h4 className="font-semibold text-[var(--color-foreground)]">Ready for review</h4>
                <p className="mt-2 text-[var(--color-muted-foreground)]">
                  Processing completed successfully, but this document needs academic review before it can be published.
                </p>
                {job?.proposal ? (
                  <dl className="mt-3 grid gap-2 text-[var(--color-muted-foreground)] sm:grid-cols-3">
                    <div><dt>Proposed sections</dt><dd className="font-medium text-[var(--color-foreground)]">{job.proposal.proposed_section_count}</dd></div>
                    <div><dt>Proposed concepts</dt><dd className="font-medium text-[var(--color-foreground)]">{job.proposal.proposed_concept_count}</dd></div>
                    <div><dt>Confidence</dt><dd className="font-medium text-[var(--color-foreground)]">{(job.proposal.confidence * 100).toFixed(1)}%</dd></div>
                  </dl>
                ) : null}
                <p className="mt-3 text-[var(--color-muted-foreground)]">Review tools coming next.</p>
              </div>
            ) : null}

            {job?.validation_findings?.length ? (
              <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-warning)]/60 p-4">
                <h4 className="text-sm font-semibold text-[var(--color-foreground)]">Validation warnings</h4>
                <ul className="mt-2 space-y-2 text-sm text-[var(--color-muted-foreground)]">
                  {job.validation_findings.map((finding) => (
                    <li key={finding.id}>
                      <span className="font-medium capitalize text-[var(--color-foreground)]">{finding.severity}:</span>{" "}
                      {finding.message}
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}

            {hasFailedImportAction ? (
              <div className="mt-4 space-y-3">
                <p className="text-sm text-[var(--color-danger)]">
                  {job.error_message || "The import failed before content could be processed."}
                </p>
                {failure && failure !== job.error_message ? (
                  <p className="text-sm text-[var(--color-muted-foreground)]">Failure reason: {failure}</p>
                ) : null}
                <p className="text-sm text-[var(--color-muted-foreground)]">
                  Try the retry action first. If it fails again, confirm the file opens locally, is really
                  a PDF or DOCX, and contains selectable text or stable document structure.
                </p>
                <div className="flex flex-wrap gap-3">
                  {job.can_retry_processing ?? true ? (
                    <button
                      className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
                      onClick={() => void handleRetry(resource.id, job.id)}
                      type="button"
                    >
                      Retry import
                    </button>
                  ) : null}
                  <button
                    className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-danger)]/60 px-3 text-sm font-medium text-[var(--color-danger)] transition hover:bg-[var(--color-danger)]/10"
                    onClick={() =>
                      setPendingDelete({
                        jobId: job.id,
                        resourceId: resource.id,
                        resourceTitle: resource.title,
                        label: deleteLabel,
                      })
                    }
                    type="button"
                  >
                    {deleteLabel}
                  </button>
                </div>
              </div>
            ) : null}

            {job && isActivelyProcessing(job) ? (
              <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 text-sm text-[var(--color-muted-foreground)]">
                Import is still running. The resource outline will unlock as soon as the backend marks this
                document ready for learning.
              </div>
            ) : null}

            <div className="mt-4 flex flex-wrap items-center gap-3">
              {readyForLearning ? (
                <Link
                  className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
                  href={`/dashboard/resources/${resource.id}`}
                >
                  Open resource outline
                </Link>
              ) : (
                <span className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 text-sm font-medium text-[var(--color-muted-foreground)]">
                  {reviewRequired ? "Academic review required before study can begin" : "Outline available after processing completes"}
                </span>
              )}
              {canDelete && job && !hasFailedImportAction ? (
                <button
                  className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-danger)]/60 px-3 text-sm font-medium text-[var(--color-danger)] transition hover:bg-[var(--color-danger)]/10"
                  onClick={() =>
                    setPendingDelete({
                      jobId: job.id,
                      resourceId: resource.id,
                      resourceTitle: resource.title,
                      label: deleteLabel,
                    })
                  }
                  type="button"
                >
                  {deleteLabel}
                </button>
              ) : null}
            </div>
          </article>
        );
      }),
    [jobsByResource, resources],
  );

  const importSummary = useMemo(() => {
    let processing = 0;
    let completed = 0;
    let review = 0;
    let warnings = 0;
    let failed = 0;
    let cancelled = 0;

    for (const resource of resources) {
      const job = jobsByResource[resource.id] ?? null;
      const presentation = presentImportStatus(job);
      if (presentation.tone === "processing") {
        processing += 1;
      } else if (presentation.tone === "review") {
        review += 1;
      } else if (presentation.tone === "completed") {
        completed += 1;
      } else if (presentation.tone === "warning") {
        warnings += 1;
      } else if (presentation.tone === "failed") {
        failed += 1;
      } else if (presentation.tone === "cancelled") {
        cancelled += 1;
      }
    }

    return { processing, review, completed, warnings, failed, cancelled };
  }, [jobsByResource, resources]);

  if (loading) {
    return <LoadingState message="Loading subject workspace..." />;
  }

  if (error && !subject) {
    return <ErrorState title="Subject unavailable" message={error} />;
  }

  if (!subject) {
    return <ErrorState title="Subject unavailable" message="We couldn't find this subject." />;
  }

  return (
    <section className="space-y-8">
      <div className="flex flex-wrap items-center gap-3 text-sm text-[var(--color-muted-foreground)]">
        <Link className="hover:text-[var(--color-foreground)]" href="/dashboard">
          Dashboard
        </Link>
        <span>/</span>
        <span className="text-[var(--color-foreground)]">{subject.name}</span>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr,0.9fr]">
        <section className={`${panelClassName} space-y-4`}>
          <div className="space-y-2">
            <p className="text-sm font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
              {subject.code}
            </p>
            <h1 className="text-3xl font-semibold text-[var(--color-foreground)] sm:text-4xl">{subject.name}</h1>
            <p className="max-w-2xl text-sm text-[var(--color-muted-foreground)] sm:text-base">
              {subject.description || "Upload source material for this subject and follow content intelligence import progress here."}
            </p>
          </div>

          {error ? <ErrorState title="Upload flow issue" message={error} /> : null}
        </section>

        <aside className={panelClassName}>
          <form className="space-y-4" onSubmit={(event) => void handleUpload(event)} ref={uploadFormRef}>
            <div className="space-y-1">
              <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Upload resource</h2>
              <p className="text-sm text-[var(--color-muted-foreground)]">
                Add a PDF or DOCX source file and let Content Intelligence process it.
              </p>
            </div>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Resource title</span>
              <input
                className="w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm"
                name="title"
                placeholder="Unit 1 textbook notes"
                type="text"
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">Description</span>
              <textarea
                className="min-h-24 w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm"
                name="description"
                placeholder="Optional context about this upload."
              />
            </label>

            <label className="block space-y-2">
              <span className="text-sm font-medium text-[var(--color-foreground)]">File</span>
              <input
                accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="block w-full rounded-[var(--radius-md)] border border-[var(--color-border)] bg-transparent px-4 py-3 text-sm"
                name="file"
                required
                type="file"
              />
            </label>

            <button
              className="inline-flex min-h-11 w-full items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-primary)] px-4 py-3 text-sm font-semibold text-[var(--color-primary-foreground)] transition hover:brightness-105 disabled:opacity-70"
              disabled={uploading}
              type="submit"
            >
              {uploading ? "Uploading and processing..." : "Upload PDF or DOCX"}
            </button>
          </form>
        </aside>
      </div>

      <section className={panelClassName}>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Resources and import status</h2>
          <p className="text-sm text-[var(--color-muted-foreground)]">
            Track each uploaded resource as it moves through content intelligence processing.
          </p>
        </div>

        <dl className="mb-6 grid gap-3 text-sm text-[var(--color-muted-foreground)] sm:grid-cols-2 xl:grid-cols-6">
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
            <dt className="font-medium text-[var(--color-foreground)]">Processing</dt>
            <dd className="mt-1">{importSummary.processing}</dd>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
            <dt className="font-medium text-[var(--color-foreground)]">Ready for review</dt>
            <dd className="mt-1">{importSummary.review}</dd>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
            <dt className="font-medium text-[var(--color-foreground)]">Completed</dt>
            <dd className="mt-1">{importSummary.completed}</dd>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
            <dt className="font-medium text-[var(--color-foreground)]">Warnings</dt>
            <dd className="mt-1">{importSummary.warnings}</dd>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
            <dt className="font-medium text-[var(--color-foreground)]">Failed</dt>
            <dd className="mt-1">{importSummary.failed}</dd>
          </div>
          <div className="rounded-[var(--radius-md)] border border-[var(--color-border)] p-4">
            <dt className="font-medium text-[var(--color-foreground)]">Cancelled</dt>
            <dd className="mt-1">{importSummary.cancelled}</dd>
          </div>
        </dl>

        {resources.length === 0 ? (
          <EmptyState
            title="No resources uploaded yet"
            description="Upload a PDF or DOCX file above. After processing finishes, open the resource outline to browse sections and concepts."
          />
        ) : (
          <div className="space-y-4">{resourceCards}</div>
        )}
      </section>

      {pendingDelete ? (
        <section aria-labelledby="delete-upload-title" aria-modal="true" className={panelClassName} role="dialog">
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]" id="delete-upload-title">
              {pendingDelete.label}
            </h2>
            <p className="text-sm text-[var(--color-muted-foreground)]">
              Delete <span className="font-medium text-[var(--color-foreground)]">{pendingDelete.resourceTitle}</span>.
              This removes the uploaded file, processing history, and any generated outline from this subject.
            </p>
            <div className="flex flex-wrap gap-3">
              <button
                className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-danger)] px-4 text-sm font-semibold text-white transition hover:brightness-105 disabled:opacity-70"
                disabled={deletingJobId === pendingDelete.jobId}
                onClick={() => void handleDeleteImport()}
                type="button"
              >
                {deletingJobId === pendingDelete.jobId ? "Deleting..." : pendingDelete.label}
              </button>
              <button
                className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-4 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
                onClick={() => setPendingDelete(null)}
                type="button"
              >
                Keep document
              </button>
            </div>
          </div>
        </section>
      ) : null}
    </section>
  );
}
