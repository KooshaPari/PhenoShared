#!/usr/bin/env node
/**
 * Provider URL shape recognizers — JS-side equivalents of the Rust guards
 * living in `apps/desktop/src-tauri/src/provider_html.rs` (the
 * `is_reddit_post_path` / `is_x_post_path` / `is_hackernews_post_path`
 * trios). These recognizers are used by the capture-time filter that
 * decides which probed anchors survive into the Playwright capture
 * payload, and they are also useful as pre-flight checks in the React
 * UI before triggering a capture.
 *
 * The recognizers are intentionally regex-based and limited to the
 * common-case shapes, so the contract is:
 *   input: any string (typically captured `href` content from a DOM)
 *   output: boolean
 *
 * Each function returns `false` on un-parseable URL input (via
 * `URL.parse`/`new URL` throw) rather than throwing, so the filter
 * pipeline can call them recursively on already-broken hrefs without
 * wrapping every call in a try/catch.
 */

/**
 * Recognize a Reddit post permalink on the modern `www.reddit.com`
 * host. Accepts the canonical shape `/r/<sub>/comments/<id>/<slug>`
 * where `<id>` is the alphanumeric post id and `<slug>` is the
 * optional human-readable slug (empty allowed). False-positives the
 * Rust guard catches but this JS recognizer does not (e.g.
 * `old.reddit.com`) remain a Rust-side concern.
 *
 * @param {string} url
 * @returns {boolean}
 */
export function isRedditPostUrl(url) {
  try {
    const u = new URL(url);
    return (
      /^www\.reddit\.com$/.test(u.hostname) &&
      /^\/r\/[^/]+\/comments\/[a-z0-9]+\/[a-z0-9-]*$/i.test(u.pathname)
    );
  } catch {
    return false;
  }
}

/**
 * Recognize an X (formerly Twitter) post permalink: `<user>/status/<id>`
 * on the canonical `x.com` host. Usernames are 1-15 characters of
 * alphanumeric + underscore (Twitter's documented rules); ids are
 * entirely numeric. Anything else — `/i/status/...`, `/intent/...`,
 * `/compose/...`, etc. — is rejected.
 *
 * @param {string} url
 * @returns {boolean}
 */
export function isXPostUrl(url) {
  try {
    const u = new URL(url);
    return (
      /^x\.com$/.test(u.hostname) &&
      /^\/[a-zA-Z0-9_]{1,15}\/status\/[0-9]+$/.test(u.pathname)
    );
  } catch {
    return false;
  }
}

/**
 * Recognize a Hacker News item permalink of the form
 * `https://news.ycombinator.com/item?id=<numeric-id>`. The id is
 * pulled from `searchParams` so querystrings with multiple params
 * still parse correctly (e.g. `?id=42&foo=bar`).
 *
 * @param {string} url
 * @returns {boolean}
 */
export function isHackerNewsItemUrl(url) {
  try {
    const u = new URL(url);
    return (
      /^news\.ycombinator\.com$/.test(u.hostname) &&
      u.pathname === "/item" &&
      /^[0-9]+$/.test(u.searchParams.get("id") || "")
    );
  } catch {
    return false;
  }
}
