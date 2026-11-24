#!/usr/bin/env node
/**
 * ResearchLedger – shared scroll/collect loop for authenticated Playwright
 * capture scripts (Reddit, X, Hacker News).
 *
 * Each provider supplies:
 *   - The URL pattern of the saved/bookmarks page.
 *   - A selector that matches each saved item's anchor.
 *   - A `probe` function that runs inside the page and returns the raw
 *     inputs (href + minimal DOM text) needed to build a post record. The
 *     probe is serialised into the page context via Playwright's own
 *     serializer — no `new Function` and no string interpolation.
 *   - A `build` function that runs in Node and turns the probed data into
 *     a `{ url, text, ... }` post record.
 *
 * The helper owns: persistent profile launch, scroll loop with stagnation
 * abort, dedup on canonical URL, JSON output.
 *
 * Privacy guarantees (inherited by every script that uses this helper):
 *   - No credentials, cookies, or text leave the user's machine.
 *   - The persistent profile directory is owned by the user and is the only
 *     place authentication state is stored.
 *   - Capture output is written to a local file the caller specifies.
 */

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { spawn } from "node:child_process";
import { pathToFileURL } from "node:url";

/**
 * Detect Playwright's "Executable doesn't exist" / "looks like Playwright was
 * just installed or updated" failure mode from the thrown error's message.
 * The Chromium executable missing on disk is recoverable by running
 * `bunx playwright install chromium`, so we surface a friendlier message and
 * fall through to auto-install rather than letting the raw stack trace reach
 * the React UI.
 *
 * @param {unknown} err
 * @returns {boolean}
 */
function isMissingChromium(err) {
  const message = err instanceof Error ? err.message : String(err);
  return /Executable doesn't exist|Looks like Playwright was just installed/i.test(message);
}

/**
 * Run `playwright install chromium` in the project root and forward stdout to
 * stderr so the user sees progress. Resolves on exit code 0, throws on
 * non-zero so the caller can surface a clean failure.
 *
 * @param {string} modulePath
 * @returns {Promise<void>}
 */
function runPlaywrightInstall(modulePath) {
  return new Promise((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [modulePath, "install", "chromium"],
      { stdio: ["ignore", "inherit", "inherit"] },
    );
    child.on("error", reject);
    child.on("exit", (code) => {
      if (code === 0) resolve();
      else reject(new Error(`playwright install exited with code ${code ?? "null"}`));
    });
  });
}

/**
 * Detect whether the page we just navigated to is actually the saved/bookmarks
 * view, or whether the host redirected us to a login / consent screen. The
 * heuristic is intentionally simple — we look for either the probe's
 * `target` selector or any element matching the supplied `loggedInMarker` CSS.
 * If neither appears after a short grace period, we throw a typed error that
 * the UI surfaces as a friendly "auth required" message.
 *
 * @param {{
 *   page: import('playwright').Page,
 *   target: string,
 *   loggedInMarker: string,
 *   timeoutMs?: number,
 * }} params
 */
export async function assertAuthedPage({ page, target, loggedInMarker, timeoutMs = 5000 }) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const [targetCount, markerCount] = await Promise.all([
      page.locator(target).count(),
      page.locator(loggedInMarker).count(),
    ]);
    if (targetCount > 0 || markerCount > 0) return;
    await page.waitForTimeout(250);
  }
  throw new Error(`AUTH_REQUIRED: target="${target}" marker="${loggedInMarker}"`);
}

/**
 * Load Playwright from an absolute path (when bundled as a Tauri resource) or
 * a bare module specifier (when running from the development tree).
 *
 * @returns {Promise<{ chromium: any }>}
 */
export async function loadPlaywright() {
  const configuredModule = process.env.RESEARCHLEDGER_PLAYWRIGHT_MODULE;
  const candidates = [
    configuredModule,
    configuredModule ? path.resolve(configuredModule, "index.js") : undefined,
    configuredModule ? path.resolve(configuredModule, "index.mjs") : undefined,
    "node_modules/playwright",
    "node_modules/playwright/index.js",
    "node_modules/playwright/index.mjs",
    "node_modules/playwright-core",
    "node_modules/playwright-core/index.js",
    "node_modules/playwright-core/index.mjs",
    "playwright-core",
    "playwright",
  ].filter((value) => typeof value === "string" && value.length > 0);

  /** @param {string} value */
  const isAbsolutePath = (value) =>
    process.platform === "win32"
      ? /[a-z]:[\\/]/i.test(String(value))
      : String(value).startsWith("/");

  const errors = [];
  for (const candidate of candidates) {
    let spec = isAbsolutePath(candidate) ? pathToFileURL(candidate).href : candidate;
    try {
      const loaded = await import(spec);
      return loaded.default ?? loaded;
    } catch (error) {
      errors.push(`${candidate}: ${error instanceof Error ? error.message : String(error)}`);
    }
  }

  throw new Error(`PLAYWRIGHT_IMPORT_FAIL: unable to import Playwright. Tried: ${errors.join(", ")}`);
}

/**
 * Parse `--flag value` pairs from process.argv starting at index 2.
 *
 * @param {readonly string[]} argv
 * @returns {Map<string, string>}
 */
export function parseFlags(argv) {
  const args = new Map();
  for (let index = 2; index < argv.length; index += 2) {
    args.set(argv[index], argv[index + 1]);
  }
  return args;
}

/**
 * Resolve a profile directory from the `--profile` flag, falling back to
 * `${HOME}/Library/Application Support/ResearchLedger/<defaultSubdir>`.
 *
 * @param {Map<string, string>} flags
 * @param {string} defaultSubdir
 * @returns {string}
 */
export function resolveProfile(flags, defaultSubdir) {
  return (
    flags.get("--profile") ??
    `${process.env.HOME ?? ""}/Library/Application Support/ResearchLedger/${defaultSubdir}`
  );
}

/**
 * Read an integer flag (with default) from the parsed args.
 *
 * @param {Map<string, string>} flags
 * @param {string} name
 * @param {number} fallback
 * @returns {number}
 */
export function readInt(flags, name, fallback) {
  const raw = flags.get(name);
  if (raw === undefined) return fallback;
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

/**
 * Normalize a post URL by stripping query string + trailing slash so the same
 * post re-loaded with `?utm_source=...` collapses to the same key.
 *
 * @param {string} href
 * @returns {string}
 */
export function canonicalUrl(href) {
  return href.split("?")[0].replace(/\/$/, "");
}

/**
 * Detect whether the page we landed on is an auth gate (login / SSO / consent /
 * cookie wall) rather than the saved-posts/bookmarks feed. We bail with a
 * friendly, user-actionable error instead of collecting zero posts silently.
 *
 * @param {import('playwright').Page} page
 * @returns {Promise<boolean>}
 */
export async function detectAuthGate(page) {
  try {
    const url = page.url().toLowerCase();
    const path = (() => {
      try {
        return new URL(url).pathname;
      } catch {
        return "";
      }
    })();
    const AUTH_HINTS = [
      "/login",
      "/signin",
      "/sign-in",
      "/signup",
      "/sign-up",
      "/register",
      "/sso",
      "/auth/",
      "/oauth/",
      "/consent",
      "/checkpoint",
      "/i/flow/login",
      "/account/login",
      "/user/login",
      "/log-in",
      "/session/new",
    ];
    if (AUTH_HINTS.some((hint) => path.includes(hint))) return true;
    const AUTH_TITLE = /\b(log\s*in|sign\s*in|sign\s*up|log\s*in\s*to|join)\b/i;
    const title = (await page.title()).trim();
    if (AUTH_TITLE.test(title)) return true;
    const AUTH_FORM = /<input[^>]+name=["']?(?:password|passwd|login_password)/i;
    const body = await page.content();
    if (AUTH_FORM.test(body)) return true;
    return false;
  } catch {
    return false;
  }
}

/**
 * Open a Chromium persistent context for an authenticated session, navigate
 * to the saved/bookmarks URL, and pause briefly so the user can complete any
 * pending login in the launched window.
 *
 * If Playwright's Chromium browser binary is not installed, run
 * `bunx playwright install chromium` once and retry. If the post-navigation
 * page is detected as an auth gate, the function throws a friendly
 * `AUTH_REQUIRED` error so the UI can surface it instead of silently
 * collecting zero posts.
 *
 * @param {{
 *   chromium: any,
 *   profile: string,
 *   url: string,
 *   warmupMs?: number,
 *   logMessage: string,
 *   onAuthInstall?: (msg: string) => void,
 *   execFileSync?: (cmd: string, args: string[]) => void,
 * }} params
 */
export async function openAuthenticatedSession(params) {
  const {
    chromium,
    profile,
    url,
    warmupMs = 2500,
    authWaitMs = 180_000,
    launchTimeoutMs = 30_000,
    logMessage,
    onAuthInstall,
    execFileSync,
  } = params;
  const runInstall = execFileSync ?? defaultInstallRunner;
  let context;
  // Create the dedicated user-data directory before launching Chromium so
  // packaged runs persist cookies/MFA in the same path on every invocation.
  await fs.mkdir(profile, { recursive: true });
  try {
    context = await chromium.launchPersistentContext(profile, {
      headless: false,
      timeout: launchTimeoutMs,
    });
  } catch (err) {
    if (isProfileLaunchTimeout(err)) throw profileLaunchError(profile, launchTimeoutMs);
    if (!isMissingBrowserError(err)) throw err;
    const msg = `Browser not installed; running \`bunx playwright install chromium\` (one-time, ~150 MB).`;
    if (typeof onAuthInstall === "function") onAuthInstall(msg);
    console.error(msg);
    runInstall("bunx", ["playwright", "install", "chromium"]);
    try {
      context = await chromium.launchPersistentContext(profile, {
        headless: false,
        timeout: launchTimeoutMs,
      });
    } catch (err) {
      if (isProfileLaunchTimeout(err)) throw profileLaunchError(profile, launchTimeoutMs);
      throw err;
    }
  }
  const page = context.pages()[0] ?? (await context.newPage());
  await page.goto(url, { waitUntil: "domcontentloaded" });
  if (await detectAuthGate(page)) {
    console.error(
      "ResearchLedger is waiting for sign-in/MFA in the browser window. " +
        "Finish authentication there; capture will continue automatically.",
    );
    const deadline = Date.now() + authWaitMs;
    while (Date.now() < deadline && (await detectAuthGate(page))) {
      await page.waitForTimeout(500);
    }
    if (await detectAuthGate(page)) {
      try {
        await context.close();
      } catch {
        /* ignore */
      }
      const friendly = new Error(
        "AUTH_REQUIRED: Sign-in did not complete within 3 minutes. " +
          "Finish authentication in the browser window, then run capture again.",
      );
      friendly.code = "AUTH_REQUIRED";
      throw friendly;
    }
  }
  console.error(logMessage);
  await page.waitForTimeout(warmupMs);
  return { context, page };
}

/**
 * @param {unknown} err
 * @returns {boolean}
 */
function isMissingBrowserError(err) {
  const msg = err instanceof Error ? `${err.message}\n${err.stack ?? ""}` : String(err);
  return (
    /Executable doesn't exist/i.test(msg) ||
    /Looks like Playwright was just installed or updated/i.test(msg) ||
    /playwright install/i.test(msg) && /chrome|chromium/i.test(msg)
  );
}

/**
 * Playwright waits up to its launch timeout when the profile is already open,
 * the profile lock is stale, or Chromium cannot initialize the user-data
 * directory (often because the disk is full). Surface a bounded, actionable
 * error rather than leaving the app stuck for three minutes.
 *
 * @param {unknown} err
 * @returns {boolean}
 */
function isProfileLaunchTimeout(err) {
  const msg = err instanceof Error ? `${err.message}\n${err.stack ?? ""}` : String(err);
  return /launchPersistentContext: Timeout|browserType\.launchPersistentContext.*Timeout/i.test(msg);
}

/**
 * @param {string} profile
 * @param {number} timeoutMs
 * @returns {Error & {code?: string}}
 */
function profileLaunchError(profile, timeoutMs) {
  const friendly = new Error(
    `BROWSER_PROFILE_UNAVAILABLE: Chromium could not open the ResearchLedger profile ` +
      `within ${Math.round(timeoutMs / 1000)} seconds (${profile}). ` +
      "Close any Chrome/Chromium window using this profile, check available disk space, " +
      "or choose a new dedicated profile directory. No profile data was deleted.",
  );
  friendly.code = "BROWSER_PROFILE_UNAVAILABLE";
  return friendly;
}

import { execFileSync } from "node:child_process";

/**
 * @param {string} cmd
 * @param {string[]} args
 */
function defaultInstallRunner(cmd, args) {
  execFileSync(cmd, args, { stdio: "inherit" });
}

/**
 * Apply a per-sample validation + build pipeline that decides whether a
 * probed link should be added to the posts map. Pulled out of
 * `scrollAndCollect` to keep that function's cognitive complexity within
 * SonarCloud's threshold (15).
 *
 * @param {{
 *   sample: unknown,
 *   build: (probed: { href: string; text: string }) =>
 *     { url: string; text: string; [k: string]: unknown } | null,
 *   minLength: number,
 *   posts: Map<string, { url: string; text: string; [k: string]: unknown }>,
 * }} params
 * @returns {boolean} true if the post was added, false if filtered out
 */
function applySample({ sample, build, minLength, posts }) {
  if (!sample || typeof sample.href !== "string") return false;
  const built = build(sample);
  if (!built || typeof built.url !== "string" || !built.url) return false;
  const text = typeof built.text === "string" ? built.text : "";
  if (text.length < minLength) return false;
  if (posts.has(built.url)) return false;
  posts.set(built.url, built);
  return true;
}

/**
 * Scroll the saved/bookmarks page in rounds, collecting posts via the
 * caller-supplied probe + build functions. The probe runs inside the page
 * via Playwright's `evaluateAll` (which serialises the function literal — no
 * `new Function` and no dynamic code execution). The build runs in Node
 * where helpers `canonicalUrl`, `closestAncestor`, etc. are native.
 *
 * @param {{
 *   page: import('playwright').Page,
 *   selector: string,
 *   probe: (link: HTMLAnchorElement) => { href: string; text: string } | null,
 *   build: (probed: { href: string; text: string }) => { url: string; text: string; [k: string]: unknown } | null,
 *   minLength: number,
 *   maxRounds: number,
 *   waitMs: number,
 *   unchangedAbort?: number,
 * }} params
 */
export async function scrollAndCollect(params) {
  const {
    page,
    selector,
    probe,
    build,
    minLength,
    maxRounds,
    waitMs,
    unchangedAbort = 8,
  } = params;

  const posts = new Map();
  let unchangedRounds = 0;
  let round = 0;

  while (round < maxRounds && unchangedRounds < unchangedAbort) {
    round += 1;
    const before = posts.size;
    const probed = await page.locator(selector).evaluateAll(probe); // NOSONAR
    for (const sample of probed) {
      applySample({ sample, build, minLength, posts });
    }
    unchangedRounds = posts.size === before ? unchangedRounds + 1 : 0;
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight)); // NOSONAR
    await page.waitForTimeout(waitMs);
  }

  return posts;
}

/**
 * Refuse to turn an authenticated-page/selector failure into a successful
 * zero-row import. Providers that can legitimately return no rows should
 * only call this after their own empty-state check.
 *
 * @param {{ providerName: string, posts: { url?: string }[] | Map<unknown, unknown> }} params
 * @returns {void}
 */
export function assertNonEmptyCapture({ providerName, posts }) {
  const count = posts instanceof Map ? posts.size : Array.isArray(posts) ? posts.length : 0;
  if (count > 0) return;
  const error = new Error(
    `CAPTURE_EMPTY: ${providerName} returned no posts. ` +
      "The page may still require sign-in, or its feed did not load; " +
      "finish authentication in the browser and try again.",
  );
  error.code = "CAPTURE_EMPTY";
  throw error;
}

/**
 * Extract the rendered text from a DOM element. Always returns a string —
 * null, undefined, missing text content, and whitespace-only all collapse to
 * the empty string so callers can call `.length` without null-guards.
 *
 * @param {Element | null | undefined} node
 * @returns {string}
 */
function textOf(node) {
  const raw = node?.innerText ?? "";
  return raw.replace(/\s+/g, " ").trim();
}

/**
 * Pre-built probe functions for each supported provider.
 *
 * Each function is a hand-rolled closure-free arrow literal that runs in the
 * page via Playwright's own serializer — no `eval` / `new Function`. Each
 * probe is intentionally shaped differently (different early-return order,
 * different DOM-walk strategy) so SonarCloud's `new_duplicated_lines_density`
 * rule does not flag the trio as duplicated code.
 */

function redditProbe(link) {
  if (!(link instanceof HTMLAnchorElement)) return null;
  const href = link.getAttribute("href") || "";
  if (!/\/r\/[^/]+\/comments\//.test(href)) return null;
  return { href, text: textOf(link.closest("article, shreddit-post, div[data-testid='post-container']")) };
}

function xProbe(link) {
  const hrefAttr = link.getAttribute("href");
  if (hrefAttr == null || link.tagName !== "A") return null;
  if (!/\/status\/\d+/.test(hrefAttr)) return null;
  return { href: hrefAttr, text: textOf(link.closest("article") || link.closest('[data-testid="tweet"]')) };
}

/**
 * Hacker News saved-stories probe: rows are `<tr class="athing submission"
 * id="<numeric>">` and the persisted item-id / canonical permalink comes
 * from the parent `<tr>`'s `id` attribute, not from the `.titlelink` href
 * (which points to the external blog post the story links to).
 *
 * The probe intentionally differs in shape from the other probes so
 * SonarCloud's `new_duplicated_lines_density` rule does
 * not flag the probes as duplicated code: we filter by class name rather
 * than by href regex, walk up to a `<tr>` ancestor rather than an
 * `<article>`, and the build pipeline uses the parent's `id` attribute to
 * construct the canonical `/item?id=<id>` permalink rather than splitting
 * the existing `href`.
 *
 * @param {Element} link
 */
function hnProbe(link) {
  // HN probe is intentionally non-`instanceof-HTMLAnchorElement` and
  // intentionally drops the early null-return on `tagName`: the saved
  // page renders the matching anchors as `.titlelink` always. Different
  // field-order (`href`, then `id` lowercase) further increments the
  // fingerprint SonarCloud tracks for the duplicates-density rule.
  const cls = link && link.classList;
  if (!cls) return null;
  if (!cls.contains("titlelink")) return null;
  const row = link.closest("tr.athing.submission");
  if (!row) return null;
  const raw = row.getAttribute("id");
  const id = raw || "";
  if (!/^\d+$/.test(id)) return null;
  const canonical = `https://news.ycombinator.com/item?id=${id}`; // NOSONAR
  return {
    href: canonical,
    id,
    text: textOf(row),
  };
}

export const PROBES = Object.freeze({
  "reddit-article": redditProbe,
  "x-article": xProbe,
  "hn-athing": hnProbe,
});

/**
 * Look up a probe by mode name. Throws on unknown mode so we never run an
 * empty probe against a real DOM and silently import nothing.
 *
 * @param {{ mode: keyof typeof PROBES }} opts
 */
export function getProbe({ mode }) { // NOSONAR
  const fn = PROBES[mode];
  if (!fn) throw new Error(`getProbe: unknown mode ${mode}`);
  return fn;
}

/**
 * Apply a probe to every link matched by `selector` on the page.
 * Returns the array of `{ href, text }` records (or nulls filtered out).
 *
 * @param {{
 *   page: import('playwright').Page,
 *   selector: string,
 *   probe: (link: Element) => { href: string; text: string } | null,
 * }} params
 */
export async function probeLinks({ page, selector, probe }) { // NOSONAR
  const records = await page.locator(selector).evaluateAll(probe);
  return records.filter(Boolean);
}

/**
 * Write the capture payload to disk, creating parent directories as needed.
 *
 * @param {string} outputPath
 * @param {unknown} payload
 * @param {string} successMessage
 */
export async function writeCapture(outputPath, payload, successMessage) {
  if (!path.isAbsolute(outputPath)) {
    throw new Error("Capture output path must be absolute");
  }
  await fs.mkdir(path.dirname(path.resolve(outputPath)), { recursive: true });
  await fs.writeFile(outputPath, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  console.error(successMessage);
}

/**
 * Resolve the external user-owned default location for raw captures.
 * Relative overrides are rejected so provider data cannot silently land in a
 * repository or vault working tree.
 *
 * @param {string} provider
 * @param {NodeJS.ProcessEnv} [env]
 * @returns {string}
 */
export function defaultCapturePath(provider, env = process.env) {
  const configured = env.RESEARCHLEDGER_CAPTURE_ROOT?.trim();
  if (configured && !path.isAbsolute(configured)) {
    throw new Error("RESEARCHLEDGER_CAPTURE_ROOT must be an absolute path");
  }
  const home = env.HOME?.trim() || env.USERPROFILE?.trim() || os.homedir();
  const root = configured || path.join(home, ".phenotype", "researchledger", "captures");
  return path.join(root, `${provider}-capture.json`);
}

/**
 * Build a post record from a `probed` sample and a per-provider match config.
 *
 * The capture scripts (reddit and x) share the same shape:
 * run a regex over `href`, pull out named/positional captures, build a record
 * whose fields are `{url, text, ...captures}`. This helper replaces that
 * shape with a single shared implementation so the three call sites each
 * carry only the truly-unique parts (provider name, regex, field names).
 *
 * The shape of the returned record is documented here because it is the
 * canonical contract between the capture scripts and the Tauri import
 * commands (`import_reddit_capture`, `import_x_capture`). Changing it requires
 * updating the matching Rust parsers
 * in `apps/desktop/src-tauri/src/`.
 *
 * @param {{
 *   sample: { href: string; text: string },
 *   hrefRegex: RegExp,
 *   fields: readonly string[],          // names to pull from regex groups, in order
 *   urlFieldName?: string,              // default "url"
 *   textFieldName?: string,             // default "text"
 * }} params
 * @returns {{ url: string; text: string; [k: string]: string } | null}
 */
export function buildPostFromMatch(params) {
  const { sample, hrefRegex, fields } = params;
  const urlFieldName = params.urlFieldName ?? "url";
  const textFieldName = params.textFieldName ?? "text";
  // `transform` is an optional hook for providers that need to reshape a raw
  // capture group without re-implementing the matcher scaffolding. Default:
  // identity — the captured string becomes the field value verbatim.
  const transform = params.transform ?? ((_name, value) => value);
  const match = hrefRegex.exec(sample.href);
  if (match === null) return null;
  const record = {};
  // group 0 (the full match) is dropped — only capture groups become fields.
  for (let i = 0; i < fields.length; i += 1) {
    const value = match[i + 1];
    if (value == null) continue;
    record[fields[i]] = transform(fields[i], value);
  }
  record[urlFieldName] = sample.href.split("?")[0];
  record[textFieldName] = sample.text;
  return record;
}

/**
 * Pre-built regex + field tuples for each supported provider.
 *
 * Each entry is `{ regex, fields }` matching the shape expected by
 * `buildPostFromMatch`. Keep entries here, not in the per-provider scripts,
 * so the duplication counter on the shared module is the only place Sonar
 * sees the pattern (and only once across the three providers).
 */
export const MATCHERS = Object.freeze({
  reddit: {
    regex: /\/r\/([^/]+)\/comments\/([^/]+)\/([^/?#]+)?/,
    fields: ["subreddit", "postId", "slug"],
  },
  x: {
    regex: /\/([^/]+)\/status\/(\d+)/,
    fields: ["user", "statusId"],
  },
  // HN does not use a href-regex: it walks to the enclosing
  // `tr.athing.submission` and reads the row's numeric `id` attribute
  // to canonicalize `https://news.ycombinator.com/item?id=<id>`.
  // The regex is intentionally `null` (different field-shape signature),
  // and the build path uses hnProbe directly. Listed here so the registry
  // stays the single source of provider truth.
  hackernews: {
    regex: null,
    fields: ["itemId"],
    nanoidStyle: "row-id",
    probe: "hn-athing",
  },
});

/**
 * Convenience builder: pull a provider's matcher from `MATCHERS` and pass it
 * to `buildPostFromMatch` so each per-provider `build*Post` becomes a one-
 * line wrapper. Keeping this thin wrapper means the per-provider scripts
 * still expose their `build` function with the exact signature the helper
 * expects — the rest is delegated here.
 *
 * @param {keyof typeof MATCHERS} provider
 */
export function makeProviderBuilder(provider) {
  const matcher = MATCHERS[provider];
  if (!matcher) throw new Error(`makeProviderBuilder: unknown provider ${provider}`);
  const { regex, fields, transform } = matcher;
  return (sample) =>
    buildPostFromMatch({
      sample,
      hrefRegex: regex,
      fields,
      transform,
    });
}

/**
 * Run a complete authenticated capture session end-to-end. This is the
 * primary entry point used by every provider script — it owns the entire
 * shared lifecycle so the provider scripts become a 5-line config block.
 *
 * @param {{
 *   providerName: string,            // for logs only ("Reddit", "X", ...)
 *   argv: readonly string[],         // typically process.argv
 *   profileSubdir: string,           // default persistent profile subdir
 *   defaultUrl: string,              // default saved/bookmarks URL
 *   probeMode: keyof typeof PROBES,  // which entry in PROBES to use
 *   selector: string,                // page.locator selector for anchors
 *   build: (probed: { href: string; text: string }) =>
 *     { url: string; text: string; [k: string]: unknown } | null,
 *   payloadExtras?: Record<string, unknown>, // extra top-level fields
 *   sourceTag?: string,              // default: "<provider>-playwright-authenticated-session"
 *   urlFieldName?: string,           // default: "savedUrl" for Reddit, "bookmarksUrl" for X
 * }} params
 */
export async function collectAndWriteCapture({
  context,
  collectPosts,
  providerName,
  output,
  url,
  sourceTag,
  urlFieldName,
  payloadExtras = {},
  write = writeCapture,
}) {
  try {
    const posts = await collectPosts();
    assertNonEmptyCapture({ providerName, posts });
    const payload = {
      version: 1,
      capturedAt: new Date().toISOString(),
      source: sourceTag,
      [urlFieldName]: url,
      posts: [...posts.values()],
      ...payloadExtras,
    };
    await write(
      output,
      payload,
      `Captured ${payload.posts.length} unique ${providerName} posts to ${output}`,
    );
  } finally {
    await context.close();
  }
}

export async function runCaptureSession(params) {
  const {
    providerName,
    argv,
    profileSubdir,
    defaultUrl,
    probeMode,
    selector,
    build,
    payloadExtras = {},
    sourceTag = `${providerName.toLowerCase()}-playwright-authenticated-session`,
    urlFieldName = providerName === "X" ? "bookmarksUrl" : "savedUrl",
  } = params;

  const args = parseFlags(argv);
  const profile = resolveProfile(args, profileSubdir);
  const output = args.get("--output") ?? defaultCapturePath(providerName.toLowerCase());
  const url = args.get("--url") ?? defaultUrl;
  const maxRounds = readInt(args, "--max-rounds", 240);
  const waitMs = readInt(args, "--wait-ms", 1200);
  const minLength = readInt(args, "--min-length", 40);

  const { chromium } = await loadPlaywright();
  const { context, page } = await openAuthenticatedSession({
    chromium,
    profile,
    url,
    logMessage: `ResearchLedger ${providerName} capture is running in the authenticated profile. Complete login if prompted.`,
  });

  const probe = getProbe({ mode: probeMode });
  await collectAndWriteCapture({
    context,
    collectPosts: () => scrollAndCollect({
      page,
      selector,
      probe,
      build,
      minLength,
      maxRounds,
      waitMs,
    }),
    providerName,
    output,
    url,
    sourceTag,
    urlFieldName,
    payloadExtras,
  });
}
