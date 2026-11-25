#!/usr/bin/env node
/**
 * ResearchLedger – X (Twitter) bookmarks capture.
 *
 * Opens x.com in a persistent Chromium profile so the user's authentication
 * session is reused across runs, navigates to /i/bookmarks, scrolls the
 * page in bounded rounds, deduplicates on the canonical
 * https://x.com/<user>/status/<id> URL, and writes the captured posts to a
 * JSON file the Tauri desktop app can import into the vault.
 *
 * Usage:
 *   node scripts/x_capture.mjs --output <path>
 *       [--profile <dir>] [--url <bookmarks-url>]
 *       [--max-rounds N] [--wait-ms MS] [--min-length CHARS]
 *
 * Privacy: this script never sends data to a third party. Cookies,
 * session tokens, and the captured text stay in the user's profile
 * directory and the output file.
 */
import { makeProviderBuilder, runCaptureSession } from "./_capture_common.mjs";

await runCaptureSession({
  providerName: "X",
  argv: process.argv,
  profileSubdir: "x",
  defaultUrl: "https://x.com/i/bookmarks",
  probeMode: "x-article",
  selector: "a[href*='/status/']",
  build: makeProviderBuilder("x"),
});
