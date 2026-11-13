// Shared test harness for the receiver.
//
// WHY THIS EXISTS. Every receiver test needs the same five things: a temp state dir, a
// fake herdr runner, a receiver handler, a real loopback server, and cleanup. Written out
// per test, that block is 14 identical lines -- which is exactly how Sonar measured 11.5%
// duplication on this PR and blocked the security gate.
//
// The fake herdr runner is the important half. It is injected, so no test ever spawns a
// herdr process and no test can move a real pane. `calls` records every argv, so tests
// assert on the literal commands the waker issued rather than on internal state.

import { once } from "node:events";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { createReceiver, createWakeServer } from "../../src/server.js";
import { ReceiptStore, SeenStore } from "../../src/store.js";
import { createHerdrWaker } from "../../src/herdr.js";
import { buildWaker } from "../../src/index.js";

export const TEST_TOKEN = "synthetic-token";

/**
 * Reserve an ephemeral loopback port, then release it for the real bind.
 *
 * The probe binds port 0 to ask the OS for a free port, then closes it. Tests must
 * always pass the CONCRETE port this returns: the receiver's own contract rejects
 * port 0 (it wants 1-65535).
 */
export async function freePort() {
  return new Promise((resolve, reject) => {
    const probe = createServer();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const address = probe.address();
      const port = typeof address === "object" && address ? address.port : 0;
      probe.close(() => resolve(port));
    });
  });
}

/**
 * Start a real loopback HTTP server around a handler, so bearer gating, JSON parsing,
 * and response bodies are exercised end to end rather than stubbed.
 * @param {(req: any, res: any) => Promise<void>} handler
 */
export async function startServer(handler) {
  const port = await freePort();
  const server = createWakeServer(handler, { port, host: "127.0.0.1" });
  if (!server.listening) await once(server, "listening");
  return { server, port, stop: () => new Promise((resolve) => server.close(resolve)) };
}

/**
 * Collect logger output into an array so a test can assert a secret never appears.
 * `error` is included because a logging bug could hide a token in an error path.
 */
export function recordingLogger() {
  const lines = [];
  const record = (msg, meta) => lines.push(`${msg} ${JSON.stringify(meta ?? {})}`);
  return { lines, info: record, warn: record, error: record };
}

/** Build one pane entry in the shape `herdr pane list` emits. */
export function pane(paneId, overrides = {}) {
  const workspaceId = paneId.split(":")[0];
  return {
    pane_id: paneId,
    workspace_id: workspaceId,
    tab_id: `${workspaceId}:t1`,
    label: "TEST",
    ...overrides,
  };
}

/**
 * A fake herdr runner over a fixed set of panes.
 *
 * `focusedPaneId` drives the per-pane `focused` flag, so a test can model either "the
 * target is already focused" (the receiver's success path) or "nothing is focused" (the
 * walk path) without duplicating the argv router.
 *
 * @param {{panes?: any[], focusedPaneId?: string | null}} options
 */
export function fakeHerdr({ panes = [], focusedPaneId = null } = {}) {
  const calls = [];
  const list = () => panes.map((p) => ({ ...p, focused: p.pane_id === focusedPaneId }));

  const runner = async (args) => {
    calls.push([...args]);
    if (args[0] === "pane" && args[1] === "list") return { result: { panes: list() } };
    if (args[0] === "pane" && args[1] === "get") {
      return { result: { pane: list().find((p) => p.pane_id === args[2]) } };
    }
    // workspace/tab focus are nudges only; focus claims come from `pane get`.
    return { result: {} };
  };

  return { runner, calls };
}

/** POST JSON to the loopback receiver and return status, raw text, and parsed body. */
export async function postJson(port, body, { token, headers = {} } = {}) {
  const all = { "content-type": "application/json", ...headers };
  if (token !== undefined) all.authorization = `Bearer ${token}`;
  const res = await fetch(`http://127.0.0.1:${port}/wake`, {
    method: "POST",
    headers: all,
    body: JSON.stringify(body),
  });
  const text = await res.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    json = undefined;
  }
  return { status: res.status, text, json };
}

/** Read the durable receipts a receiver wrote, parsed one per entry. */
export async function readReceipts(stateDir) {
  let raw;
  try {
    raw = await readFile(join(stateDir, "receipts.jsonl"), "utf8");
  } catch (error) {
    // "no wake attempt reached the log" is a meaningful state, not a test failure.
    if (error.code === "ENOENT") return [];
    throw error;
  }
  return raw
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

/**
 * Wire a complete receiver: temp state dir, fake herdr, handler, and a live loopback
 * server, with teardown registered on the test context.
 *
 * Every field is an override, so a test states only what it actually cares about and the
 * rest stops being copy-paste.
 *
 * @param {any} t node:test context, used for automatic teardown
 * @param {{
 *   recipientMap?: Record<string, {paneId?: string, label?: string, agent?: string}>,
 *   panes?: any[], focusedPaneId?: string | null, dryRun?: boolean,
 *   token?: string, maxPerMinute?: number, logger?: any, waker?: any,
 *   store?: any, seen?: any, stateDir?: string,
 * }} options
 */
export async function withReceiver(t, options = {}) {
  const {
    recipientMap = {},
    panes = [],
    focusedPaneId = null,
    dryRun = false,
    token = TEST_TOKEN,
    maxPerMinute,
    logger = recordingLogger(),
    waker: injectedWaker,
    store: injectedStore,
    seen: injectedSeen,
    stateDir: reuseStateDir,
  } = options;

  // Passing an existing stateDir models a receiver RESTART: a new process over the same
  // durable files is the only way to observe what a crash actually left behind.
  const stateDir = reuseStateDir ?? (await mkdtemp(join(tmpdir(), "wake-test-")));
  if (!reuseStateDir) t.after(() => rm(stateDir, { recursive: true, force: true }));

  const { runner, calls } = fakeHerdr({ panes, focusedPaneId });

  const waker =
    injectedWaker ??
    (dryRun
      ? buildWaker({ dryRun: true, recipientMap }, runner)
      : createHerdrWaker({ recipientMap, runner }));

  // A test may inject a store or index (for example one that throws on write, standing in
  // for a full disk). Everything else still gets the real, fsyncing implementation.
  const seen = injectedSeen ?? new SeenStore(stateDir);
  const handler = createReceiver({
    store: injectedStore ?? new ReceiptStore(stateDir),
    seen,
    waker,
    token,
    logger,
    maxPerMinute,
  });

  const { port, stop } = await startServer(handler);
  t.after(stop);

  return {
    port,
    stateDir,
    seen,
    calls,
    logger,
    token,
    runner,
    post: (body, postOptions) => postJson(port, body, { token, ...postOptions }),
    receipts: () => readReceipts(stateDir),
  };
}
