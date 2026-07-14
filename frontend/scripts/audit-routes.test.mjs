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
