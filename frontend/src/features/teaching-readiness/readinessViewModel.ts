import type {
  TeachingReadinessCheck,
  TeachingReadinessCheckCategory,
  TeachingReadinessCheckSeverity,
  TeachingReadinessStatusResponse,
} from "./types";

export type ReadinessCheckFilter = "all" | "blockers" | "warnings" | "passed";

const categories: TeachingReadinessCheckCategory[] = [
  "source", "processing", "review", "approval", "academic", "retrieval", "provenance", "policy",
];
const severity: Record<TeachingReadinessCheckSeverity, number> = {
  blocker: 0, warning: 1, information: 2,
};

export function filterReadinessChecks(checks: TeachingReadinessCheck[], filter: ReadinessCheckFilter) {
  if (filter === "passed") return checks.filter((check) => check.passed);
  if (filter === "blockers") return checks.filter((check) => !check.passed && check.severity === "blocker");
  if (filter === "warnings") return checks.filter((check) => !check.passed && check.severity === "warning");
  return checks;
}

export function groupReadinessChecks(checks: TeachingReadinessCheck[], filter: ReadinessCheckFilter) {
  const visible = filterReadinessChecks(checks, filter);
  return categories.map((category) => ({
    category,
    checks: visible
      .filter((check) => check.category === category)
      .sort((left, right) => severity[left.severity] - severity[right.severity] || left.code.localeCompare(right.code)),
  })).filter((group) => group.checks.length);
}

export function readinessLabel(status: TeachingReadinessStatusResponse) {
  if (status.status === "stale") return "STALE";
  if (status.status === "ready_for_teaching" && status.decision === "ready") return "READY FOR TEACHING";
  if (status.decision === "blocked") return "BLOCKED";
  return "NOT EVALUATED";
}
