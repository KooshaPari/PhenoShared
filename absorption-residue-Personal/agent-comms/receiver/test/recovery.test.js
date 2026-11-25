// Crash, persistence-failure, and recovery tests for the replay protocol.
//
// WHY THIS FILE EXISTS. `idempotency.test.js` proves the happy replay rules (delivered is
// acknowledged, failed is retried). It does not prove what happens when the process dies or
// the disk refuses a write, which is precisely where an idempotency scheme either earns its
// keep or quietly lies. The rules under test here:
//
//   1. A durable INTENT is written before the pane is walked.
//   2. An interrupted attempt leaves `pending` on disk, and a replay of it FAILS CLOSED:
//      no 200 "awakened", no second wake, no automatic retry. Only an operator resolves it.
//   3. A successful reply is sent ONLY after the outcome is durable. A write failure after a
//      wake is answered as a refusal, never as delivery.
//   4. Disk errors are surfaced as a code, with no token or message body anywhere in the
//      response or the logs.
//   5. A KNOWN failure may be retried (before and after a restart).
//   6. A receipt id that does not derive from its own agent/messageId is refused, and an id
//      already recorded under different fields is refused as a collision.
//
// These tests never touch herdr: the waker is injected, and every receiver binds loopback.

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { appendFileSync, mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { deriveReceiptId } from "../src/receipt.js";
import { createReceiver } from "../src/server.js";
import { SeenIndexCapacityError, SeenStore } from "../src/store.js";
import { pane, withReceiver } from "./helpers/harness.js";

const TOKEN = "synthetic-token";
const PANE_ID = "w8:pN";
const SECRET_BODY = "SECRET-MESSAGE-BODY-DO-NOT-PERSIST";

const BASE = {
  recipientMap: { jcode: { paneId: PANE_ID } },
  panes: [pane(PANE_ID, { label: "Cockpit" })],
  focusedPaneId: PANE_ID,
  token: TOKEN,
};

function receipt(agent, messageId, overrides = {}) {
  return {
    id: deriveReceiptId(agent, messageId, SECRET_BODY),
    agent,
    messageId,
    guildId: "1558641660915884154",
    channelId: "1558641660915884154",
    userId: "684729569226977292",
    content: SECRET_BODY,
    ...overrides,
  };
}

/** Read a JSONL file into parsed entries, [] when it does not exist. */
function readJsonl(stateDir, name) {
  let raw;
  try {
    raw = readFileSync(join(stateDir, name), "utf8");
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
  return raw
    .trim()
    .split("\n")
    .filter(Boolean)
    .map((line) => {
      try {
        return JSON.parse(line);
      } catch {
        return { unparsable: line };
      }
    });
}

/** An errno-shaped failure, as the filesystem would raise it. */
function diskError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

/**
 * Wrap a real SeenStore so that recording one specific status throws, standing in for a
 * full or read-only disk at exactly that point in the protocol.
 */
function seenFailingOn(real, failingStatus) {
  return {
    get: (id) => real.get(id),
    record: (id, status) => {
      if (status === failingStatus) {
        throw diskError("ENOSPC", "ENOSPC: no space left on device, write");
      }
      return real.record(id, status);
    },
  };
}

/** A receipt log that refuses every append. */
function storeFailing() {
  return {
    add: () => {
      throw diskError("EACCES", "EACCES: permission denied, open 'receipts.jsonl'");
    },
  };
}

async function postAsPhenoBot(receiver, body) {
  const response = await receiver.post(body, {
    token: TOKEN,
    headers: { "idempotency-key": body.id },
  });
  const delivered =
    response.status === 200 &&
    response.json?.status === "awakened" &&
    response.json?.receiptId === body.id;
  return { ...response, delivered };
}

describe("durable intent before the wake", () => {
  test("the pending intent is on disk before the waker is invoked", async (t) => {
    let intentSeen = null;
    let stateDirRef;
    const waker = async () => {
      // Read the durable file from inside the waker: this is the exact moment the pane would
      // be walked, so anything the crash story depends on must already be there.
      intentSeen = readJsonl(stateDirRef, "seen.jsonl");
      return { woke: true, detail: "ok", paneId: PANE_ID };
    };
    const receiver = await withReceiver(t, { ...BASE, waker });
    stateDirRef = receiver.stateDir;

    const r = receipt("jcode", "m-intent");
    const result = await postAsPhenoBot(receiver, r);

    assert.equal(result.delivered, true, result.text);
    assert.equal(intentSeen.length, 1, "exactly one index line exists during the walk");
    assert.equal(intentSeen[0].id, r.id);
    assert.equal(intentSeen[0].status, "pending", "the intent must precede the wake");
  });

  test("a failed attempt is durably marked failed, not left pending", async (t) => {
    const waker = async () => ({ woke: false, detail: "not ready" });
    const receiver = await withReceiver(t, { ...BASE, waker });
    const r = receipt("jcode", "m-known-failure");

    const result = await postAsPhenoBot(receiver, r);
    assert.equal(result.delivered, false);
    assert.equal(result.status, 503);

    const lines = readJsonl(receiver.stateDir, "seen.jsonl");
    assert.deepEqual(
      lines.map((entry) => entry.status),
      ["pending", "failed"],
      "a known failure is terminal for this attempt",
    );
  });

  test("a waker that throws is a known failure and is retried, not left uncertain", async (t) => {
    let attempts = 0;
    const waker = async () => {
      attempts += 1;
      if (attempts === 1) throw new Error("herdr exited 1");
      return { woke: true, detail: "ok", paneId: PANE_ID };
    };
    const receiver = await withReceiver(t, { ...BASE, waker });
    const r = receipt("jcode", "m-waker-throws");

    const first = await postAsPhenoBot(receiver, r);
    assert.equal(first.delivered, false);
    assert.equal(first.status, 502);
    // A thrown waker means no pane was raised, so the outcome is KNOWN and retryable.
    assert.equal(receiver.seen.get(r.id).status, "failed");
    assert.equal(receiver.logger.lines.some((line) => line.includes("herdr exited 1")), true);

    const second = await postAsPhenoBot(receiver, r);
    assert.equal(second.delivered, true, "a known failure is retried");
    assert.equal(attempts, 2);
    assert.equal(receiver.seen.get(r.id).status, "delivered");
  });
});

describe("recovery after an interrupted attempt", () => {
  test("a pending attempt that survived a crash is refused, never delivered and never retried", async (t) => {
    // Model the crash directly: the durable state is exactly what a process killed between
    // the intent write and the outcome write would leave behind.
    const crashed = await withReceiver(t, BASE);
    const r = receipt("jcode", "m-crashed");
    crashed.seen.record(r.id, "pending");

    let wakes = 0;
    const waker = async () => {
      wakes += 1;
      return { woke: true, detail: "ok", paneId: PANE_ID };
    };
    // A fresh process over the same state dir is the restart.
    const restarted = await withReceiver(t, {
      ...BASE,
      waker,
      stateDir: crashed.stateDir,
    });

    const replays = [];
    for (let i = 0; i < 3; i += 1) replays.push(await postAsPhenoBot(restarted, r));

    for (const replay of replays) {
      assert.equal(replay.delivered, false, "an unknown outcome must never claim delivery");
      assert.equal(replay.status, 409);
      assert.equal(replay.json.code, "uncertain-outcome");
      assert.notEqual(replay.status, 202, "202 would stop the producer replaying");
    }
    assert.equal(wakes, 0, "the receiver must not re-wake a pane with an unknown outcome");
    assert.equal(
      readJsonl(restarted.stateDir, "receipts.jsonl").length,
      0,
      "a refused replay must not append a wake receipt",
    );
  });

  test("a delivered outcome survives a restart and is acknowledged without a wake", async (t) => {
    const first = await withReceiver(t, BASE);
    const r = receipt("jcode", "m-delivered-restart");
    assert.equal((await postAsPhenoBot(first, r)).delivered, true);

    let wakes = 0;
    const restarted = await withReceiver(t, {
      ...BASE,
      stateDir: first.stateDir,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });

    const replay = await postAsPhenoBot(restarted, r);
    assert.equal(replay.delivered, true);
    assert.equal(wakes, 0);
  });

  test("a known failure survives a restart and may then be retried", async (t) => {
    const first = await withReceiver(t, {
      ...BASE,
      waker: async () => ({ woke: false, detail: "not ready" }),
    });
    const r = receipt("jcode", "m-failed-restart");
    assert.equal((await postAsPhenoBot(first, r)).delivered, false);
    assert.equal(first.seen.get(r.id).status, "failed");

    let wakes = 0;
    const restarted = await withReceiver(t, {
      ...BASE,
      stateDir: first.stateDir,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });

    const retry = await postAsPhenoBot(restarted, r);
    assert.equal(retry.delivered, true, "a known failure is retryable");
    assert.equal(wakes, 1);
    assert.equal(restarted.seen.get(r.id).status, "delivered");
  });

  test("an operator can resolve an uncertain receipt by appending the outcome", async (t) => {
    const crashed = await withReceiver(t, BASE);
    const r = receipt("jcode", "m-operator-resolved");
    crashed.seen.record(r.id, "pending");
    // The documented escape hatch: a later line for the same id wins on load.
    appendFileSync(
      join(crashed.stateDir, "seen.jsonl"),
      JSON.stringify({ id: r.id, status: "delivered", ts: new Date().toISOString() }) + "\n",
    );

    let wakes = 0;
    const restarted = await withReceiver(t, {
      ...BASE,
      stateDir: crashed.stateDir,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });

    const replay = await postAsPhenoBot(restarted, r);
    assert.equal(replay.delivered, true);
    assert.equal(wakes, 0, "a resolved receipt is acknowledged, not re-woken");
  });

  test("a torn index line REFUSES startup instead of being skipped", async (t) => {
    const first = await withReceiver(t, BASE);
    const r = receipt("jcode", "m-torn");
    assert.equal((await postAsPhenoBot(first, r)).delivered, true);
    appendFileSync(join(first.stateDir, "seen.jsonl"), '{"id":"truncated-because-the-process-' + SECRET_BODY + '"\n');

    // Skipping the line would silently drop an unknown transition: if that line had been a
    // `pending`, the next replay would wake the pane again. Refusing to start is the only
    // honest answer, and it never runs a wake path.
    let thrown;
    assert.throws(
      () => new SeenStore(first.stateDir),
      (error) => {
        thrown = error;
        return error.code === "seen-index-corrupt" && error.line === 3;
      },
    );
    assert.equal(String(thrown.message).includes(SECRET_BODY), false, "no index content in the error");
    assert.match(String(thrown.message), /line 3/);
  });
});

describe("persistence failures fail closed", () => {
  test("a failed intent write refuses the wake and never touches the pane", async (t) => {
    let wakes = 0;
    const stateDir = (await withReceiver(t, BASE)).stateDir;
    const seen = seenFailingOn(new SeenStore(stateDir), "pending");
    const receiver = await withReceiver(t, {
      ...BASE,
      stateDir,
      seen,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });

    const r = receipt("jcode", "m-intent-fails");
    const result = await postAsPhenoBot(receiver, r);

    assert.equal(result.delivered, false);
    assert.equal(result.status, 500);
    assert.equal(result.json.code, "intent-not-durable");
    assert.equal(wakes, 0, "no intent, no wake");
    assert.equal(readJsonl(stateDir, "receipts.jsonl").length, 0);
  });

  test("an unrecordable success is refused, not reported as delivered", async (t) => {
    const base = await withReceiver(t, BASE);
    const seen = seenFailingOn(new SeenStore(base.stateDir), "delivered");
    let wakes = 0;
    const receiver = await withReceiver(t, {
      ...BASE,
      stateDir: base.stateDir,
      seen,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });

    const r = receipt("jcode", "m-outcome-fails");
    const result = await postAsPhenoBot(receiver, r);

    assert.equal(result.delivered, false, "an unrecorded outcome must not be claimed");
    assert.equal(result.status, 500);
    assert.equal(result.json.code, "outcome-not-durable");
    assert.equal(wakes, 1, "the wake did happen; it simply could not be recorded");

    // The durable index is left at `pending`, so a later replay fails closed instead of
    // waking the pane a second time.
    const lines = readJsonl(base.stateDir, "seen.jsonl");
    assert.equal(lines.at(-1).status, "pending");
  });

  test("after an unrecordable success, a restart refuses the replay", async (t) => {
    const base = await withReceiver(t, BASE);
    const seen = seenFailingOn(new SeenStore(base.stateDir), "delivered");
    let wakes = 0;
    const broken = await withReceiver(t, {
      ...BASE,
      stateDir: base.stateDir,
      seen,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });

    const r = receipt("jcode", "m-outcome-fails-restart");
    await postAsPhenoBot(broken, r);

    const restarted = await withReceiver(t, {
      ...BASE,
      stateDir: base.stateDir,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });
    const replay = await postAsPhenoBot(restarted, r);

    assert.equal(replay.delivered, false);
    assert.equal(replay.json.code, "uncertain-outcome");
    assert.equal(wakes, 1, "exactly one wake attempt across both processes");
  });

  test("a receipt-log write failure surfaces as an errno code with no secrets", async (t) => {
    const base = await withReceiver(t, BASE);
    const receiver = await withReceiver(t, {
      ...BASE,
      stateDir: base.stateDir,
      store: storeFailing(),
      waker: async () => ({ woke: true, detail: "ok", paneId: PANE_ID }),
    });

    const r = receipt("jcode", "m-receipt-log-fails");
    const result = await postAsPhenoBot(receiver, r);

    assert.equal(result.delivered, false);
    assert.equal(result.status, 500);
    assert.equal(result.json.code, "outcome-not-durable");

    // A disk failure is diagnosable, but only as a code: no token, no message body, and no
    // control characters smuggled into the log stream.
    const everything = result.text + receiver.logger.lines.join("\n");
    assert.equal(everything.includes(TOKEN), false, "the bearer token never leaks");
    assert.equal(everything.includes(SECRET_BODY), false, "the message body never leaks");
    assert.match(everything, /EACCES/);
    assert.equal(/[\r\n]\s*(wake|error)/.test(result.json.error ?? ""), false);
  });

  test("a failed attempt whose failure cannot be recorded stays uncertain", async (t) => {
    const base = await withReceiver(t, BASE);
    const seen = seenFailingOn(new SeenStore(base.stateDir), "failed");
    const receiver = await withReceiver(t, {
      ...BASE,
      stateDir: base.stateDir,
      seen,
      waker: async () => ({ woke: false, detail: "not ready" }),
    });

    const r = receipt("jcode", "m-failure-unrecordable");
    const result = await postAsPhenoBot(receiver, r);

    assert.equal(result.delivered, false);
    assert.equal(result.status, 500);
    assert.equal(result.json.code, "outcome-not-durable");
    assert.equal(readJsonl(base.stateDir, "seen.jsonl").at(-1).status, "pending");
  });
});

describe("receipt id integrity", () => {
  test("an id that does not derive from agent/messageId is refused before any wake", async (t) => {
    let wakes = 0;
    const receiver = await withReceiver(t, {
      ...BASE,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });

    const r = receipt("jcode", "m-mismatch", { messageId: "a-different-message" });
    const result = await postAsPhenoBot(receiver, r);

    assert.equal(result.status, 400);
    assert.equal(result.json.code, "receipt-id-mismatch");
    assert.equal(wakes, 0);
  });

  test("an id already recorded under different fields is refused as a collision", async (t) => {
    let wakes = 0;
    const receiver = await withReceiver(t, {
      ...BASE,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });

    const original = receipt("jcode", "m-collision-source");
    assert.equal((await postAsPhenoBot(receiver, original)).delivered, true);

    // Same id, different (agent, messageId): the id no longer derives from its own fields,
    // and it is already on record, so this is a collision rather than a malformed body.
    const impostor = receipt("jcode", "m-collision-impostor", { id: original.id });
    const result = await postAsPhenoBot(receiver, impostor);

    assert.equal(result.status, 409);
    assert.equal(result.json.code, "receipt-id-collision");
    assert.equal(wakes, 1, "the original wake only");
    assert.equal(receiver.seen.get(original.id).status, "delivered");
  });
});

describe("concurrency scope", () => {
  test("distinct receipts in flight together do not block or cross-contaminate", async (t) => {
    const started = [];
    let release;
    const gate = new Promise((resolve) => {
      release = resolve;
    });
    const waker = async (_recipient, body) => {
      started.push(body.receiptId);
      await gate;
      return { woke: true, detail: "ok", paneId: PANE_ID };
    };
    const receiver = await withReceiver(t, { ...BASE, waker });

    const a = receipt("jcode", "m-parallel-a");
    const b = receipt("jcode", "m-parallel-b");
    const first = postAsPhenoBot(receiver, a);
    while (started.length < 1) await new Promise((resolve) => setTimeout(resolve, 1));
    const second = postAsPhenoBot(receiver, b);
    while (started.length < 2) await new Promise((resolve) => setTimeout(resolve, 1));

    assert.equal(receiver.seen.get(a.id).status, "pending");
    assert.equal(receiver.seen.get(b.id).status, "pending");

    release();
    const [ra, rb] = await Promise.all([first, second]);
    assert.equal(ra.delivered, true);
    assert.equal(rb.delivered, true);
    assert.deepEqual(started.sort(), [a.id, b.id].sort());
    assert.equal(receiver.seen.get(a.id).status, "delivered");
    assert.equal(receiver.seen.get(b.id).status, "delivered");
  });
});

// The bounded index has several ways to lose the truth (stale recency on reload, compaction
// evicting an unknown outcome, a torn tail swallowing the next record, and capacity pressure).
// Each one is exercised here at the store level, because these are properties of the file
// format rather than of the HTTP surface.
const SEEN_MAX = 10_000;

function seenLine(id, status) {
  return JSON.stringify({ id, status, ts: "2026-10-29T00:00:00.000Z" });
}

/** A state dir holding a hand-built seen.jsonl, with no receiver attached. */
function storeOver(lines) {
  const dir = mkdtempSync(join(tmpdir(), "seen-test-"));
  writeFileSync(join(dir, "seen.jsonl"), lines.join("\n") + "\n");
  return { dir, store: new SeenStore(dir) };
}

describe("index hardening", () => {
  test("re-loading refreshes recency for an id recorded twice", () => {
    const lines = [seenLine("resolved-late", "pending")];
    for (let i = 0; i < SEEN_MAX; i += 1) lines.push(seenLine(`filler-${i}`, "delivered"));
    lines.push(seenLine("resolved-late", "delivered"));

    const { store } = storeOver(lines);
    const keys = [...store.map.keys()];
    assert.equal(keys.at(-1), "resolved-late", "the later line must move the id to the newest slot");
    assert.equal(store.get("resolved-late").status, "delivered");
  });

  test("compaction never evicts a pending entry, however old", () => {
    const lines = [seenLine("ancient-pending", "pending")];
    for (let i = 0; i < SEEN_MAX - 1; i += 1) lines.push(seenLine(`settled-${i}`, "delivered"));
    const { dir, store } = storeOver(lines);
    assert.equal(store.map.size, SEEN_MAX);

    store.record("brand-new", "pending"); // size SEEN_MAX+1 -> compaction runs

    assert.equal(store.get("ancient-pending")?.status, "pending", "an unknown outcome is never dropped");
    assert.equal(store.get("brand-new")?.status, "pending");
    assert.ok(store.map.size <= SEEN_MAX, `size stays bounded, got ${store.map.size}`);
    // The rewritten file must still be loadable and must still hold the pending entry.
    const reloaded = new SeenStore(dir);
    assert.equal(reloaded.get("ancient-pending")?.status, "pending");
    assert.ok(reloaded.map.size <= SEEN_MAX);
  });

  test("capacity fails closed when every slot holds an unresolved receipt", () => {
    const lines = [];
    for (let i = 0; i < SEEN_MAX; i += 1) lines.push(seenLine(`stuck-${i}`, "pending"));
    const { store } = storeOver(lines);

    assert.throws(
      () => store.record("would-need-an-eviction", "pending"),
      (error) => error instanceof SeenIndexCapacityError && error.code === "seen-index-at-capacity",
    );
    // A transition of an id that is already on record needs no room and is still allowed.
    store.record("stuck-0", "delivered");
    assert.equal(store.get("stuck-0").status, "delivered");
  });

  test("a file without a trailing newline does not swallow the next record", () => {
    const dir = mkdtempSync(join(tmpdir(), "seen-test-"));
    // No trailing newline: the next append would otherwise splice onto this line.
    writeFileSync(join(dir, "seen.jsonl"), seenLine("first", "delivered"));
    const store = new SeenStore(dir);
    assert.equal(store.get("first").status, "delivered");

    store.record("second", "delivered");
    const reloaded = new SeenStore(dir);
    assert.equal(reloaded.get("first")?.status, "delivered");
    assert.equal(reloaded.get("second")?.status, "delivered", "the appended record must stay parseable");
  });

  test("createReceiver refuses to build without a seen index", () => {
    const store = { add: () => {} };
    assert.throws(
      () =>
        createReceiver({
          store,
          waker: async () => ({ woke: true, detail: "ok" }),
          token: TOKEN,
          logger: { info: () => {}, warn: () => {} },
        }),
      (error) => error instanceof TypeError && /seen index/.test(error.message),
    );
  });

  test("an at-capacity index refuses the wake with its own code, and wakes nothing", async (t) => {
    let wakes = 0;
    const base = await withReceiver(t, BASE);
    const real = new SeenStore(base.stateDir);
    const seen = {
      get: (id) => real.get(id),
      record: (id, status) => {
        if (status === "pending") throw new SeenIndexCapacityError(SEEN_MAX);
        return real.record(id, status);
      },
    };
    const receiver = await withReceiver(t, {
      ...BASE,
      stateDir: base.stateDir,
      seen,
      waker: async () => {
        wakes += 1;
        return { woke: true, detail: "ok", paneId: PANE_ID };
      },
    });

    const result = await postAsPhenoBot(receiver, receipt("jcode", "m-at-capacity"));
    assert.equal(result.delivered, false);
    assert.equal(result.status, 503);
    assert.equal(result.json.code, "index-at-capacity");
    assert.equal(wakes, 0);
    assert.equal(readJsonl(base.stateDir, "receipts.jsonl").length, 0);
  });
});
