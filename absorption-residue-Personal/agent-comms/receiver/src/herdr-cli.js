// Transport for the herdr CLI: spawn it, parse its JSON envelope, classify failures.
//
// Kept separate from the wake policy in `herdr.js` so the policy can be read -- and
// reviewed -- without also re-reading the process-spawning code.

import { execFile } from "node:child_process";
import { promisify } from "node:util";

const exec = promisify(execFile);

/** Per-call ceiling. A wedged herdr must not wedge the receiver. */
const STEP_TIMEOUT_MS = 10_000;

/** herdr could not be reached, or spoke something other than its JSON envelope. */
export class HerdrNotReachable extends Error {}

/**
 * Runs the herdr CLI and resolves its parsed JSON envelope.
 *
 * Injectable so tests can exercise the verification logic without spawning a process per
 * call. Spawning ~40 child processes per test run is slow and, on a loaded machine, adds
 * enough scheduling delay to destabilise OTHER suites in the same run.
 *
 * @param {string[]} args
 * @returns {Promise<any>}
 */
export const runHerdr = async (args) => {
  let stdout;
  try {
    ({ stdout } = await exec("herdr", args, { timeout: STEP_TIMEOUT_MS, maxBuffer: 8 * 1024 * 1024 }));
  } catch (error) {
    throw new HerdrNotReachable(`herdr ${args.join(" ")} failed: ${/** @type {Error} */ (error).message}`);
  }
  try {
    return JSON.parse(stdout);
  } catch {
    throw new HerdrNotReachable(`herdr ${args.join(" ")} returned non-JSON output`);
  }
};

/**
 * Unwrap herdr's `{result: ...}` envelope.
 *
 * @param {any} doc
 * @returns {any}
 */
export function result(doc) {
  if (doc && typeof doc === "object" && doc.result) return doc.result;
  throw new HerdrNotReachable("herdr response had no result");
}
