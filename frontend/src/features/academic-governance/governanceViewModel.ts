import type {
  ApprovedProjection,
  ApprovalReadinessSnapshot,
  PopulationReadiness,
  ReviewSession,
} from "@/services/academic-review";

export function governanceStage(session: ReviewSession) {
  if (session.status === "rejected") return "rejected" as const;
  if (session.status === "approved" || session.status === "approved_with_edits") {
    return "approved" as const;
  }
  if (session.status === "ready_for_approval") return "awaiting_decision" as const;
  return "review_incomplete" as const;
}

export function approvalAllowed(session: ReviewSession, readiness: ApprovalReadinessSnapshot | null) {
  return session.status === "ready_for_approval" && readiness?.ready === true;
}

export function orderedProjection(projection: ApprovedProjection) {
  return {
    sections: [...projection.sections].sort((left, right) => left.ordinal - right.ordinal || left.id - right.id),
    concepts: [...projection.concepts].sort((left, right) => left.ordinal - right.ordinal || left.id - right.id),
  };
}

export function populationAllowed(readiness: PopulationReadiness | null) {
  return readiness?.ready === true && !readiness.existing_population_run_id;
}
