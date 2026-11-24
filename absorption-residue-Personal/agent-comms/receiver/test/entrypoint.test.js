// Regression test for the silent wake outage.
//
// The receiver auto-starts itself only when it is the process entrypoint. That guard used
// to be `import.meta.url === `file://${process.argv[1]}``, which compares this module's
// RESOLVED realpath against the path AS TYPED. Under a symlinked parent directory or a
// symlinked launch path the two differ, the guard went false, main() never ran, and the
// process printed NOTHING and exited 0 -- with no port bound. A supervisor reading that
// clean exit concluded the receiver was healthy while no wake path existed at all.
//
// This test therefore must spawn a real child process through a symlink and observe the
// bind. Re-importing the module in-process could never catch the bug.

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, symlink, rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { freePort } from "./helpers/harness.js";

const ENTRYPOINT = fileURLToPath(new URL("../src/index.js", import.meta.url));
const TOKEN = "synthetic-test-token-not-real-0000";
const MAP_JSON = JSON.stringify({ civis: "wE:p1" });

/**
 * Spawn the entrypoint and observe whether it actually bound a port.
 *
 * @param {string} launchPath path handed to `node`, which may be a symlink
 * @param {{port: number, stateDir: string, token?: string}} options
 * @returns {Promise<{stdout: string, stderr: string, exitCode: number | null, bound: boolean}>}
 */
async function spawnReceiver(launchPath, { port, stateDir, token = TOKEN }) {
  const child = spawn(process.execPath, [launchPath], {
    env: {
      ...process.env,
      WAKE_RECEIVER_TOKEN: token,
      WAKE_RECEIVER_PORT: String(port),
      WAKE_RECEIVER_STATE: stateDir,
      WAKE_RECEIVER_DRY_RUN: "1",
      WAKE_RECEIVER_MAP_JSON: MAP_JSON,
    },
    stdio: ["ignore", "pipe", "pipe"],
  });

  const LISTENING = /\[wake\] listening on http:\/\/127\.0\.0\.1:\d+\/wake/;

  let stdout = "";
  let stderr = "";
  child.stdout.setEncoding("utf8");
  child.stderr.setEncoding("utf8");
  child.stdout.on("data", (chunk) => {
    stdout += chunk;
  });
  child.stderr.on("data", (chunk) => {
    stderr += chunk;
  });

  /** @type {{code: number | null}} */
  const exit = { code: null };
  const closed = new Promise((resolve) => {
    // 'close' fires only after the process exited AND all its stdio streams ended.
    child.once("close", (code) => {
      exit.code = code;
      resolve(undefined);
    });
  });

  // Wait until the child has bound (listening line), exited, or is clearly stuck.
  const TIMEOUT_MS = 30_000;
  const startedAt = Date.now();
  while (Date.now() - startedAt < TIMEOUT_MS) {
    if (LISTENING.test(stdout)) break;
    if (exit.code !== null) break;
    await new Promise((resolve) => setTimeout(resolve, 25));
  }

  // A child that is still running (whether it bound or is stuck) must be reaped. Its open
  // stdout/stderr pipes otherwise keep the TEST-FILE process alive after the tests finish,
  // which makes the whole run hang with no failing test to point at.
  if (exit.code === null) {
    child.kill("SIGKILL");
  }
  await Promise.race([closed, new Promise((resolve) => setTimeout(resolve, 5000))]);

  return { stdout, stderr, exitCode: exit.code, bound: LISTENING.test(stdout) };
}

describe("entrypoint detection", () => {
  test("a symlinked launch path binds the port instead of exiting 0 in silence", async (t) => {
    const stateDir = await mkdtemp(join(tmpdir(), "wake-entry-state-"));
    const linkDir = await mkdtemp(join(tmpdir(), "wake-entry-link-"));
    const linkPath = join(linkDir, "index.js");

    await symlink(ENTRYPOINT, linkPath);
    assert.notEqual(linkPath, ENTRYPOINT, "the launch path must actually be a symlink");

    t.after(async () => {
      await rm(stateDir, { recursive: true, force: true });
      await rm(linkDir, { recursive: true, force: true });
    });

    const { stdout, stderr, exitCode, bound } = await spawnReceiver(linkPath, {
      port: await freePort(),
      stateDir,
    });

    // The historical bug: guard false, main() never ran, process exited 0, nothing bound.
    assert.equal(bound, true, `a symlinked launch path must bind (exitCode=${exitCode}, stderr: ${stderr})`);
    assert.notEqual(exitCode, 0, `the receiver must not report a clean exit when it never started (stderr: ${stderr})`);
    assert.match(
      stdout,
      /\[wake\] listening on http:\/\/127\.0\.0\.1:\d+\/wake/,
      "a symlinked launch path must bind and print the listening line",
    );
  });

  test("a realpath launch path still binds", async (t) => {
    const stateDir = await mkdtemp(join(tmpdir(), "wake-entry-state-"));
    t.after(async () => {
      await rm(stateDir, { recursive: true, force: true });
    });

    const { stdout, exitCode, bound } = await spawnReceiver(ENTRYPOINT, {
      port: await freePort(),
      stateDir,
    });

    assert.equal(bound, true, "the realpath launch path must still bind");
    assert.notEqual(exitCode, 0, "a running receiver is killed, never a clean exit");
    assert.match(stdout, /\[wake\] listening on http:\/\/127\.0\.0\.1:\d+\/wake/);
  });

  test("startup failure exits non-zero and explains itself on stderr", async (t) => {
    const stateDir = await mkdtemp(join(tmpdir(), "wake-entry-state-"));
    const linkDir = await mkdtemp(join(tmpdir(), "wake-entry-link-"));
    t.after(async () => {
      await rm(stateDir, { recursive: true, force: true });
      await rm(linkDir, { recursive: true, force: true });
    });

    const linkPath = join(linkDir, "index.js");
    await symlink(ENTRYPOINT, linkPath);

    // No token: main() throws. Even reached via a symlink this must never look healthy.
    const { stdout, stderr, exitCode, bound } = await spawnReceiver(linkPath, {
      port: await freePort(),
      stateDir,
      token: "",
    });

    assert.equal(exitCode, 1, "a failed startup must be a non-zero exit");
    assert.equal(bound, false, "a failed startup must never look like a bound receiver");
    assert.equal(stdout, "", "nothing may be printed as if the receiver were up");
    assert.match(stderr, /WAKE_RECEIVER_TOKEN is required/);
  });

  test("a port already in use exits non-zero instead of exiting 0 in silence", async (t) => {
    const stateDir = await mkdtemp(join(tmpdir(), "wake-entry-state-"));
    t.after(async () => {
      await rm(stateDir, { recursive: true, force: true });
    });

    // Hold a port, then ask the receiver to bind the same one.
    const holder = createServer();
    await new Promise((resolve) => holder.listen(0, "127.0.0.1", resolve));
    const address = holder.address();
    const port = typeof address === "object" && address ? address.port : 0;
    t.after(() => new Promise((resolve) => holder.close(resolve)));

    const { stderr, exitCode, bound } = await spawnReceiver(ENTRYPOINT, { port, stateDir });

    assert.equal(bound, false);
    assert.equal(exitCode, 1, "EADDRINUSE must be a loud non-zero exit");
    assert.match(stderr, /could not bind/);
  });
});
