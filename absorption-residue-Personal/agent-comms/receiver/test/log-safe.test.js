// Tests for log sanitisation.
//
// SonarCloud flagged `Log Injection via unsanitized user input` on
// scripts/live-bridge-check.mjs:126, where the receiver's HTTP response body was
// interpolated into a log line verbatim. These tests pin the property that
// closes it: a sanitised value is always exactly one line, whatever it contains.

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { logSafe, safeError } from "../src/log-safe.js";

/** Count real line terminators, which is what a log consumer would split on. */
const lineCount = (s) => (s.match(/\r\n|\r|\n/g) ?? []).length;

describe("log sanitisation", () => {
  test("a newline in a value cannot forge a second log entry", () => {
    // Exactly the shape of the finding: a response body that ends its own line
    // and starts a convincing fake one.
    const hostile = '{"detail":"nope"}\nresponse body : FORGED: everything is fine';
    const entry = `response body : ${logSafe(hostile)}`;

    assert.equal(lineCount(entry), 0, "the entry must stay on one line");
    assert.match(entry, /response body : /);
    // The real content is still readable, just inert.
    assert.match(entry, /FORGED: everything is fine/);
  });

  test("carriage returns are neutralised too, not just LF", () => {
    // A lone CR is a line terminator for plenty of terminals and log shippers,
    // so catching only \n would leave the hole half open.
    const entry = logSafe("first\rsecond");
    assert.equal(lineCount(entry), 0);
    assert.match(entry, /\\x0d/);
  });

  test("CRLF survives as two visible escapes, never as a terminator", () => {
    const entry = logSafe("a\r\nb");
    assert.equal(lineCount(entry), 0);
    assert.equal(entry, "a\\x0d\\x0ab");
  });

  test("other C0 controls and DEL are escaped", () => {
    const entry = logSafe("nul\u0000tab\tdel\u007f");
    assert.equal(entry, "nul\\x00tab\\x09del\\x7f");
    assert.ok(!/[\u0000-\u001f\u007f]/.test(entry), "no control byte may survive");
  });

  test("an ordinary value is returned unchanged", () => {
    // Escaping everything would make the log unreadable, so the common case
    // must be a byte-for-byte no-op. This is what catches an over-broad regex.
    const plain = '{"status":"awakened","receiptId":"abc123"}';
    assert.equal(logSafe(plain), plain);
    assert.equal(logSafe("plain text with spaces, dots, : and ="), "plain text with spaces, dots, : and =");
  });

  test("non-strings are coerced rather than throwing", () => {
    assert.equal(logSafe(42), "42");
    assert.equal(logSafe(null), "null");
    assert.equal(logSafe(undefined), "undefined");
    assert.equal(logSafe({ a: 1 }), "[object Object]");
  });

  test("sanitising is not idempotent-breaking: escapes are never re-escaped", () => {
    // "a\\x0ab" is a legitimate literal value a caller may have. Re-escaping it
    // would be harmless but doubling the length of every real escape, so the
    // contract is one pass over the input.
    const once = logSafe("a\nb");
    assert.equal(once, "a\\x0ab");
    assert.equal(logSafe(once), once);
  });

  test("a thrown Error keeps its stack and loses its newlines", () => {
    const error = new Error("upstream said\nERROR: all clear");
    const entry = safeError(error);
    assert.equal(lineCount(entry), 0, "an error report must still be one line");
    assert.match(entry, /upstream said/);
    assert.match(entry, /Error/, "the stack must remain diagnosable");
  });

  test("a thrown non-Error still renders safely", () => {
    assert.equal(safeError("plain\nreason"), "plain\\x0areason");
    assert.equal(safeError(0), "0");
  });
});