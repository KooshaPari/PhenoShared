#!/usr/bin/env node
/**
 * Ensure the desktop renderer CSP remains narrow and keeps Vite-only access out
 * of production builds. Native Rust/provider requests are not renderer CSP
 * traffic and must not be added here.
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const configPath = path.join(repoRoot, "apps/desktop/src-tauri/tauri.conf.json");

function sourceList(csp, directive) {
  const value = csp?.[directive];
  return Array.isArray(value) ? value : typeof value === "string" ? value.split(/\s+/) : [];
}

function requireSources(csp, directive, sources, label, errors) {
  const actual = sourceList(csp, directive);
  for (const source of sources) {
    if (!actual.includes(source)) errors.push(`${label} ${directive} is missing ${source}`);
  }
}

function isForbiddenProductionSource(source) {
  if (source === "*" || source.startsWith("ws:") || source.startsWith("wss:")) return true;
  try {
    const url = new URL(source);
    const hostname = url.hostname.replace(/^\[|\]$/g, "");
    return ["http:", "https:"].includes(url.protocol)
      && ["localhost", "127.0.0.1", "::1"].includes(hostname)
      && !["ipc.localhost", "asset.localhost"].includes(hostname);
  } catch {
    return false;
  }
}

export function verifyCspConfig(config) {
  const security = config.app?.security;
  const errors = [];
  if (!security || typeof security.csp !== "object" || Array.isArray(security.csp)) {
    errors.push("app.security.csp must be a structured production CSP");
  } else {
    const production = security.csp;
    requireSources(production, "default-src", ["'self'", "customprotocol:", "asset:"], "production", errors);
    requireSources(production, "connect-src", ["ipc:", "http://ipc.localhost"], "production", errors);
    requireSources(production, "img-src", ["'self'", "asset:", "http://asset.localhost"], "production", errors);
    requireSources(production, "base-uri", ["'none'"], "production", errors);
    requireSources(production, "form-action", ["'none'"], "production", errors);
    requireSources(production, "object-src", ["'none'"], "production", errors);
    for (const [directive, sources] of Object.entries(production)) {
      for (const source of sourceList({ [directive]: sources }, directive)) {
        if (isForbiddenProductionSource(source)) {
          errors.push(`production ${directive} must not allow development or wildcard source ${source}`);
        }
      }
    }
  }
  if (!security || typeof security.devCsp !== "object" || Array.isArray(security.devCsp)) {
    errors.push("app.security.devCsp must preserve the local Vite development flow");
  } else {
    requireSources(security.devCsp, "connect-src", ["http://127.0.0.1:5173", "ws://127.0.0.1:5173"], "development", errors);
  }
  return errors;
}

function main() {
  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  const errors = verifyCspConfig(config);
  if (errors.length > 0) {
    console.error(`CSP verification failed (${errors.length} issue${errors.length === 1 ? "" : "s"}):`);
    for (const error of errors) console.error(`- ${error}`);
    process.exitCode = 1;
  } else {
    console.log("CSP verification passed: production is limited to Tauri assets and IPC.");
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main();
}
