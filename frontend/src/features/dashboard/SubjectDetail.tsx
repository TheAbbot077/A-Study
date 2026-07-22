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
  type LegacyImportJobId,
} from "@/services/content-intelligence";
import { uploadStoredFile } from "@/services/storage";
import { pollOperation } from "@/lib/polling";
import { ApiError } from "@/services/api";
import { contentProcessingApi } from "@/features/content-processing/api";
import {
  canonicalStatusLabel,
  isCanonicalProcessingActive,
  isCanonicalProcessingFailed,
  isCanonicalProcessingTerminal,
  PROCESSING_POLL_INTERVAL_MS,
} from "@/features/content-processing/processingState";
import {
  toProcessingJobId,
  type ProcessingDiagnostic,
  type ProcessingJob,
  type ProcessingJobId,
} from "@/features/content-processing/types";

type SubjectDetailProps = {
  subjectId: string;
};

type ImportStatusTone = "processing" | "review" | "completed" | "warning" | "failed" | "cancelled";

type ImportPresentation = {
  label: string;
  tone: ImportStatusTone;
};

type PendingDelete = {
  jobId: LegacyImportJobId;
  resourceId: string;
  resourceTitle: string;
  label: string;
};

const panelClassName =
  "rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-background)] p-6 shadow-[var(--shadow-card)]";

function getLatestImportJob(jobs: ContentImportJob[]): ContentImportJob | null {
  return jobs[0] ?? null;
}

function presentImportStatus(
  job: ContentImportJob | null,
  canonicalJob: ProcessingJob | null,
  resolvingCanonical: boolean,
): ImportPresentation {
  if (resolvingCanonical) {
    return { label: "Resolving processing status", tone: "processing" };
  }
  if (canonicalJob) {
    if (canonicalJob.review_required) return { label: "Ready for review", tone: "review" };
    if (isCanonicalProcessingActive(canonicalJob)) return { label: canonicalStatusLabel(canonicalJob), tone: "processing" };
    if (canonicalJob.status === "READY_FOR_TEACHING") return { label: "Ready for teaching", tone: "completed" };
    if (canonicalJob.status === "FAILED") return { label: "Processing failed", tone: "failed" };
    if (canonicalJob.status === "CANCELLED" || canonicalJob.status === "DELETED") {
      return { label: canonicalStatusLabel(canonicalJob), tone: "cancelled" };
    }
  }
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
  const requestVersionRef = useRef(0);
  const pollingControllersRef = useRef(new Map<string, AbortController>());
  const [subject, setSubject] = useState<Subject | null>(null);
  const [resources, setResources] = useState<LearningResource[]>([]);
  const [jobsByResource, setJobsByResource] = useState<Record<string, ContentImportJob | null>>({});
  const [processingJobsByResource, setProcessingJobsByResource] = useState<Record<string, ProcessingJob | null | undefined>>({});
  const [diagnosticsByResource, setDiagnosticsByResource] = useState<Record<string, ProcessingDiagnostic[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null);

  function replacePollingController(resourceId: string) {
    pollingControllersRef.current.get(resourceId)?.abort();
    const controller = new AbortController();
    pollingControllersRef.current.set(resourceId, controller);
    return controller;
  }

  function isTransientPollingError(pollingError: unknown) {
    return pollingError instanceof TypeError ||
      (pollingError instanceof ApiError &&
        (pollingError.status === 0 || (pollingError.status !== undefined && pollingError.status >= 500)));
  }

  async function loadCanonicalDiagnostics(resourceId: string, jobId: ProcessingJobId) {
    const diagnostics = await contentProcessingApi.diagnostics(jobId);
    setDiagnosticsByResource((current) => ({ ...current, [resourceId]: diagnostics ?? [] }));
  }

  async function pollCanonicalJob(initialJob: ProcessingJob, resourceId: string) {
    if (!isCanonicalProcessingActive(initialJob)) return;
    const controller = replacePollingController(resourceId);
    try {
      const nextJob = await pollOperation({
        signal: controller.signal,
        intervalMs: PROCESSING_POLL_INTERVAL_MS,
        request: async (signal) => {
          const job = await contentProcessingApi.get(initialJob.processing_job_id, signal);
          if (!job) throw new Error("Canonical processing status returned no response body.");
          return job;
        },
        isSuccess: isCanonicalProcessingTerminal,
        isFailure: isCanonicalProcessingFailed,
        shouldRetryError: isTransientPollingError,
        onValue: (job) => {
          setProcessingJobsByResource((current) => ({ ...current, [resourceId]: job }));
        },
      });
      if (!controller.signal.aborted && (nextJob.warning_count > 0 || nextJob.failure)) {
        await loadCanonicalDiagnostics(resourceId, nextJob.processing_job_id);
      }
    } catch (pollingError) {
      if (!(pollingError instanceof DOMException && pollingError.name === "AbortError")) {
        setError(pollingError instanceof Error ? pollingError.message : "Unable to refresh processing status.");
      }
    } finally {
      if (pollingControllersRef.current.get(resourceId) === controller) {
        pollingControllersRef.current.delete(resourceId);
      }
    }
  }

  async function resolveCanonicalJob(legacyJob: ContentImportJob, resourceId: string, signal?: AbortSignal) {
    if (!legacyJob.processing_job_id) {
      setProcessingJobsByResource((current) => ({ ...current, [resourceId]: null }));
      return null;
    }
    const canonicalId = toProcessingJobId(legacyJob.processing_job_id);
    const canonicalJob = await pollOperation({
      signal,
      intervalMs: PROCESSING_POLL_INTERVAL_MS,
      request: async (requestSignal) => {
        const resolved = await contentProcessingApi.get(canonicalId, requestSignal);
        if (!resolved) throw new Error("Canonical processing linkage returned no response body.");
        return resolved;
      },
      isSuccess: () => true,
      isFailure: () => false,
      shouldRetryError: isTransientPollingError,
    });
    if (signal?.aborted) return null;
    setProcessingJobsByResource((current) => ({ ...current, [resourceId]: canonicalJob }));
    if (canonicalJob.warning_count > 0 || canonicalJob.failure) {
      await loadCanonicalDiagnostics(resourceId, canonicalId);
    }
    if (isCanonicalProcessingActive(canonicalJob)) void pollCanonicalJob(canonicalJob, resourceId);
    return canonicalJob;
  }

  async function pollLegacyJob(initialJob: ContentImportJob, resourceId: string) {
    const controller = replacePollingController(resourceId);
    try {
      const nextJob = await pollOperation({
        signal: controller.signal,
        intervalMs: PROCESSING_POLL_INTERVAL_MS,
        request: (signal) => getImportJob(initialJob.id, signal),
        isSuccess: (job) => Boolean(job.processing_job_id) || isPollingTerminal(job),
        isFailure: isProcessingFailed,
        shouldRetryError: isTransientPollingError,
        onValue: (job) => {
          setJobsByResource((current) => ({ ...current, [resourceId]: job }));
        },
      });
      if (!controller.signal.aborted && nextJob.processing_job_id) {
        await resolveCanonicalJob(nextJob, resourceId);
      }
    } catch (pollingError) {
      if (!(pollingError instanceof DOMException && pollingError.name === "AbortError")) {
        setError(pollingError instanceof Error ? pollingError.message : "Unable to refresh legacy import status.");
      }
    } finally {
      if (pollingControllersRef.current.get(resourceId) === controller) {
        pollingControllersRef.current.delete(resourceId);
      }
    }
  }

  async function resolveCanonicalOnlyResource(resourceId: string, signal: AbortSignal) {
    const jobs = await contentProcessingApi.listForResource(resourceId, signal);
    if (signal.aborted) return;
    const canonicalJob = jobs?.[0] ?? null;
    setProcessingJobsByResource((current) => ({ ...current, [resourceId]: canonicalJob }));
    if (canonicalJob && isCanonicalProcessingActive(canonicalJob)) {
      void pollCanonicalJob(canonicalJob, resourceId);
    }
  }

  function synchronizeProcessingJobs(entries: ReadonlyArray<readonly [string, ContentImportJob | null]>) {
    for (const [resourceId, job] of entries) {
      if (!job) {
        setProcessingJobsByResource((current) => ({ ...current, [resourceId]: undefined }));
        const controller = replacePollingController(resourceId);
        void resolveCanonicalOnlyResource(resourceId, controller.signal).catch((resolutionError: unknown) => {
          if (!(resolutionError instanceof DOMException && resolutionError.name === "AbortError")) {
            setError(resolutionError instanceof Error ? resolutionError.message : "Unable to resolve processing status.");
          }
        });
      } else if (job.processing_job_id) {
        setProcessingJobsByResource((current) => ({ ...current, [resourceId]: undefined }));
        const controller = replacePollingController(resourceId);
        void resolveCanonicalJob(job, resourceId, controller.signal)
          .catch((resolutionError: unknown) => {
            if (!(resolutionError instanceof DOMException && resolutionError.name === "AbortError")) {
              setError(resolutionError instanceof Error ? resolutionError.message : "Unable to resolve canonical processing status.");
            }
          });
      } else if (isActivelyProcessing(job)) {
        setProcessingJobsByResource((current) => ({ ...current, [resourceId]: null }));
        void pollLegacyJob(job, resourceId);
      } else {
        setProcessingJobsByResource((current) => ({ ...current, [resourceId]: null }));
      }
    }
  }

  async function loadSubjectData() {
    const requestVersion = ++requestVersionRef.current;
    setLoading(true);
    setError(null);

    try {
      let nextSubject: Subject | null = null;
      try {
        nextSubject = await getSubject(subjectId);
      } catch (loadSubjectError) {
        if (loadSubjectError instanceof ApiError && loadSubjectError.status === 404) {
          const subjects = await listSubjects();
          nextSubject = subjects.find((item) => item.id === subjectId) ?? null;
          if (!nextSubject) {
            throw loadSubjectError;
          }
        } else {
          throw loadSubjectError;
        }
      }

      const nextResources = await listResourcesForSubject(subjectId);

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

      if (requestVersion !== requestVersionRef.current) return;
      setSubject(nextSubject);
      setResources(nextResources);
      setJobsByResource(Object.fromEntries(jobEntries));
      synchronizeProcessingJobs(jobEntries);
      if (failedJobLoads) {
        setError("The subject loaded, but some import status details could not be retrieved right now.");
      }
    } catch (loadError) {
      if (requestVersion === requestVersionRef.current) {
        setError(loadError instanceof Error ? loadError.message : "Unable to load this subject right now.");
      }
    } finally {
      if (requestVersion === requestVersionRef.current) setLoading(false);
    }
  }

  useEffect(() => {
    const requestVersion = ++requestVersionRef.current;
    let active = true;
    async function synchronizeSubject() {
      try {
        let nextSubject: Subject | null;
        try {
          nextSubject = await getSubject(subjectId);
        } catch (loadSubjectError) {
          if (!(loadSubjectError instanceof ApiError) || loadSubjectError.status !== 404) throw loadSubjectError;
          const subjects = await listSubjects();
          nextSubject = subjects.find((item) => item.id === subjectId) ?? null;
          if (!nextSubject) throw loadSubjectError;
        }
        const nextResources = await listResourcesForSubject(subjectId);
        const settled = await Promise.allSettled(nextResources.map(async (resource) => {
          const jobs = await listImportJobsForResource(resource.id);
          return [resource.id, getLatestImportJob(jobs)] as const;
        }));
        if (!active || requestVersion !== requestVersionRef.current) return;
        setSubject(nextSubject);
        setResources(nextResources);
        setJobsByResource(Object.fromEntries(
          settled.filter((item): item is PromiseFulfilledResult<readonly [string, ContentImportJob | null]> => item.status === "fulfilled").map((item) => item.value),
        ));
        synchronizeProcessingJobs(
          settled
            .filter((item): item is PromiseFulfilledResult<readonly [string, ContentImportJob | null]> => item.status === "fulfilled")
            .map((item) => item.value),
        );
        setError(settled.some((item) => item.status === "rejected") ? "The subject loaded, but some import status details could not be retrieved right now." : null);
      } catch (loadError) {
        if (active && requestVersion === requestVersionRef.current) {
          setError(loadError instanceof Error ? loadError.message : "Unable to load this subject right now.");
        }
      } finally {
        if (active && requestVersion === requestVersionRef.current) setLoading(false);
      }
    }
    void synchronizeSubject();
    return () => {
      active = false;
      for (const controller of pollingControllersRef.current.values()) controller.abort();
      pollingControllersRef.current.clear();
    };
  }, [subjectId]);

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

      if (job.processing_job_id) {
        setProcessingJobsByResource((current) => ({ ...current, [resource.id]: undefined }));
        await resolveCanonicalJob(job, resource.id);
      } else if (isActivelyProcessing(job)) {
        setProcessingJobsByResource((current) => ({ ...current, [resource.id]: null }));
        void pollLegacyJob(job, resource.id);
      } else {
        await loadSubjectData();
      }
    } catch (uploadError) {
      if (uploadError instanceof DOMException && uploadError.name === "AbortError") return;
      setError(uploadError instanceof Error ? uploadError.message : "Unable to upload this resource right now.");
    } finally {
      setUploading(false);
    }
  }

  async function handleRetry(resourceId: string, legacyJob: ContentImportJob, canonicalJob: ProcessingJob | null) {
    setError(null);

    try {
      if (canonicalJob) {
        const retriedJob = await contentProcessingApi.retry(canonicalJob.processing_job_id);
        if (!retriedJob) throw new Error("Canonical retry returned no response body.");
        setProcessingJobsByResource((current) => ({ ...current, [resourceId]: retriedJob }));
        void pollCanonicalJob(retriedJob, resourceId);
      } else {
        const retriedJob = await retryImportJob(legacyJob.id);
        setJobsByResource((current) => ({ ...current, [resourceId]: retriedJob }));
        if (retriedJob.processing_job_id) {
          await resolveCanonicalJob(retriedJob, resourceId);
        } else {
          void pollLegacyJob(retriedJob, resourceId);
        }
      }
    } catch (retryError) {
      if (retryError instanceof DOMException && retryError.name === "AbortError") return;
      setError(retryError instanceof Error ? retryError.message : "Unable to retry this import right now.");
    }
  }

  async function handleCancel(resourceId: string, canonicalJob: ProcessingJob) {
    setError(null);
    try {
      const cancelledJob = await contentProcessingApi.cancel(canonicalJob.processing_job_id);
      if (!cancelledJob) throw new Error("Canonical cancellation returned no response body.");
      pollingControllersRef.current.get(resourceId)?.abort();
      setProcessingJobsByResource((current) => ({ ...current, [resourceId]: cancelledJob }));
    } catch (cancelError) {
      setError(cancelError instanceof Error ? cancelError.message : "Unable to cancel processing right now.");
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

  const resourceCards = resources.map((resource) => {
        const job = jobsByResource[resource.id] ?? null;
        const canonicalState = processingJobsByResource[resource.id];
        const canonicalJob = canonicalState ?? null;
        const resolvingCanonical = Boolean(job?.processing_job_id) && canonicalState === undefined;
        const presentation = presentImportStatus(job, canonicalJob, resolvingCanonical);
        const authoritativeStatus = canonicalJob ? canonicalJob.status : authoritativeProcessingStatus(job);
        const reviewRequired = canonicalJob ? canonicalJob.review_required : isReviewRequired(job);
        const readyForLearning = canonicalJob
          ? canonicalJob.ready_for_teaching
          : isReadyForTeaching(job) || (!authoritativeStatus && Boolean(resource.resource_ready_for_learning || job?.resource_ready_for_learning));
        const activelyProcessing = canonicalJob ? isCanonicalProcessingActive(canonicalJob) : isActivelyProcessing(job);
        const canDelete = Boolean(job && !activelyProcessing);
        const hasFailedImportAction = canonicalJob ? isCanonicalProcessingFailed(canonicalJob) : job !== null && isProcessingFailed(job);
        const deleteLabel = job?.status === "failed" || job?.status === "cancelled" ? "Delete failed upload" : "Delete document";
        const failure = canonicalJob?.failure?.message ?? failureReason(job);
        const activeStageLabel = resolvingCanonical
          ? "Resolving processing status"
          : canonicalJob ? canonicalStatusLabel(canonicalJob) : processingStageLabel(job);
        const progress = resolvingCanonical
          ? null
          : canonicalJob?.progress ?? (typeof job?.processing_progress === "number" ? job.processing_progress : null);
        const attempt = canonicalJob?.attempt ?? (typeof job?.processing_attempt === "number" ? job.processing_attempt : null);
        const diagnostics = diagnosticsByResource[resource.id] ?? [];

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
                <dd className="mt-1">{canonicalJob?.warning_count ?? job?.processing_warning_count ?? job?.validation_findings?.length ?? 0}</dd>
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
                    <p>{reviewRequired ? `${progress}% processed — governed review required` : `${progress}% processed`}</p>
                  </div>
                ) : null}
                {canonicalJob && isCanonicalProcessingActive(canonicalJob) ? <p className="mt-2">Processing is still active.</p> : null}
                {canonicalJob ? (
                  <>
                    <p className="mt-2">Last confirmed update: {new Date(canonicalJob.updated_at).toLocaleString()}</p>
                    <p className="mt-2 break-all text-xs">
                      Processing job: {canonicalJob.processing_job_id}
                      {job ? `; legacy import: ${job.id}` : ""}
                    </p>
                  </>
                ) : null}
              </div>
            ) : null}

            {diagnostics.length ? (
              <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-warning)]/60 p-4">
                <h4 className="text-sm font-semibold text-[var(--color-foreground)]">Processing diagnostics</h4>
                <ul className="mt-2 space-y-2 text-sm text-[var(--color-muted-foreground)]">
                  {diagnostics.map((diagnostic) => <li key={diagnostic.id}>{diagnostic.public_message}</li>)}
                </ul>
              </div>
            ) : null}

            {reviewRequired ? (
              <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-primary)]/50 p-4 text-sm">
                <h4 className="font-semibold text-[var(--color-foreground)]">Ready for review</h4>
                <p className="mt-2 text-[var(--color-muted-foreground)]">
                  Processing completed successfully, but this document needs academic review before it can become official Academic content.
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

            {job && hasFailedImportAction ? (
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
                  {(canonicalJob ? canonicalJob.can_retry : job.can_retry_processing ?? true) ? (
                    <button
                      className="inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 text-sm font-medium transition hover:bg-[var(--color-accent)]/25"
                      onClick={() => void handleRetry(resource.id, job, canonicalJob)}
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

            {job && activelyProcessing ? (
              <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--color-border)] p-4 text-sm text-[var(--color-muted-foreground)]">
                Processing is still active. The resource outline remains governed until the backend reaches the appropriate state.
                {canonicalJob?.can_cancel ? (
                  <button
                    className="ml-3 inline-flex min-h-10 items-center justify-center rounded-[var(--radius-md)] border border-[var(--color-border)] px-3 text-sm font-medium"
                    onClick={() => void handleCancel(resource.id, canonicalJob)}
                    type="button"
                  >
                    Cancel processing
                  </button>
                ) : null}
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
      });

  const importSummary = useMemo(() => {
    let processing = 0;
    let completed = 0;
    let review = 0;
    let warnings = 0;
    let failed = 0;
    let cancelled = 0;

    for (const resource of resources) {
      const job = jobsByResource[resource.id] ?? null;
      const canonicalState = processingJobsByResource[resource.id];
      const presentation = presentImportStatus(
        job,
        canonicalState ?? null,
        Boolean(job?.processing_job_id) && canonicalState === undefined,
      );
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
  }, [jobsByResource, processingJobsByResource, resources]);

  if (loading) {
    return <LoadingState message="Loading subject workspace..." />;
  }

  if (error && !subject) {
    return <ErrorState title="Subject unavailable" message={error} />;
  }

  if (!subject) {
    return <ErrorState title="Subject unavailable" message="We could not find this subject." />;
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
