#!/usr/bin/env node
/**
 * ResearchLedger – Hacker News "saved stories" capture.
 *
 * Opens news.ycombinator.com in a persistent Chromium profile so the user's
 * authentication session is reused across runs, navigates to
 * `/saved?id=<username>`, scrolls the page in bounded rounds (HN has finite
 * pagination — we cap `unchangedAbort` aggressively so a short saved
 * queue doesn't loop for minutes), deduplicates on the canonical
 * `https://news.ycombinator.com/item?id=<id>` permalink, and writes the
 * captured posts to a JSON file the Tauri desktop app can import
 * (`import_hackernews_capture`) into the vault.
 *
 * Usage:
 *   node scripts/hackernews_capture.mjs --output <path>
 *       [--profile <dir>] [--url <saved-url>]
 *       [--max-rounds N] [--wait-ms MS] [--min-length CHARS]
 *
 * Privacy: this script never sends data to a third party. Cookies,
 * session tokens, and the captured text stay in the user's profile
 * directory and the output file. The `USERNAME` placeholder in the
 * default URL must be replaced with the user's HN username; if it is
 * not, this script bails with a friendly `AUTH_REQUIRED`-style message
 * before opening any session so the user is not silently disturbed by
 * a Chromium window they cannot complete the login flow inside.
 */
import {
  openAuthenticatedSession,
  scrollAndCollect,
  getProbe,
  writeCapture,
  loadPlaywright,
  parseFlags,
  defaultCapturePath,
} from "./_capture_common.mjs";

const flags = parseFlags(process.argv);
const output = flags.get("--output") ?? defaultCapturePath("hackernews");
const profile = flags.get("--profile")
  ?? `${process.env.HOME}/Library/Application Support/ResearchLedger/hackernews-profile`;
const url = flags.get("--url") ?? "https://news.ycombinator.com/saved?id=USERNAME";
// HN's saved-stories queue is finite (the `/saved` listing is paginated
// and most users have a small handful); cap the scroll budget so we don't
// spend forever in an empty window. `scrollAndCollect` also aborts early
// after a string of unchanged rounds.
const maxRounds = Number(flags.get("--max-rounds") ?? 30);
const waitMs = Number(flags.get("--wait-ms") ?? 1000);
const minLength = Number(flags.get("--min-length") ?? 40);

if (url.includes("USERNAME")) {
  console.error(
    "AUTH_REQUIRED: default --url still contains the USERNAME placeholder — sign in to news.ycombinator.com in the launched window, then re-run capture with `--url https://news.ycombinator.com/saved?id=<your-username>`.",
  );
  process.exit(2);
}

const { chromium } = await loadPlaywright();

const { context, page } = await openAuthenticatedSession({
  chromium,
  profile,
  url,
  logMessage:
    "ResearchLedger Hacker News capture is running in the authenticated profile. Complete login if prompted.",
});

const probe = getProbe({ mode: "hn-athing" });
const posts = await scrollAndCollect({
  page,
  selector: "tr.athing.submission a.titlelink",
  probe,
  build: (sample) => ({
    id: /** @type {{id: string}} */ (sample).id,
    url: /** @type {{href: string}} */ (sample).href,
    text: /** @type {{text: string}} */ (sample).text,
    author: "",
    title: "",
  }),
  minLength,
  maxRounds,
  waitMs,
});

const payload = {
  version: 1,
  capturedAt: new Date().toISOString(),
  source: "hackernews-playwright-authenticated-session",
  provider: "hackernews",
  savedUrl: url,
  posts: [...posts.values()],
};

await writeCapture(
  output,
  payload,
  `Captured ${payload.posts.length} unique Hacker News saved stories to ${output}`,
);
await context.close();
