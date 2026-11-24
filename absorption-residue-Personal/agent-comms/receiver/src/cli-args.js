// Validation for every value the waker hands to the herdr CLI.
//
// WHY THIS EXISTS. The ids the waker passes to herdr -- `pane_id`, `tab_id`,
// `workspace_id` -- are not compiled-in constants. They come from two untrusted-ish
// places: the JSON `herdr pane list` emits, and the operator's recipient map file,
// which is a plain editable JSON document.
//
// `execFile` is spawned WITHOUT a shell, so a value here cannot start a shell command
// and that class of bug is already closed. It is NOT closed against ARGUMENT
// INJECTION. herdr parses the raw argv we build, so a pane id of `--json` or `-h` is
// read as a FLAG rather than as a pane name: the command silently changes meaning and
// the waker walks toward whatever the flag selected. A value containing whitespace is
// equally fine for argv but wrong for a handle, and a newline can corrupt anything that
// later re-parses the command line we logged.
//
// The fix is to REFUSE anything outside a narrow allowlist for an opaque handle, not to
// escape or repair it. Herdr ids are machine-generated handles (`w7:p1Q`, `w8:pN`,
// `wA:p8`); there is no legitimate id needing a leading dash, a space, or a shell
// metacharacter. A rejected value fails the wake honestly, which is the invariant the
// rest of the receiver is built around -- never a fabricated success.

import { RECEIPT_ID_PATTERN } from "./receipt.js";

// A handle must START alphanumeric, which is what makes flag injection impossible:
// `-` can never be the first character, so a value can never be read as an option.
// The tail allows the punctuation herdr actually emits in ids (`:`, `.`, `_`, `-`).
const HERDR_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:@-]*$/;

/** Upper bound on a handle. Observed ids are ~6 characters; this only stops abuse. */
export const MAX_HERDR_ID_LENGTH = 128;

/** The only directions `herdr pane focus --direction` accepts. */
export const HERDR_DIRECTIONS = Object.freeze(["left", "right", "up", "down"]);

/**
 * Raised when a value cannot be safely passed to the herdr CLI. Callers turn this into
 * an honest `woke: false` outcome rather than letting the bad value through.
 */
export class InvalidCliArgument extends Error {
  /**
   * @param {"pane id" | "tab id" | "workspace id" | "direction"} kind
   * @param {unknown} value
   */
  constructor(kind, value) {
    super(`refusing to pass an invalid herdr ${kind}: ${JSON.stringify(String(value))}`);
    this.name = "InvalidCliArgument";
    this.kind = kind;
  }
}

/**
 * The outcomes an OPERATOR may record for an uncertain receipt. `pending` is not one of
 * them: it is a state the receiver writes for itself, and letting a human set it would mean
 * "unknown" on demand, which the protocol already infers from a crashed attempt.
 */
export const RESOLVE_STATUSES = Object.freeze(["delivered", "failed"]);

/** Usage text for the `resolve` subcommand. Kept next to the parser so they cannot drift. */
export const RESOLVE_USAGE =
  "usage: index.js resolve <receipt-id> <delivered|failed>\n" +
  "  appends an operator decision to seen.jsonl so the next replay is no longer uncertain\n" +
  "  (env: WAKE_RECEIVER_STATE selects the state directory, same as the server)";

/**
 * Raised when an operator resolves an uncertain receipt with bad arguments. Separate from
 * InvalidCliArgument because this is a human-facing command whose error is printed, not a
 * wake that failed.
 */
export class InvalidResolveArgument extends Error {
  /** @param {string} reason */
  constructor(reason) {
    super(`${reason}\n${RESOLVE_USAGE}`);
    this.name = "InvalidResolveArgument";
    this.code = "invalid-resolve-argument";
  }
}

/**
 * True when `value` is one of the outcomes an operator may record.
 * @param {unknown} value
 * @returns {boolean}
 */
export function isValidResolveStatus(value) {
  return typeof value === "string" && RESOLVE_STATUSES.includes(value);
}

/**
 * Parse and validate `resolve` arguments.
 *
 * The id is checked against the SAME hex-64 pattern the receiver enforces on the wire, so an
 * operator who pastes a truncated id, a whitespace-padded id, or a hex string of the wrong
 * length is told so before anything is appended. There is no repair: guessing which receipt
 * the operator meant is exactly the kind of guess this module refuses to make.
 *
 * @param {string[]} argv the arguments AFTER the `resolve` subcommand
 * @returns {{receiptId: string, status: "delivered" | "failed"}}
 */
export function parseResolveArgs(argv) {
  const args = Array.isArray(argv) ? argv : [];
  if (args.length !== 2) {
    throw new InvalidResolveArgument("resolve takes exactly two arguments: <receipt-id> <outcome>");
  }
  const [receiptId, status] = args;
  if (typeof receiptId !== "string" || !RECEIPT_ID_PATTERN.test(receiptId)) {
    throw new InvalidResolveArgument(
      `receipt id must be 64 lowercase hex characters, got ${JSON.stringify(String(receiptId))}`,
    );
  }
  if (!isValidResolveStatus(status)) {
    throw new InvalidResolveArgument(
      `outcome must be one of: ${RESOLVE_STATUSES.join(", ")}; got ${JSON.stringify(String(status))}`,
    );
  }
  return { receiptId, status: /** @type {"delivered" | "failed"} */ (status) };
}

/**
 * True when `value` is safe to use as a herdr handle in argv.
 *
 * @param {unknown} value
 * @returns {boolean}
 */
export function isValidHerdrId(value) {
  return (
    typeof value === "string" &&
    value.length > 0 &&
    value.length <= MAX_HERDR_ID_LENGTH &&
    HERDR_ID_PATTERN.test(value)
  );
}

/**
 * True when `value` is one of the four directions herdr accepts.
 *
 * @param {unknown} value
 * @returns {boolean}
 */
export function isValidHerdrDirection(value) {
  return typeof value === "string" && HERDR_DIRECTIONS.includes(value);
}

/**
 * Return `value` unchanged when it is a safe handle, otherwise throw.
 *
 * @param {"pane id" | "tab id" | "workspace id"} kind
 * @param {unknown} value
 * @returns {string}
 */
export function assertHerdrId(kind, value) {
  if (!isValidHerdrId(value)) throw new InvalidCliArgument(kind, value);
  return /** @type {string} */ (value);
}

/**
 * Return `value` unchanged when it is a real direction, otherwise throw.
 *
 * @param {unknown} value
 * @returns {string}
 */
export function assertHerdrDirection(value) {
  if (!isValidHerdrDirection(value)) throw new InvalidCliArgument("direction", value);
  return /** @type {string} */ (value);
}

/**
 * Validate a pane entry from `herdr pane list`, returning only the handles that are
 * safe to pass back to the CLI.
 *
 * A pane whose `pane_id` is malformed is DROPPED rather than repaired. Dropping it means
 * the waker reports "no pane matched" -- an honest failure the operator can act on --
 * instead of navigating somewhere the id may have pointed.
 *
 * @param {any} pane a `panes[]` entry from herdr
 * @returns {{paneId: string, workspaceId?: string, tabId?: string} | undefined}
 */
export function sanitizePaneEntry(pane) {
  if (!pane || typeof pane !== "object") return undefined;
  if (!isValidHerdrId(pane.pane_id)) return undefined;
  return {
    paneId: /** @type {string} */ (pane.pane_id),
    ...(isValidHerdrId(pane.workspace_id) ? { workspaceId: /** @type {string} */ (pane.workspace_id) } : {}),
    ...(isValidHerdrId(pane.tab_id) ? { tabId: /** @type {string} */ (pane.tab_id) } : {}),
  };
}
