import { expect, test } from "@playwright/test";
import {
  approvalAllowed,
  governanceStage,
  orderedProjection,
  populationAllowed,
} from "../../src/features/academic-governance/governanceViewModel";
import type {
  ApprovedProjection,
  ApprovalReadinessSnapshot,
  PopulationReadiness,
  ReviewSession,
} from "../../src/services/academic-review";

const session = {
  status: "ready_for_approval",
  version: 4,
} as ReviewSession;
const readiness = {
  ready: true,
  review_session_version: 4,
} as ApprovalReadinessSnapshot;

test("governance actions preserve backend readiness authority", () => {
  expect(governanceStage(session)).toBe("awaiting_decision");
  expect(approvalAllowed(session, readiness)).toBe(true);
  expect(approvalAllowed(session, { ...readiness, ready: false })).toBe(false);
  expect(populationAllowed({ ready: true, existing_population_run_id: null } as PopulationReadiness)).toBe(true);
  expect(populationAllowed({ ready: false, existing_population_run_id: null } as PopulationReadiness)).toBe(false);
  expect(populationAllowed({ ready: true, existing_population_run_id: "run-1" } as PopulationReadiness)).toBe(false);
});

test("immutable projection ordering uses authoritative ordinals", () => {
  const projection = {
    sections: [{ id: 2, ordinal: 2 }, { id: 1, ordinal: 1 }],
    concepts: [{ id: 4, ordinal: 4 }, { id: 3, ordinal: 3 }],
  } as ApprovedProjection;
  const ordered = orderedProjection(projection);
  expect(ordered.sections.map((item) => item.id)).toEqual([1, 2]);
  expect(ordered.concepts.map((item) => item.id)).toEqual([3, 4]);
});
