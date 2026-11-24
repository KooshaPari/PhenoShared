// Receiver-level tests: loopback HTTP, bearer gating, honest no-mapping failure, dry-run
// never touching a pane, and the bearer token never leaving the process.
//
// The fake herdr runner is injected, so these tests spawn no herdr process and touch no pane.
// A real loopback HTTP server is used so the bearer gate, JSON parsing, and response bodies
// are exercised end to end. See helpers/harness.js for the shared wiring.

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { noopWaker } from "../src/herdr.js";
import { buildWaker } from "../src/index.js";
import { pane, recordingLogger, withReceiver } from "./helpers/harness.js";

const RECIPIENT = "civis@example.com";

describe("receiver over loopback HTTP", () => {
  test("a mapped recipient wakes its pane and records a durable receipt", async (t) => {
    const { post, calls, receipts } = await withReceiver(t, {
      recipientMap: { civis: { paneId: "wE:p1" } },
      panes: [pane("wE:p1", { label: "TARGET" })],
      focusedPaneId: "wE:p1",
    });

    const response = await post({ recipient: RECIPIENT, messageId: "msg-1" });

    assert.equal(response.status, 200);
    assert.equal(response.json.woke, true, response.json.detail);
    assert.equal(response.json.paneId, "wE:p1");
    assert.ok(
      calls.map((c) => c.join(" ")).includes("pane get wE:p1"),
      "the receiver must drive the waker, which confirms per-pane",
    );

    const stored = await receipts();
    assert.equal(stored.length, 1);
    assert.equal(stored[0].recipient, "civis");
    assert.equal(stored[0].woke, true);
    assert.equal(stored[0].paneId, "wE:p1");
    assert.equal(stored[0].messageId, "msg-1");
  });

  test("a recipient with NO mapping reports an honest failure and never claims a wake", async (t) => {
    const { post, calls } = await withReceiver(t, {
      recipientMap: {},
      panes: [pane("wE:p1", { label: "TARGET" })],
      focusedPaneId: "wE:p1",
    });

    const response = await post({ recipient: "nobody@example.com" });

    assert.equal(response.status, 200);
    assert.equal(response.json.woke, false);
    assert.match(response.json.detail, /no herdr pane bound/);
    assert.equal(calls.length, 0, "an unmapped recipient must not even read the pane list");
  });

  test("a wrong or missing bearer token is rejected before any wake", async (t) => {
    const { port, token, calls } = await withReceiver(t, {
      recipientMap: { civis: { paneId: "wE:p1" } },
      panes: [pane("wE:p1")],
      focusedPaneId: "wE:p1",
    });

    const wrong = await fetch(`http://127.0.0.1:${port}/wake`, {
      method: "POST",
      headers: { "content-type": "application/json", authorization: "Bearer not-the-token" },
      body: JSON.stringify({ recipient: "civis" }),
    });
    const missing = await fetch(`http://127.0.0.1:${port}/wake`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ recipient: "civis" }),
    });

    assert.equal(wrong.status, 401);
    assert.equal(missing.status, 401);
    assert.equal(calls.length, 0, "a rejected token must never drive the waker");
    assert.ok(token);
  });

  test("GET /healthz answers without a token", async (t) => {
    const { port } = await withReceiver(t, { waker: noopWaker });

    const res = await fetch(`http://127.0.0.1:${port}/healthz`);
    assert.equal(res.status, 200);
    assert.deepEqual(await res.json(), { ok: true });
  });

  test("a missing recipient is a 400 and never drives the waker", async (t) => {
    const { post, calls } = await withReceiver(t, {
      recipientMap: { civis: { paneId: "wE:p1" } },
      panes: [pane("wE:p1")],
      focusedPaneId: "wE:p1",
    });

    const response = await post({});
    assert.equal(response.status, 400);
    assert.match(response.json.error, /recipient required/);
    assert.equal(calls.length, 0);
  });

  test("a per-minute rate limit returns 429 and never drives the waker past the budget", async (t) => {
    const { post, calls } = await withReceiver(t, {
      recipientMap: { civis: { paneId: "wE:p1" } },
      panes: [pane("wE:p1")],
      focusedPaneId: "wE:p1",
      maxPerMinute: 1,
    });

    const first = await post({ recipient: "civis" });
    const second = await post({ recipient: "civis" });

    assert.equal(first.status, 200);
    assert.equal(first.json.woke, true, first.json.detail);
    assert.equal(second.status, 429);
    assert.match(second.json.error, /slow down/);

    // Only the first request reached the waker: exactly one per-pane confirmation.
    const paneGets = calls.filter((c) => c[0] === "pane" && c[1] === "get");
    assert.equal(paneGets.length, 1, "a rate-limited request must not drive the waker");
  });
});

describe("dry-run never moves a pane", () => {
  test("buildWaker returns a no-op waker in dry-run and never invokes the runner", async () => {
    const calls = [];
    const runner = async (args) => {
      calls.push([...args]);
      return { result: {} };
    };

    const waker = buildWaker({ dryRun: true, recipientMap: { civis: { paneId: "wE:p1" } } }, runner);
    const result = await waker("civis", {});

    assert.equal(result.woke, false);
    assert.match(result.detail, /dry-run/);
    assert.equal(calls.length, 0, "dry-run must never invoke any herdr command");
    assert.equal(
      calls.some((c) => c[0] === "pane" && c[1] === "focus"),
      false,
      "dry-run must never issue a focus command",
    );
  });

  test("a dry-run receiver reports dry-run and invokes nothing", async (t) => {
    const { post, calls } = await withReceiver(t, {
      recipientMap: { civis: { paneId: "wE:p1" } },
      panes: [pane("wE:p1")],
      dryRun: true,
    });

    const response = await post({ recipient: "civis" });
    assert.equal(response.status, 200);
    assert.equal(response.json.woke, false);
    assert.match(response.json.detail, /dry-run/);
    assert.equal(calls.length, 0, "dry-run must never invoke any herdr command");
  });
});

describe("the bearer token never leaves the process", () => {
  const TOKEN = "synthetic-bearer-token-DO-NOT-LEAK-9f3a";

  test("no log line, response payload, or receipt contains the token", async (t) => {
    const logger = recordingLogger();
    const { post, logger: captured, receipts } = await withReceiver(t, {
      recipientMap: { civis: { paneId: "wE:p1" } },
      panes: [pane("wE:p1")],
      focusedPaneId: "wE:p1",
      token: TOKEN,
      logger,
    });
    assert.equal(captured, logger);

    const ok = await post({ recipient: RECIPIENT });
    const wrong = await post({ recipient: "civis" }, { token: "wrong-token" });
    const missing = await post({ recipient: "civis" }, { token: undefined });

    // Responses must never echo the token.
    for (const response of [ok, wrong, missing]) {
      assert.equal(response.text.includes(TOKEN), false, `response leaked the token: ${response.text}`);
    }

    // No log line may contain the token.
    const joined = logger.lines.join("\n");
    assert.equal(joined.includes(TOKEN), false, `a log line leaked the token:\n${joined}`);

    // The durable receipts must never contain the token.
    const stored = JSON.stringify(await receipts());
    assert.equal(stored.includes(TOKEN), false, "a receipt leaked the token");

    // Sanity: the success path really did run.
    assert.equal(ok.status, 200);
    assert.equal(ok.json.woke, true);
  });
});
