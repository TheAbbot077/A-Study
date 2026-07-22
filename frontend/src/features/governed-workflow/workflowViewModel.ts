export type GovernedStageKey =
  | "upload"
  | "processing"
  | "review"
  | "approval"
  | "population"
  | "retrieval"
  | "teaching_readiness";

export type GovernedStageStatus =
  | "not_started"
  | "available"
  | "in_progress"
  | "completed"
  | "blocked"
  | "failed"
  | "stale"
  | "superseded"
  | "not_applicable";

export type GovernedWorkflowStage = {
  key: GovernedStageKey;
  status: GovernedStageStatus;
  label: string;
  description: string;
  href?: string;
  blockerCount: number;
  warningCount: number;
  updatedAt?: string | null;
};

export type GovernedWorkflowInput = {
  resourceExists: boolean;
  processingStatus?: string | null;
  reviewStatus?: string | null;
  reviewBlockers?: number;
  approvalReady?: boolean | null;
  approvalBlockers?: number;
  projectionStatus?: string | null;
  populationStatus?: string | null;
  populationBlockers?: number;
  retrievalReady?: boolean | null;
  retrievalStatus?: string | null;
  retrievalBlockers?: number;
  retrievalWarnings?: number;
  readinessStatus?: string | null;
  readinessDecision?: string | null;
  readinessBlockers?: number;
  readinessWarnings?: number;
  hrefs?: Partial<Record<GovernedStageKey, string>>;
};

export type GovernedWorkflow = {
  stages: GovernedWorkflowStage[];
  currentStage: GovernedStageKey;
  latestCompletedStage: GovernedStageKey | null;
};

const labels: Record<GovernedStageKey, string> = {
  upload: "Upload",
  processing: "Processing",
  review: "Review",
  approval: "Approval",
  population: "Population",
  retrieval: "Retrieval",
  teaching_readiness: "Teaching readiness",
};

function stage(
  input: GovernedWorkflowInput,
  key: GovernedStageKey,
  status: GovernedStageStatus,
  description: string,
  blockerCount = 0,
  warningCount = 0,
): GovernedWorkflowStage {
  return {
    key, status, description, blockerCount, warningCount,
    label: labels[key], href: input.hrefs?.[key],
  };
}

function processingStage(input: GovernedWorkflowInput) {
  if (!input.resourceExists) return stage(input, "processing", "not_started", "Upload a resource before processing can begin.");
  if (!input.processingStatus) return stage(input, "processing", "not_started", "No processing job has been reported.");
  if (["failed", "cancelled"].includes(input.processingStatus)) return stage(input, "processing", "failed", `Processing ${input.processingStatus}.`);
  if (["ready_for_review", "ready_for_teaching", "completed", "completed_with_warnings"].includes(input.processingStatus)) {
    return stage(input, "processing", "completed", "Governed processing completed.");
  }
  if ([
    "created",
    "queued",
    "inspecting",
    "extracting",
    "structuring",
    "segmenting",
    "validating",
    "populating",
    "indexing",
    "processing",
    "running",
    "retrying",
  ].includes(input.processingStatus)) {
    return stage(input, "processing", "in_progress", "The backend is processing this resource.");
  }
  return stage(input, "processing", "blocked", `Unknown processing state: ${input.processingStatus}.`);
}

function reviewStage(input: GovernedWorkflowInput, processing: GovernedWorkflowStage) {
  if (processing.status !== "completed") return stage(input, "review", "not_started", "Processing must complete before review.");
  if (!input.reviewStatus) return stage(input, "review", "available", "A governed review may be opened when a proposal exists.");
  if (input.reviewStatus === "in_progress") {
    return stage(input, "review", input.reviewBlockers ? "blocked" : "in_progress", input.reviewBlockers ? "Resolve authoritative review blockers." : "Human review is in progress.", input.reviewBlockers);
  }
  if (["ready_for_approval", "approved", "approved_with_edits", "rejected"].includes(input.reviewStatus)) {
    return stage(input, "review", "completed", input.reviewStatus === "rejected" ? "Review completed with rejection." : "Human review completed.");
  }
  return stage(input, "review", "blocked", `Unknown review state: ${input.reviewStatus}.`);
}

export function mapGovernedWorkflow(input: GovernedWorkflowInput): GovernedWorkflow {
  const upload = stage(input, "upload", input.resourceExists ? "completed" : "available", input.resourceExists ? "Source upload recorded." : "Upload a source resource.");
  const processing = processingStage(input);
  const review = reviewStage(input, processing);

  let approval = stage(input, "approval", "not_started", "Complete review before approval.");
  if (input.reviewStatus === "ready_for_approval") {
    approval = stage(input, "approval", input.approvalReady === false ? "blocked" : "available", input.approvalReady === false ? "Backend approval readiness is blocked." : "An authorized approval decision is available.", input.approvalBlockers);
  } else if (["approved", "approved_with_edits"].includes(input.reviewStatus ?? "")) {
    approval = stage(input, "approval", "completed", "An immutable approved projection exists.");
  } else if (input.reviewStatus === "rejected") {
    approval = stage(input, "approval", "not_applicable", "The reviewed proposal was rejected.");
  }

  let population = stage(input, "population", "not_started", "Approval is required before Academic population.");
  if (approval.status === "not_applicable") {
    population = stage(input, "population", "not_applicable", "Population does not apply to a rejected proposal.");
  } else if (approval.status === "completed") {
    if (input.populationStatus === "failed") population = stage(input, "population", "failed", "Academic population failed.", input.populationBlockers);
    else if (input.populationStatus === "populating" || input.populationStatus === "planned") population = stage(input, "population", "in_progress", "Academic population is in progress.");
    else if (input.populationStatus === "populated") population = stage(input, "population", "completed", "Official Academic content was populated.");
    else population = stage(input, "population", input.projectionStatus ? "available" : "not_started", input.projectionStatus ? "Academic population is available." : "An approved projection is required.", input.populationBlockers);
  }

  let retrieval = stage(input, "retrieval", "not_started", "Population must complete before retrieval synchronization.");
  if (population.status === "not_applicable") {
    retrieval = stage(input, "retrieval", "not_applicable", "Retrieval does not apply to a rejected proposal.");
  } else if (population.status === "completed") {
    if (input.retrievalStatus === "failed") retrieval = stage(input, "retrieval", "failed", "Retrieval synchronization failed.", input.retrievalBlockers, input.retrievalWarnings);
    else if (input.retrievalStatus === "superseded") retrieval = stage(input, "retrieval", "superseded", "This retrieval generation was superseded by authoritative replacement.", input.retrievalBlockers, input.retrievalWarnings);
    else if (["planned", "synchronizing"].includes(input.retrievalStatus ?? "")) retrieval = stage(input, "retrieval", "in_progress", "Retrieval synchronization is in progress.", input.retrievalBlockers, input.retrievalWarnings);
    else if (input.retrievalStatus === "synchronized") retrieval = stage(input, "retrieval", "completed", "Grounded retrieval is synchronized.", input.retrievalBlockers, input.retrievalWarnings);
    else retrieval = stage(input, "retrieval", input.retrievalReady === false ? "blocked" : "available", input.retrievalReady === false ? "Backend synchronization readiness is blocked." : "Retrieval synchronization is available.", input.retrievalBlockers, input.retrievalWarnings);
  }

  let teaching = stage(input, "teaching_readiness", "not_started", "Retrieval must synchronize before evaluation.");
  if (retrieval.status === "not_applicable") {
    teaching = stage(input, "teaching_readiness", "not_applicable", "Teaching readiness does not apply to a rejected proposal.");
  } else if (retrieval.status === "completed") {
    if (input.readinessStatus === "stale") teaching = stage(input, "teaching_readiness", "stale", "A prior readiness result is stale and no longer current.", input.readinessBlockers, input.readinessWarnings);
    else if (input.readinessStatus === "ready_for_teaching" && input.readinessDecision === "ready") teaching = stage(input, "teaching_readiness", "completed", "The backend granted READY_FOR_TEACHING.", input.readinessBlockers, input.readinessWarnings);
    else if (input.readinessDecision === "blocked") teaching = stage(input, "teaching_readiness", "blocked", "Evaluation completed with authoritative blockers.", input.readinessBlockers, input.readinessWarnings);
    else if (!input.readinessStatus || input.readinessStatus === "not_ready") teaching = stage(input, "teaching_readiness", "available", "Teaching readiness has not been evaluated.", input.readinessBlockers, input.readinessWarnings);
    else teaching = stage(input, "teaching_readiness", "blocked", `Unknown teaching-readiness state: ${input.readinessStatus}.`, input.readinessBlockers, input.readinessWarnings);
  }

  const stages = [upload, processing, review, approval, population, retrieval, teaching];
  const latestCompletedStage = [...stages].reverse().find((item) => item.status === "completed")?.key ?? null;
  const currentStage = stages.find((item) => !["completed", "not_applicable", "superseded"].includes(item.status))?.key ?? "teaching_readiness";
  return { stages, currentStage, latestCompletedStage };
}
