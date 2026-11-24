#!/usr/bin/env node
/**
 * ResearchLedger – Reddit "saved" post capture.
 *
 * Opens Reddit in a persistent Chromium profile so the user's authentication
 * session is reused across runs, navigates to /user/<name>/saved, scrolls
 * the page in bounded rounds, deduplicates on the canonical
 * /r/<sub>/comments/<id>/ URL, and writes the captured posts to a JSON
 * file the Tauri desktop app can import into the vault.
 *
 * Usage:
 *   node scripts/reddit_capture.mjs --output <path>
 *       [--profile <dir>] [--url <saved-url>]
 *       [--max-rounds N] [--wait-ms MS] [--min-length CHARS]
 *
 * Privacy: this script never sends data to a third party. Cookies,
 * session tokens, and the captured text stay in the user's profile
 * directory and the output file.
 */
import { makeProviderBuilder, runCaptureSession } from "./_capture_common.mjs";

await runCaptureSession({
  providerName: "Reddit",
  argv: process.argv,
  profileSubdir: "reddit",
  defaultUrl: "https://www.reddit.com/user/saved",
  probeMode: "reddit-article",
  selector: "a[href*='/r/'][href*='/comments/']",
  build: makeProviderBuilder("reddit"),
});
