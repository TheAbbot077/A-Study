import { expect, test } from "@playwright/test";
import {
  filterReadinessChecks,
  groupReadinessChecks,
  readinessLabel,
} from "../../src/features/teaching-readiness/readinessViewModel";
import type { TeachingReadinessCheck, TeachingReadinessStatusResponse } from "../../src/features/teaching-readiness/types";

const checks: TeachingReadinessCheck[] = [
  { code: "PASSED_SOURCE", category: "source", passed: true, severity: "blocker", expected: true, observed: true, explanation: "Source is current.", related_ids: [] },
  { code: "WARNING_POLICY", category: "policy", passed: false, severity: "warning", expected: "v2", observed: "v1", explanation: "A newer policy is available.", related_ids: [] },
  { code: "BLOCKED_RETRIEVAL", category: "retrieval", passed: false, severity: "blocker", expected: "active", observed: "failed", explanation: "Retrieval is not active.", related_ids: ["generation-1"] },
];

function status(overrides: Partial<TeachingReadinessStatusResponse>): TeachingReadinessStatusResponse {
  return {
    resource_id: "resource-1", status: "not_ready", latest_evaluation_id: null,
    decision: null, blockers: [], warnings: [], can_evaluate: true, can_reevaluate: false,
    ...overrides,
  };
}

test("readiness labels preserve READY, BLOCKED, STALE, and unevaluated backend states", () => {
  expect(readinessLabel(status({ status: "ready_for_teaching", decision: "ready" }))).toBe("READY FOR TEACHING");
  expect(readinessLabel(status({ decision: "blocked" }))).toBe("BLOCKED");
  expect(readinessLabel(status({ status: "stale", decision: "ready" }))).toBe("STALE");
  expect(readinessLabel(status({}))).toBe("NOT EVALUATED");
});

test("check filters preserve backend pass and severity values", () => {
  expect(filterReadinessChecks(checks, "blockers").map((check) => check.code)).toEqual(["BLOCKED_RETRIEVAL"]);
  expect(filterReadinessChecks(checks, "warnings").map((check) => check.code)).toEqual(["WARNING_POLICY"]);
  expect(filterReadinessChecks(checks, "passed").map((check) => check.code)).toEqual(["PASSED_SOURCE"]);
});

test("checks remain grouped in governed category order", () => {
  expect(groupReadinessChecks(checks, "all").map((group) => group.category)).toEqual(["source", "retrieval", "policy"]);
});
