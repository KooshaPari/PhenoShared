#!/usr/bin/env node
/**
 * ResearchLedger – postinstall hook.
 *
 * Runs `bunx playwright install chromium` automatically when `bun install`
 * completes, so users never see the "Browser not installed" prompt at
 * first capture. The capture scripts (`scripts/_capture_common.mjs`) still
 * run a lazy auto-install as a safety net for users who skip bun install.
 *
 * Idempotent:
 *   - Playwright's install is a no-op if the browser is already cached at
 *     ~/Library/Caches/ms-playwright (macOS) / %LOCALAPPDATA%\ms-playwright
 *     (Windows) / ~/.cache/ms-playwright (Linux).
 *
 * Quiet:
 *   - Skipped entirely when CI=1 or PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1.
 *
 * Non-fatal:
 *   - Exits 0 even on install failure so a transient network / permission
 *     issue doesn't break `bun install`. The capture-time auto-install
 *     remains the safety net.
 *
 * Platform handling:
 *   - macOS / Windows: `bunx playwright install chromium`
 *   - Linux: `bunx playwright install chromium --with-deps` first (needs
 *     sudo / root for system libraries). If `--with-deps` fails, fall
 *     back to a plain `install chromium` and warn the user that they may
 *     need to install system libs manually.
 */

import { spawn } from "node:child_process";
import process from "node:process";

const TAG = "[researchledger/postinstall]";

/** @returns {boolean} */
function shouldSkip() {
  if (process.env.PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD === "1") return true;
  if (process.env.CI === "1" || process.env.CI === "true") return true;
  return false;
}

/**
 * Run a command, inheriting stdio so the user sees progress. Resolves on
 * exit 0; rejects on any non-zero exit (or spawn error) so the caller can
 * decide whether to swallow the failure.
 *
 * @param {string} cmd
 * @param {readonly string[]} args
 * @returns {Promise<void>}
 */
function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { stdio: "inherit" });
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${cmd} ${args.join(" ")} exited with code ${code ?? "null"}`));
    });
  });
}

/**
 * @returns {"mac" | "linux" | "windows" | "unknown"}
 */
function detectPlatform() {
  if (process.platform === "darwin") return "mac";
  if (process.platform === "linux") return "linux";
  if (process.platform === "win32") return "windows";
  return "unknown";
}

async function main() {
  if (shouldSkip()) {
    console.log(`${TAG} skipped (CI=1 or PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1)`);
    return;
  }

  const platform = detectPlatform();
  console.log(`${TAG} ensuring Playwright Chromium is installed (one-time, ~150 MB)…`);

  // Always run via `bunx playwright` so users without a global Playwright still
  // resolve the binary out of node_modules.
  const baseArgs = ["playwright", "install", "chromium"];

  try {
    if (platform === "linux") {
      try {
        await run("bunx", [...baseArgs, "--with-deps"]);
        console.log(`${TAG} Chromium ready.`);
        return;
      } catch (err) {
        console.warn(
          `${TAG} --with-deps failed (likely needs sudo / root): ${err.message}`,
        );
        console.warn(`${TAG} falling back to plain install; system libs may be missing.`);
      }
    }
    await run("bunx", baseArgs);
    console.log(`${TAG} Chromium ready.`);
  } catch (err) {
    // Non-fatal: capture-time auto-install remains as a safety net.
    console.warn(
      `${TAG} browser install failed (${err.message}). ` +
        `The first capture will retry automatically, or run \`bunx playwright install chromium\` manually.`,
    );
    // Exit 0 — bun install must not fail because the browser download failed.
  }
}

main().catch((err) => {
  console.warn(`${TAG} unexpected error: ${err.message ?? err}`);
  // Exit 0 — same non-fatal policy as above.
});
