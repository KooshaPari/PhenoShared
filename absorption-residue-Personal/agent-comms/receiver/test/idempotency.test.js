// Idempotent replay tests.
//
// WHY THIS FILE EXISTS. PhenoBot retains any receipt it considers undelivered and re-POSTs
// it. Before the seen index, every replay walked to the pane again, woke it again, and
// appended a second receipt. That is a duplicate activation, not a retry.
//
// The rule under test:
//   * a replay of a DELIVERED receipt is acknowledged (200 awakened) without any wake;
//   * a replay of a FAILED receipt is retried (that is what the producer wants);
//   * a concurrent duplicate is refused as in-flight (503, retryable), not woken twice;
//   * the seen index persists across a restart and never stores content or the token.

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { join } from "node:path";

import { deriveReceiptId } from "../src/receipt.js";
import { SeenStore } from "../src/store.js";
import { pane, withReceiver } from "./helpers/harness.js";

const TOKEN = "synthetic-token";
const PANE_ID = "w8:pN";

const BASE = {
  recipientMap: { jcode: { paneId: PANE_ID } },
  panes: [pane(PANE_ID, { label: "Cockpit" })],
  focusedPaneId: PANE_ID,
  token: TOKEN,
};

/** Build a receipt exactly as PhenoBot's Inbox.put persists it. */
function receipt(agent, messageId, overrides = {}) {
  const content = overrides.content ?? "ping";
  return {
    id: deriveReceiptId(agent, messageId, content),
    agent,
    messageId,
    guildId: "1558641660915884154",
    channelId: "1558641660915884154",
    userId: "684729569226977292",
    content,
    ...overrides,
  };
}

/** Apply the producer's own acceptance rule to a reply. */
function producerVerdict(status, body, id) {
  if (status === 202) return "pending-protocol";
  if (status === 200 && body?.status === "awakened" && body?.receiptId === id) return "delivered";
  return "failed";
}

/** POST a receipt the way PhenoBot's httpWakeAdapter does. */
async function postAsPhenoBot(receiver, body) {
  const response = await receiver.post(body, {
    token: TOKEN,
    headers: { "idempotency-key": body.id },
  });
  return { ...response, verdict: producerVerdict(response.status, response.json, body.id) };
}

describe("idempotent replay", () => {
  test("a replayed delivered receipt is acknowledged without a second wake", async (t) => {
    let wakes = 0;
    const waker = async () => {
      wakes += 1;
      return { woke: true, detail: "ok", paneId: PANE_ID };
    };
    const receiver = await withReceiver(t, { ...BASE, waker });
    const r = receipt("jcode", "m-duplicate");

    const first = await postAsPhenoBot(receiver, r);
    const second = await postAsPhenoBot(receiver, r);

    assert.equal(first.verdict, "delivered", first.text);
    assert.equal(second.verdict, "delivered", second.text);
    assert.equal(wakes, 1, "a delivered replay must not walk the pane again");

    // No second durable receipt: a duplicate is not a second wake.
    const stored = await receiver.receipts();
    assert.equal(stored.length, 1);
    assert.equal(receiver.seen.get(r.id).status, "delivered");
  });

  test("a replayed failed receipt is retried and can then succeed", async (t) => {
    let wakes = 0;
    const waker = async () => {
      wakes += 1;
      return wakes === 1
        ? { woke: false, detail: "not ready" }
        : { woke: true, detail: "ok", paneId: PANE_ID };
    };
    const receiver = await withReceiver(t, { ...BASE, waker });
    const r = receipt("jcode", "m-retry");

    const first = await postAsPhenoBot(receiver, r);
    const second = await postAsPhenoBot(receiver, r);

    // A failure must not be 202 (the producer would stop replaying without a wake).
    assert.equal(first.verdict, "failed");
    assert.notEqual(first.status, 202);
    assert.equal(second.verdict, "delivered", second.text);
    assert.equal(wakes, 2, "a failed receipt must be retried, not short-circuited");

    const stored = await receiver.receipts();
    assert.equal(stored.length, 2);
    assert.equal(receiver.seen.get(r.id).status, "delivered");
  });

  test("the seen index persists across a restart", async (t) => {
    const receiver = await withReceiver(t, BASE);
    const r = receipt("jcode", "m-persist");

    await postAsPhenoBot(receiver, r);

    // A new store over the same state dir models a receiver restart.
    const reloaded = new SeenStore(receiver.stateDir);
    assert.equal(reloaded.get(r.id)?.status, "delivered");
  });

  test("the seen index stores only id/status/ts, never content or the token", async (t) => {
    const receiver = await withReceiver(t, BASE);
    const r = receipt("jcode", "m-secret", { content: "SECRET-MESSAGE-BODY" });

    await postAsPhenoBot(receiver, r);

    const raw = await readFile(join(receiver.stateDir, "seen.jsonl"), "utf8");
    assert.equal(raw.includes("SECRET-MESSAGE-BODY"), false, "the seen index must not store content");
    assert.equal(raw.includes(TOKEN), false, "the seen index must not store the token");

    const entry = JSON.parse(raw.trim().split("\n")[0]);
    assert.deepEqual(Object.keys(entry).sort(), ["attempted_at", "attempts", "id", "status", "ts"]);
  });

  test("a concurrent duplicate is refused in-flight, not woken twice", async (t) => {
    let wakes = 0;
    let release;
    const gate = new Promise((resolve) => {
      release = resolve;
    });
    const waker = async () => {
      wakes += 1;
      await gate;
      return { woke: true, detail: "ok", paneId: PANE_ID };
    };
    const receiver = await withReceiver(t, { ...BASE, waker });
    const r = receipt("jcode", "m-inflight");

    const firstPromise = postAsPhenoBot(receiver, r);
    // Wait until the first request has entered the waker (it is now in flight).
    while (wakes === 0) await new Promise((resolve) => setTimeout(resolve, 1));

    const second = await postAsPhenoBot(receiver, r);
    release();
    const first = await firstPromise;

    assert.equal(first.verdict, "delivered", first.text);
    assert.equal(second.status, 503);
    assert.equal(second.json.detail, "duplicate in flight");
    assert.equal(wakes, 1, "a concurrent duplicate must not walk the pane");
  });

  test("a delivered duplicate does not consume the rate-limit budget", async (t) => {
    const receiver = await withReceiver(t, { ...BASE, maxPerMinute: 1 });
    const r = receipt("jcode", "m-budget");

    assert.equal((await postAsPhenoBot(receiver, r)).verdict, "delivered");
    // The duplicate short-circuits before the rate limiter, so the one-per-minute budget
    // is still available to a genuinely new receipt.
    assert.equal((await postAsPhenoBot(receiver, r)).verdict, "delivered");

    const other = await postAsPhenoBot(receiver, receipt("jcode", "m-budget-2"));
    assert.equal(other.status, 429);
  });

  test("the local recipient shape is not deduped because it carries no receipt id", async (t) => {
    let wakes = 0;
    const waker = async () => {
      wakes += 1;
      return { woke: true, detail: "ok", paneId: PANE_ID };
    };
    const receiver = await withReceiver(t, { ...BASE, waker });

    await receiver.post({ recipient: "jcode" }, { token: TOKEN });
    await receiver.post({ recipient: "jcode" }, { token: TOKEN });

    assert.equal(wakes, 2, "a local probe without an id is not a replayable receipt");
  });
});
