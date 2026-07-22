import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

import { findUnresolvedApiTargets, scanApiTargetsFromContent } from "./audit-lib.mjs";

const scriptFile = fileURLToPath(import.meta.url);
const scriptDir = path.dirname(scriptFile);
const frontendRoot = path.resolve(scriptDir, "..");
const manifestPath = path.join(frontendRoot, "testing", "mvp-route-contract.json");
const fixturesRoot = path.join(frontendRoot, "testing", "fixtures", "audit");
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));

test("known finite auth endpoints resolve against the route contract", () => {
  const content = fs.readFileSync(path.join(fixturesRoot, "known-auth-endpoints.ts"), "utf8");
  const apiTargets = scanApiTargetsFromContent(content, "testing/fixtures/audit/known-auth-endpoints.ts");
  const unresolved = findUnresolvedApiTargets(apiTargets, manifest.backendEndpoints);

  assert.equal(
    unresolved.length,
    0,
    `Unresolved API targets:\n${unresolved.map((item) => JSON.stringify(item)).join("\n")}`,
  );
});

test("unknown dynamic endpoint expressions remain unresolved", () => {
  const content = fs.readFileSync(path.join(fixturesRoot, "unknown-dynamic-endpoint.ts"), "utf8");
  const apiTargets = scanApiTargetsFromContent(content, "testing/fixtures/audit/unknown-dynamic-endpoint.ts");
  const unresolved = findUnresolvedApiTargets(apiTargets, manifest.backendEndpoints);

  assert.deepEqual(
    unresolved.map((entry) => entry.path),
    ["content-intelligence/${resourceName}/status/"],
  );
});

test("implemented PI-6D dynamic endpoints resolve against the route contract", () => {
  const content = `
    apiRequest(\`academic-review/projections/\${projectionId}/population-readiness/\`);
    apiRequest(\`academic-review/projections/\${projectionId}/populate/\`);
    apiRequest(\`academic-review/sessions/\${sessionId}/resolve-finding/\`);
    apiRequest(\`academic/learning-resources/\${resourceId}/teaching-readiness/\`);
    apiRequest(\`academic/learning-resources/\${resourceId}/teaching-readiness/evaluate/\`);
    apiRequest(\`content-processing/teaching-readiness/evaluations/\${evaluationId}/\`);
    apiRequest(\`academic-review/population-runs/\${populationRunId}/retrieval-readiness/\`);
    apiRequest(\`academic-review/population-runs/\${populationRunId}/synchronize-retrieval/\`);
    apiRequest(\`retrieval/synchronization-runs/\${runId}/\`);
    apiRequest(\`content-processing/jobs/\${jobId}/\`);
    apiRequest(\`content-processing/jobs/\${jobId}/attempts/\`);
    apiRequest(\`content-processing/jobs/\${jobId}/diagnostics/\`);
    apiRequest(\`content-processing/jobs/\${jobId}/retry/\`);
    apiRequest(\`content-processing/jobs/\${jobId}/cancel/\`);
    apiRequest(\`academic-review/population-runs/\${runId}/\`);
  `;
  const apiTargets = scanApiTargetsFromContent(content, "src/features/pi-6d/api.ts");

  assert.deepEqual(findUnresolvedApiTargets(apiTargets, manifest.backendEndpoints), []);
});

test("incorrect endpoint spelling and missing trailing slash remain unresolved", () => {
  const content = `
    apiRequest(\`academic-review/approved-projections/\${projectionId}/populate/\`);
    apiRequest(\`content-processing/jobs/\${jobId}/retry\`);
  `;
  const apiTargets = scanApiTargetsFromContent(content, "src/features/invalid/api.ts");
  const unresolved = findUnresolvedApiTargets(apiTargets, manifest.backendEndpoints);

  assert.deepEqual(
    unresolved.map((entry) => entry.path),
    [
      "academic-review/approved-projections/${projectionId}/populate/",
      "content-processing/jobs/${jobId}/retry",
    ],
  );
});

test("duplicate discoveries in one source are reported once", () => {
  const duplicate = {
    source: "src/features/invalid/api.ts",
    path: "content-processing/jobs/${jobId}/missing/",
  };

  assert.deepEqual(
    findUnresolvedApiTargets([duplicate, { ...duplicate }], manifest.backendEndpoints),
    [duplicate],
  );
});

test("planned frontend routes are not implemented API contracts", () => {
  const deferredFrontendRoute = manifest.frontendRoutes.find(
    (entry) => entry.route === "/dashboard/remediation/:planId",
  );
  const apiTargets = scanApiTargetsFromContent(
    "apiRequest(`dashboard/remediation/${planId}/`);",
    "src/features/remediation/api.ts",
  );

  assert.equal(deferredFrontendRoute?.status, "deferred");
  assert.equal(findUnresolvedApiTargets(apiTargets, manifest.backendEndpoints).length, 1);
});

test("PI-6E.2 review workspace is an implemented reviewer route", () => {
  assert.deepEqual(
    manifest.frontendRoutes.find(
      (entry) => entry.route === "/dashboard/academic-review/:proposalId",
    ),
    {
      route: "/dashboard/academic-review/:proposalId",
      auth: "reviewer",
      status: "implemented",
      description: "PI-6E.2 governed human-review workspace; completion ends at ready for approval",
    },
  );
});

test("PI-6E.3 governance workspace is an implemented reviewer route", () => {
  assert.deepEqual(
    manifest.frontendRoutes.find(
      (entry) => entry.route === "/dashboard/academic-review/:proposalId/governance",
    ),
    {
      route: "/dashboard/academic-review/:proposalId/governance",
      auth: "reviewer",
      status: "implemented",
      description: "PI-6E.3 approval, immutable projection, and Academic population workspace",
    },
  );
});

test("PI-6F.1 self-study policy endpoints resolve against the route contract", () => {
  const routes = manifest.backendEndpoints;
  for (const [path, method] of [
    ["self-study/intents/", "POST"],
    ["self-study/intents/:intentId/activate/", "POST"],
    ["self-study/intents/:intentId/policy/", "GET"],
    ["self-study/intents/:intentId/authorize-resource/", "POST"],
  ]) {
    assert.ok(routes.some((route) => route.path === path && route.method === method && route.status === "implemented"));
  }
});

test("known pathname resolves when its query value is dynamic", () => {
  const targets = scanApiTargetsFromContent(
    "apiRequest(`content-processing/jobs/?resource=${encodeURIComponent(resourceId)}`);",
    "src/features/content-processing/api.ts",
  );
  assert.deepEqual(findUnresolvedApiTargets(targets, manifest.backendEndpoints), []);
});

test("query removal preserves strict pathname spelling and trailing slashes", () => {
  const targets = scanApiTargetsFromContent(
    `
      apiRequest(\`content-processing/jobz/?resource=\${encodeURIComponent(resourceId)}\`);
      apiRequest(\`content-processing/jobs?resource=\${encodeURIComponent(resourceId)}\`);
    `,
    "src/features/content-processing/invalid-api.ts",
  );
  assert.deepEqual(
    findUnresolvedApiTargets(targets, manifest.backendEndpoints).map((entry) => entry.path),
    [
      "content-processing/jobz/?resource=${encodeURIComponent(resourceId)}",
      "content-processing/jobs?resource=${encodeURIComponent(resourceId)}",
    ],
  );
});

test("dynamic pathnames remain contract-governed after query removal", () => {
  const targets = scanApiTargetsFromContent(
    `
      apiRequest(\`content-processing/jobs/\${jobId}/?view=summary\`);
      apiRequest(\`content-processing/unknown/\${jobId}/?view=summary\`);
    `,
    "src/features/content-processing/dynamic-api.ts",
  );
  assert.deepEqual(
    findUnresolvedApiTargets(targets, manifest.backendEndpoints).map((entry) => entry.path),
    ["content-processing/unknown/${jobId}/?view=summary"],
  );
});

test("discarding a query cannot match an unrelated endpoint", () => {
  const targets = scanApiTargetsFromContent(
    "apiRequest(`retrieval/not-a-synchronization-run/?run=${runId}`);",
    "src/features/retrieval/invalid-api.ts",
  );
  assert.equal(findUnresolvedApiTargets(targets, manifest.backendEndpoints).length, 1);
});

test("PI-6F.2 curriculum registry and resolver endpoints are governed", () => {
  const routes = manifest.backendEndpoints;
  for (const [path, method] of [
    ["self-study/intents/:intentId/curriculum-resolution/", "POST"],
    ["self-study/curriculum-resolutions/:attemptId/", "GET"],
    ["curricula/:curriculumId/versions/:versionId/", "GET"],
    ["curriculum-registry/authorities/:authorityId/verify/", "POST"],
    ["curriculum-registry/versions/:versionId/activate/", "POST"],
  ]) {
    assert.ok(routes.some((route) => route.path === path && route.method === method));
  }
});

test("PI-6F.6 bridge planning and handoff endpoints are governed", () => {
  const routes = manifest.backendEndpoints;
  for (const [path, method] of [
    ["self-study/bridge-planning-runs/", "POST"],
    ["self-study/bridge-planning-runs/:runId/plan/", "GET"],
    ["self-study/bridge-plans/:planId/nodes/", "GET"],
    ["self-study/bridge-plans/:planId/dependencies/", "GET"],
    ["self-study/bridge-plans/:planId/approve/", "POST"],
    ["self-study/bridge-plans/:planId/activate/", "POST"],
    ["self-study/bridge-plans/current-handoff/:intentId/", "GET"],
  ]) {
    assert.ok(routes.some((route) => route.path === path && route.method === method && route.status === "implemented"));
  }
});
