import { expect, test } from "@playwright/test";
import { mapGovernedWorkflow, type GovernedWorkflowInput } from "../../src/features/governed-workflow/workflowViewModel";

function workflow(overrides: Partial<GovernedWorkflowInput> = {}) {
  return mapGovernedWorkflow({ resourceExists: true, ...overrides });
}

function status(input: Partial<GovernedWorkflowInput>, key: string) {
  return workflow(input).stages.find((stage) => stage.key === key)?.status;
}

test("workflow never infers later completion from an earlier governed stage", () => {
  const result = workflow({ processingStatus: "ready_for_review" });
  expect(status({ processingStatus: "ready_for_review" }, "processing")).toBe("completed");
  expect(result.stages.find((stage) => stage.key === "review")?.status).toBe("available");
  expect(result.stages.find((stage) => stage.key === "retrieval")?.status).toBe("not_started");
  expect(result.stages.find((stage) => stage.key === "teaching_readiness")?.status).toBe("not_started");
});

test("review and approval blockers remain authoritative presentation states", () => {
  expect(status({ processingStatus: "ready_for_review", reviewStatus: "in_progress", reviewBlockers: 2 }, "review")).toBe("blocked");
  expect(status({ processingStatus: "ready_for_review", reviewStatus: "ready_for_approval", approvalReady: false, approvalBlockers: 1 }, "approval")).toBe("blocked");
});

test("population and synchronization lifecycles map without granting readiness", () => {
  const base = { processingStatus: "ready_for_review", reviewStatus: "approved", projectionStatus: "populated" };
  expect(status({ ...base, populationStatus: "failed" }, "population")).toBe("failed");
  expect(status({ ...base, populationStatus: "populated", retrievalStatus: "synchronizing" }, "retrieval")).toBe("in_progress");
  expect(status({ ...base, populationStatus: "populated", retrievalStatus: "failed" }, "retrieval")).toBe("failed");
  expect(status({ ...base, populationStatus: "populated", retrievalStatus: "synchronized" }, "teaching_readiness")).toBe("available");
});

test("BLOCKED, READY_FOR_TEACHING, and STALE remain distinct final states", () => {
  const base = {
    processingStatus: "ready_for_review", reviewStatus: "approved",
    projectionStatus: "populated", populationStatus: "populated", retrievalStatus: "synchronized",
  };
  expect(status({ ...base, readinessDecision: "blocked" }, "teaching_readiness")).toBe("blocked");
  expect(status({ ...base, readinessStatus: "ready_for_teaching", readinessDecision: "ready" }, "teaching_readiness")).toBe("completed");
  expect(status({ ...base, readinessStatus: "stale", readinessDecision: "ready" }, "teaching_readiness")).toBe("stale");
});

test("unknown backend states are visibly blocked rather than completed", () => {
  const result = workflow({ processingStatus: "unexpected_state" });
  expect(result.stages.find((stage) => stage.key === "processing")).toMatchObject({
    status: "blocked",
    description: "Unknown processing state: unexpected_state.",
  });
  expect(result.latestCompletedStage).toBe("upload");
  expect(result.currentStage).toBe("processing");
});

test("canonical extracting remains in progress and does not unlock review", () => {
  const result = workflow({ processingStatus: "extracting" });
  expect(result.stages.find((stage) => stage.key === "processing")?.status).toBe("in_progress");
  expect(result.stages.find((stage) => stage.key === "review")?.status).toBe("not_started");
});

test("superseded retrieval and unknown readiness remain visible", () => {
  const base = {
    processingStatus: "ready_for_review", reviewStatus: "approved",
    projectionStatus: "populated", populationStatus: "populated",
  };
  expect(status({ ...base, retrievalStatus: "superseded" }, "retrieval")).toBe("superseded");
  expect(status({ ...base, retrievalStatus: "synchronized", readinessStatus: "unexpected" }, "teaching_readiness")).toBe("blocked");
});
