import { expect, test } from "@playwright/test";
import { OperationIdempotency } from "../../src/lib/idempotency";
import { pollOperation } from "../../src/lib/polling";
import { ApiError, normalizeApiProblem } from "../../src/services/api";

test("operation idempotency is stable and scoped", () => {
  const keys = new OperationIdempotency();
  const first = keys.key("resource-1", "populate");
  expect(keys.key("resource-1", "populate")).toBe(first);
  expect(keys.key("resource-1", "synchronize")).not.toBe(first);
  keys.retire("resource-1", "populate");
  expect(keys.key("resource-1", "populate")).not.toBe(first);
});

test("API problems retain backend codes, fields, and blockers", () => {
  const problem = normalizeApiProblem(new ApiError("failed", 422, "READINESS_BLOCKED", {
    detail: "Readiness is blocked.",
    idempotency_key: ["Already used."],
    blockers: [{ code: "READINESS_CITATION_COVERAGE_FAILED", message: "Coverage is incomplete." }],
    correlation_id: "correlation-1",
  }));
  expect(problem.status).toBe(422);
  expect(problem.code).toBe("READINESS_BLOCKED");
  expect(problem.fieldErrors?.idempotency_key).toEqual(["Already used."]);
  expect(problem.blockers?.[0].code).toBe("READINESS_CITATION_COVERAGE_FAILED");
  expect(problem.correlationId).toBe("correlation-1");
});

test("polling stops on terminal success without overlapping requests", async () => {
  let calls = 0;
  let concurrent = 0;
  let maximumConcurrent = 0;
  const result = await pollOperation({
    intervalMs: 0,
    request: async () => {
      calls += 1;
      concurrent += 1;
      maximumConcurrent = Math.max(maximumConcurrent, concurrent);
      await Promise.resolve();
      concurrent -= 1;
      return calls;
    },
    isSuccess: (value) => value === 3,
    isFailure: () => false,
  });
  expect(result).toBe(3);
  expect(maximumConcurrent).toBe(1);
});

test("polling cancellation stops an active workflow", async () => {
  const controller = new AbortController();
  const polling = pollOperation({
    signal: controller.signal,
    intervalMs: 0,
    request: async () => "extracting",
    isSuccess: () => false,
    isFailure: () => false,
    onValue: () => controller.abort(),
  });
  await expect(polling).rejects.toMatchObject({ name: "AbortError" });
});

test("transient polling errors retry without becoming processing failures", async () => {
  let calls = 0;
  const result = await pollOperation({
    intervalMs: 0,
    request: async () => {
      calls += 1;
      if (calls === 1) throw new TypeError("temporary network failure");
      return { status: "EXTRACTING", progress: 25 };
    },
    isSuccess: () => true,
    isFailure: () => false,
    shouldRetryError: (error) => error instanceof TypeError,
  });
  expect(result).toEqual({ status: "EXTRACTING", progress: 25 });
  expect(calls).toBe(2);
});
