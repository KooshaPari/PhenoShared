// Log output sanitisation.
//
// Anything this process did not author itself -- an HTTP response body, a
// receipt line, a value typed on the command line -- can carry CR/LF. Logged
// verbatim, a newline lets whoever controls that value append whole fake log
// entries to the stream, so a reader scrolling the output is reading something
// the reader did not get from the program. Sanitising is the fix; there is no
// version of "print it raw but trust it" that is safe.
//
// Escaped rather than stripped: dropping the character would silently merge
// two values into one token ("tok" + "en" -> "token"), which is worse than a
// visible marker. Keeping the bytes legible also means a reader can tell a
// sanitised value from a real one.

/** C0 controls plus DEL. Excludes nothing needed for single-line text output. */
const CONTROL_CHARS = /[\u0000-\u001f\u007f]/g;

/**
 * Render a value safe to interpolate into a single-line log entry.
 *
 * Every C0 control character (including CR and LF) and DEL becomes a visible
 * `\xNN` escape, so the result is always exactly one line.
 *
 * @param {unknown} value
 * @returns {string}
 */
export function logSafe(value) {
  return String(value).replace(CONTROL_CHARS, (ch) => `\\x${ch.codePointAt(0).toString(16).padStart(2, "0")}`);
}

/**
 * Render a thrown value for a single-line log entry, preferring the stack so
 * the failure is still diagnosable, and falling back to the message for the
 * many shapes an Error-ish rejection can take.
 *
 * @param {unknown} error
 * @returns {string}
 */
export function safeError(error) {
  if (error instanceof Error) return logSafe(error.stack ?? `${error.name}: ${error.message}`);
  return logSafe(error);
}