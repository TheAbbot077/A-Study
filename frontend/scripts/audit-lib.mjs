import fs from "node:fs";
import path from "node:path";

function extractConstStringMaps(content) {
  const maps = new Map();
  const objectPattern =
    /const\s+([A-Za-z_$][\w$]*)\s*=\s*\{([\s\S]*?)\}\s*as\s+const/g;

  for (const match of content.matchAll(objectPattern)) {
    const [, objectName, objectBody] = match;
    const entries = new Map();
    const entryPattern =
      /([A-Za-z_$][\w$]*)\s*:\s*["'`]([^"'`]+)["'`]\s*,?/g;

    for (const entryMatch of objectBody.matchAll(entryPattern)) {
      const [, key, value] = entryMatch;
      entries.set(key, value);
    }

    if (entries.size > 0) {
      maps.set(objectName, entries);
    }
  }

  return maps;
}

function expandKnownTemplateReferences(rawPath, stringMaps) {
  return rawPath.replace(
    /\$\{([A-Za-z_$][\w$]*)\.([A-Za-z_$][\w$]*)\}/g,
    (fullMatch, objectName, propertyName) => {
      const objectMap = stringMaps.get(objectName);
      const value = objectMap?.get(propertyName);
      return value ?? fullMatch;
    },
  );
}

export function walkFiles(rootDir, predicate, onMissing) {
  if (!fs.existsSync(rootDir)) {
    if (onMissing) {
      onMissing(rootDir);
      return [];
    }
    throw new Error(`Required directory does not exist: ${rootDir}`);
  }

  const results = [];
  const stack = [rootDir];

  while (stack.length > 0) {
    const current = stack.pop();
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const resolved = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(resolved);
        continue;
      }
      if (!predicate || predicate(resolved)) {
        results.push(resolved);
      }
    }
  }

  return results;
}

export function routeFromPageFile(filePath, appRoot) {
  const relative = path.relative(appRoot, filePath).replace(/\\/g, "/");
  const withoutPage = relative.replace(/\/page\.tsx$/, "").replace(/^page\.tsx$/, "");
  if (!withoutPage) {
    return "/";
  }

  return (
    "/" +
    withoutPage
      .split("/")
      .map((segment) => {
        if (/^\[\.\.\.(.+)\]$/.test(segment)) {
          return `:${segment.slice(4, -1)}*`;
        }
        if (/^\[\[(?:\.\.\.)?(.+)\]\]$/.test(segment)) {
          return `:${segment.replace(/^\[\[(?:\.\.\.)?/, "").replace(/\]\]$/, "")}*`;
        }
        if (/^\[(.+)\]$/.test(segment)) {
          return `:${segment.slice(1, -1)}`;
        }
        return segment;
      })
      .join("/")
  );
}

export function normalizeTarget(target) {
  return (
    target
      .split("?")[0]
      .split("#")[0]
      .replace(/\$\{[^}]+\}/g, ":param")
      .replace(/\/+/g, "/")
      .replace(/\/$/, "") || "/"
  );
}

export function routePatternToRegex(routePattern) {
  const escaped = routePattern
    .replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    .replace(/:([A-Za-z0-9_]+)\*/g, ".+")
    .replace(/:([A-Za-z0-9_]+)/g, "[^/]+");
  return new RegExp(`^${escaped}$`);
}

export function normalizeApiPath(rawPath) {
  const withoutQueryOrFragment = rawPath.split(/[?#]/, 1)[0];
  const withoutOrigin = withoutQueryOrFragment.replace(/^https?:\/\/[^/]+/i, "");
  const withoutApiPrefix = withoutOrigin.replace(/^\/?api\//, "");
  const normalizedBase = withoutApiPrefix.startsWith("/")
    ? withoutApiPrefix.slice(1)
    : withoutApiPrefix;
  return {
    pathname: normalizedBase.replace(/\$\{[^}]+\}/g, ":param"),
  };
}

export function scanNavigationTargets(files, frontendRoot) {
  const patterns = [
    /href\s*=\s*["'`]([^"'`]+)["'`]/g,
    /href\s*=\s*\{\s*["'`]([^"'`]+)["'`]\s*\}/g,
    /href\s*=\s*\{\s*\`([^`]+)\`\s*\}/g,
    /router\.(?:push|replace)\(\s*["'`]([^"'`]+)["'`]/g,
    /router\.(?:push|replace)\(\s*\`([^`]+)\`/g,
    /new URL\(\s*["'`]([^"'`]+)["'`]/g,
  ];

  const targets = [];
  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    for (const pattern of patterns) {
      for (const match of content.matchAll(pattern)) {
        const target = match[1];
        if (!target?.startsWith("/")) {
          continue;
        }
        targets.push({
          source: path.relative(frontendRoot, file).replace(/\\/g, "/"),
          target,
        });
      }
    }
  }
  return targets;
}

export function scanApiTargetsFromContent(content, source) {
  const targets = [];
  const stringMaps = extractConstStringMaps(content);
  const patterns = [
    /apiRequest(?:<[^>]+>)?\(\s*["']([^"']+)["']/g,
    /apiRequest(?:<[^>]+>)?\(\s*\`([^`]+)\`/g,
    /fetch\(\s*\`[^`]*\/api\/([^`]+)\`/g,
  ];

  for (const pattern of patterns) {
    for (const match of content.matchAll(pattern)) {
      targets.push({
        source,
        path: expandKnownTemplateReferences(match[1], stringMaps),
      });
    }
  }

  return targets;
}

export function scanApiTargets(files, frontendRoot) {
  const targets = [];
  for (const file of files) {
    const content = fs.readFileSync(file, "utf8");
    targets.push(
      ...scanApiTargetsFromContent(content, path.relative(frontendRoot, file).replace(/\\/g, "/")),
    );
  }
  return targets;
}

export function findUnresolvedApiTargets(apiTargets, backendEndpoints) {
  const backendPatterns = backendEndpoints
    .filter((entry) => entry.status === "implemented")
    .map((entry) => ({
      ...entry,
      regex: routePatternToRegex(entry.path),
    }));

  const unresolved = apiTargets.filter(({ path: rawPath }) => {
    const normalized = normalizeApiPath(rawPath);
    return !backendPatterns.some((entry) => {
      return entry.regex.test(normalized.pathname);
    });
  });

  return [
    ...new Map(
      unresolved.map((entry) => {
        const normalized = normalizeApiPath(entry.path);
        const identity = `${entry.source}:${normalized.pathname}`;
        return [identity, entry];
      }),
    ).values(),
  ];
}
