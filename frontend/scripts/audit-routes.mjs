import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  findUnresolvedApiTargets,
  normalizeTarget,
  routeFromPageFile,
  routePatternToRegex,
  scanApiTargets,
  scanNavigationTargets,
  walkFiles,
} from "./audit-lib.mjs";

const scriptFile = fileURLToPath(import.meta.url);
const scriptDir = path.dirname(scriptFile);
const frontendRoot = path.resolve(scriptDir, "..");
const appRoot = path.join(frontendRoot, "src", "app");
const srcRoot = path.join(frontendRoot, "src");
const manifestPath = path.join(frontendRoot, "testing", "mvp-route-contract.json");

function failWithPathContext(message) {
  console.error(message);
  console.error(`Resolved frontend root: ${frontendRoot}`);
  console.error(`Expected manifest path: ${manifestPath}`);
  process.exit(1);
}

if (!fs.existsSync(manifestPath)) {
  failWithPathContext("Route contract manifest is missing.");
}

const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const pageFiles = walkFiles(appRoot, (file) => file.endsWith("page.tsx"), (missingPath) =>
  failWithPathContext(`Required directory does not exist: ${missingPath}`),
);
const sourceFiles = walkFiles(srcRoot, (file) => /\.(ts|tsx)$/.test(file), (missingPath) =>
  failWithPathContext(`Required directory does not exist: ${missingPath}`),
);

const discoveredRoutes = [...new Set(pageFiles.map((file) => routeFromPageFile(file, appRoot)))].sort();
const implementedManifestRoutes = manifest.frontendRoutes
  .filter((route) => route.status === "implemented")
  .map((route) => route.route)
  .sort();

const missingDeclaredRoutes = implementedManifestRoutes.filter((route) => !discoveredRoutes.includes(route));
const unexpectedRoutes = discoveredRoutes.filter((route) => !manifest.frontendRoutes.some((entry) => entry.route === route));

const routeRegexes = implementedManifestRoutes.map((route) => ({
  route,
  regex: routePatternToRegex(route),
}));

const navigationTargets = scanNavigationTargets(sourceFiles, frontendRoot);
const unresolvedNavigation = navigationTargets.filter(({ target }) => {
  const normalized = normalizeTarget(target);
  return !routeRegexes.some(({ regex }) => regex.test(normalized));
});

const apiTargets = scanApiTargets(sourceFiles, frontendRoot);
const unresolvedApiTargets = findUnresolvedApiTargets(apiTargets, manifest.backendEndpoints);

console.log("MVP Route Audit");
console.log("================");
console.log(`Discovered app routes: ${discoveredRoutes.length}`);
console.log(`Manifest routes: ${implementedManifestRoutes.length} implemented / ${manifest.frontendRoutes.length} total`);
console.log(`Navigation targets scanned: ${navigationTargets.length}`);
console.log(`API targets scanned: ${apiTargets.length}`);

if (missingDeclaredRoutes.length > 0) {
  console.log("\nMissing implemented frontend routes:");
  for (const route of missingDeclaredRoutes) {
    console.log(`- ${route}`);
  }
}

if (unexpectedRoutes.length > 0) {
  console.log("\nRoutes present in src/app but missing from the route contract:");
  for (const route of unexpectedRoutes) {
    console.log(`- ${route}`);
  }
}

if (unresolvedNavigation.length > 0) {
  console.log("\nUnresolved navigation targets:");
  for (const issue of unresolvedNavigation) {
    console.log(`- ${issue.target} (${issue.source})`);
  }
}

if (unresolvedApiTargets.length > 0) {
  console.log("\nUnresolved API targets:");
  for (const issue of unresolvedApiTargets) {
    console.log(`- ${issue.path} (${issue.source})`);
  }
}

if (
  missingDeclaredRoutes.length > 0 ||
  unexpectedRoutes.length > 0 ||
  unresolvedNavigation.length > 0 ||
  unresolvedApiTargets.length > 0
) {
  process.exitCode = 1;
} else {
  console.log("\nNo broken static route or API references found.");
}
