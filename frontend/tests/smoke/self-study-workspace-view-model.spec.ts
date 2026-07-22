import { test, expect } from "@playwright/test";
import {
  coverageMeaning,
  diagnosticExperienceTitle,
  diagnosticProgressLabel,
  planReadinessLabel,
} from "../../src/features/self-study/experienceViewModel";
import { hasBlockingOnboarding, materialStatusSummary, nextActionTone, workspaceStatusLabel } from "../../src/features/self-study/workspaceViewModel";
import type { SelfStudyDiagnosticExperience, SelfStudyNextAction, SelfStudyOnboardingSummary, SelfStudyPlanExperience, WorkspaceMaterial } from "../../src/services/self-study";

test("workspace labels keep learner copy distinct from backend enum values", () => {
  expect(workspaceStatusLabel("INTENT_REQUIRED")).toBe("Intent Required");
  expect(workspaceStatusLabel("ready_to_learn")).toBe("Ready To Learn");
});

test("next action tone distinguishes ready, waiting, and blocked states", () => {
  const action = (code: SelfStudyNextAction["code"]): SelfStudyNextAction => ({
    code,
    title: code,
    explanation: "",
    primary_cta_label: "",
    target_route: "/dashboard/self-study/workspace-1",
    blocker_codes: [],
    safe_ids: {},
    safe_status_summary: {},
  });

  expect(nextActionTone(action("START_DIAGNOSTIC"))).toBe("ready");
  expect(nextActionTone(action("WAIT_FOR_PROCESSING"))).toBe("waiting");
  expect(nextActionTone(action("RESOLVE_MATERIAL_ISSUES"))).toBe("blocked");
  expect(nextActionTone(action("COMPLETE_INTENT"))).toBe("neutral");
});

test("material summary preserves backend material statuses", () => {
  const materials = [
    { status: "PROCESSING" },
    { status: "ELIGIBLE" },
    { status: "ELIGIBLE" },
  ] as WorkspaceMaterial[];

  expect(materialStatusSummary(materials)).toBe("2 Eligible, 1 Processing");
});

test("onboarding blocker detection reads backend blocker codes", () => {
  const summary: SelfStudyOnboardingSummary = {
    workspace_id: "workspace-1",
    status: "INTENT_REQUIRED",
    version: 1,
    blocker_codes: [],
    material_counts: {},
    next_action: {
      code: "COMPLETE_INTENT",
      title: "Tell Abbot what you want to learn",
      explanation: "Answer intent questions.",
      primary_cta_label: "Answer intent questions",
      target_route: "/dashboard/self-study/workspace-1/intent",
      blocker_codes: ["INTENT_REQUIRED"],
      safe_ids: { workspace_id: "workspace-1" },
      safe_status_summary: { workspace_status: "INTENT_REQUIRED" },
    },
  };

  expect(hasBlockingOnboarding(summary)).toBe(true);
  expect(hasBlockingOnboarding(null)).toBe(false);
});

test("diagnostic experience copy avoids mastery language while preserving progress", () => {
  const experience: SelfStudyDiagnosticExperience = {
    workspace_id: "workspace-1",
    diagnostic_session_id: "diagnostic-1",
    status: "READY_TO_START",
    can_start: true,
    can_resume: false,
    can_submit: false,
    progress: { answered: 0, minimum_items: 8, maximum_items: 12 },
    disclosure_complete: true,
    privacy_notice_version: "1",
    next_action: "diagnostic",
    blocker_codes: [],
  };

  expect(diagnosticExperienceTitle(experience)).toBe("You’re ready for your diagnostic");
  expect(diagnosticProgressLabel(experience)).toBe("0 of 12 diagnostic items recorded.");
});

test("coverage meanings preserve safe learner-facing PI-6F.5 distinctions", () => {
  expect(coverageMeaning("COVERED")).toBe("Materials are available for this part.");
  expect(coverageMeaning("PARTIAL")).toBe("Some support exists, but it may not be enough.");
  expect(coverageMeaning("MISSING")).toBe("Required material is not available yet.");
  expect(coverageMeaning("CONFLICTING")).toBe("Materials disagree or contain unresolved conflict.");
  expect(coverageMeaning("OUT_OF_SCOPE")).toBe("Uploaded material does not support this curriculum area.");
  expect(coverageMeaning("SUPPLEMENTARY")).toBe("Helpful extra material exists, but it is not core support.");
  expect(coverageMeaning("NOT_APPLICABLE")).toBe("Material coverage is not required for this node.");
  expect(coverageMeaning("UNEVALUATED")).toBe("Coverage has not been evaluated yet.");
});

test("study plan readiness label fails closed until teaching preparation permits launch", () => {
  const basePlan: SelfStudyPlanExperience = {
    workspace_id: "workspace-1",
    bridge_plan_id: "plan-1",
    plan_status: "ACTIVE",
    approval_status: "APPROVED",
    active: true,
    target_scope: {},
    estimated_node_count: 3,
    required_node_count: 2,
    optional_node_count: 1,
    blocked_node_count: 0,
    ready_node_count: 2,
    next_plan_node_id: "node-1",
    can_start_learning: false,
    blocker_codes: ["TEACHING_NOT_PREPARED"],
    findings: [],
  };

  expect(planReadinessLabel(basePlan)).toBe("Your study plan is being prepared");
  expect(planReadinessLabel({ ...basePlan, can_start_learning: true, blocker_codes: [] })).toBe("Start learning with Abbot");
});
