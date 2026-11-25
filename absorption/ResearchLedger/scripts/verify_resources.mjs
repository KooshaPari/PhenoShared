#!/usr/bin/env node
/**
 * Verify the desktop bundle declares every runtime browser-capture resource.
 *
 * This is intentionally a source/config check that runs before `tauri build`.
 * Pass `--bundle <Resources directory>` after packaging to verify the same
 * resources were actually copied into an app bundle.
 */
import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const configPath = path.join(repoRoot, "apps/desktop/src-tauri/tauri.conf.json");
const config = JSON.parse(fs.readFileSync(configPath, "utf8"));

const requiredResources = new Map([
  ["scripts/hackernews_capture.mjs", "scripts/hackernews_capture.mjs"],
  ["scripts/reddit_capture.mjs", "scripts/reddit_capture.mjs"],
  ["scripts/x_capture.mjs", "scripts/x_capture.mjs"],
  ["scripts/_capture_common.mjs", "scripts/_capture_common.mjs"],
  ["scripts/_path_shapes.mjs", "scripts/_path_shapes.mjs"],
  ["node_modules/playwright", "node_modules/playwright"],
  ["node_modules/playwright-core", "node_modules/playwright-core"],
]);

const resources = config.bundle?.resources;
if (!resources || typeof resources !== "object" || Array.isArray(resources)) {
  throw new Error("tauri.conf.json bundle.resources must be an object");
}

const errors = [];
for (const [source, target] of requiredResources) {
  const sourceKey = `../../../${source}`;
  if (resources[sourceKey] !== target) {
    errors.push(`missing resource declaration: ${sourceKey} -> ${target}`);
  }
  const sourcePath = path.join(repoRoot, source);
  if (!fs.existsSync(sourcePath)) {
    errors.push(`declared resource source does not exist: ${sourcePath}`);
  }
}

const bundleIndex = process.argv.indexOf("--bundle");
if (bundleIndex !== -1) {
  const bundleRoot = process.argv[bundleIndex + 1];
  if (!bundleRoot) errors.push("--bundle requires a Resources directory");
  else {
    const resolvedBundle = path.resolve(bundleRoot);
    for (const target of requiredResources.values()) {
      if (!fs.existsSync(path.join(resolvedBundle, target))) {
        errors.push(`packaged resource missing: ${path.join(resolvedBundle, target)}`);
      }
    }
  }
}

if (errors.length > 0) {
  console.error(`Resource parity failed (${errors.length} issue${errors.length === 1 ? "" : "s"}):`);
  for (const error of errors) console.error(`- ${error}`);
  process.exitCode = 1;
} else {
  const suffix = bundleIndex === -1 ? "source declarations" : "source declarations + packaged files";
  console.log(`Resource parity passed: ${requiredResources.size} ${suffix}.`);
}
