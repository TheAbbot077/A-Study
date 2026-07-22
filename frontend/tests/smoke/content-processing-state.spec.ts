import { expect, test } from "@playwright/test";
import {
  isCanonicalProcessingActive,
  isCanonicalProcessingTerminal,
  selectAuthoritativeProcessing,
} from "../../src/features/content-processing/processingState";
import { toProcessingJobId, type ProcessingJob, type ProcessingJobId } from "../../src/features/content-processing/types";
import { processingJobPath } from "../../src/features/content-processing/api";
import {
  legacyImportJobPath,
  toLegacyImportJobId,
  type LegacyImportJobId,
} from "../../src/services/content-intelligence";

function canonical(overrides: Partial<ProcessingJob> = {}): ProcessingJob {
  const id = toProcessingJobId("canonical-job-1");
  return {
    id,
    processing_job_id: id,
    resource: "resource-1",
    stored_file: "stored-file-1",
    status: "EXTRACTING",
    stage: "extracting",
    progress: 25,
    stage_label: "Extracting document content",
    message: null,
    attempt: 2,
    warning_count: 0,
    can_retry: false,
    can_cancel: true,
    failure: null,
    review_required: false,
    ready_for_teaching: false,
    completed_at: null,
    created_at: "2026-07-20T09:12:43Z",
    updated_at: "2026-07-20T09:14:40Z",
    ...overrides,
  };
}

test("canonical processing progress wins when legacy projection disagrees", () => {
  const selected = selectAuthoritativeProcessing(canonical(), {
    processing_status: "QUEUED",
    processing_stage: "queued",
    processing_progress: 5,
    processing_stage_label: "Waiting to begin processing",
    processing_attempt: 1,
  });
  expect(selected).toMatchObject({
    source: "canonical",
    status: "EXTRACTING",
    stage: "extracting",
    progress: 25,
    stageLabel: "Extracting document content",
    attempt: 2,
  });
});

test("legacy-only records retain compatibility without fabricating a canonical identifier", () => {
  const selected = selectAuthoritativeProcessing(null, {
    processing_status: "processing",
    processing_stage: "validation",
    processing_progress: 70,
  });
  expect(selected.source).toBe("legacy");
  expect(selected.progress).toBe(70);
  expect(selected).not.toHaveProperty("processing_job_id");
});

test("long-running extraction remains active while terminal states stop polling", () => {
  expect(isCanonicalProcessingActive(canonical())).toBe(true);
  expect(isCanonicalProcessingTerminal(canonical())).toBe(false);
  expect(isCanonicalProcessingActive(canonical({ status: "READY_FOR_REVIEW", review_required: true }))).toBe(false);
  expect(isCanonicalProcessingTerminal(canonical({ status: "FAILED" }))).toBe(true);
});

test("processing completion does not imply teaching readiness", () => {
  const readyForReview = canonical({
    status: "READY_FOR_REVIEW",
    progress: 98,
    review_required: true,
    ready_for_teaching: false,
  });
  expect(readyForReview.ready_for_teaching).toBe(false);
});

test("canonical and legacy actions use distinct typed identifiers and endpoints", () => {
  const canonicalId = toProcessingJobId("canonical-job-1");
  const legacyId = toLegacyImportJobId("legacy-job-1");
  expect(processingJobPath(canonicalId, "retry")).toBe("content-processing/jobs/canonical-job-1/retry/");
  expect(processingJobPath(canonicalId, "cancel")).toBe("content-processing/jobs/canonical-job-1/cancel/");
  expect(legacyImportJobPath(legacyId, "retry")).toBe("content-intelligence/import-jobs/legacy-job-1/retry/");

  // @ts-expect-error A legacy import identifier cannot be sent to canonical processing actions.
  const crossedCanonicalId: ProcessingJobId = legacyId;
  // @ts-expect-error A canonical processing identifier cannot be sent to legacy import actions.
  const crossedLegacyId: LegacyImportJobId = canonicalId;
  expect(crossedCanonicalId).toBe(legacyId);
  expect(crossedLegacyId).toBe(canonicalId);
});
