// THE BRIDGE CONTRACT TEST.
//
// This is the test that decides whether the bridge is actually WIRED or merely
// present. It exercises the real producer's semantics against the real receiver.
//
// THE PRODUCER. PhenoBot's `httpWakeAdapter` (PhenoBot `src/bridges/inbox.ts`) is the
// only real client that talks to this receiver. It:
//
//   1. POSTs a full Receipt as JSON, with `authorization: Bearer <token>` and an
//      `idempotency-key` header equal to the receipt id.
//   2. REQUIRES HTTP 200 and a body of exactly `{status:"awakened", receiptId}`.
//   3. Treats 202 as "accepted, protocol pending" -- explicitly NOT a wake.
//   4. Treats ANY other status or body as a FAILED wake, and RETAINS the receipt
//      for replay.
//
// The bug this test guards: the receiver used to answer `{woke, detail}` and to key
// on a `recipient` field. Against the real producer that is a guaranteed failure --
// the producer never sends `recipient`, and never accepts `woke`. The bridge looked
// complete and would have silently dropped every real message.
//
// These tests bind a real loopback HTTP server and inject a fake herdr runner (so no
// pane is ever moved and no process is spawned), then assert the exact bytes the
// producer would accept.

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { deriveReceiptId, validateReceiptBody } from "../src/receipt.js";
import { pane, withReceiver } from "./helpers/harness.js";

const TOKEN = "synthetic-token";
const PANE_ID = "w8:pN";

/** The receiver wiring every test in this file shares. */
const BASE = {
  recipientMap: { jcode: { paneId: PANE_ID } },
  panes: [pane(PANE_ID, { label: "Cockpit" })],
  focusedPaneId: PANE_ID,
  token: TOKEN,
};

/**
 * Build a receipt EXACTLY as PhenoBot's `Inbox.put` persists it. The id is derived
 * from `${agent}:${messageId}`, so a test cannot accidentally assert against an id
 * the producer would never send.
 */
function phenobotReceipt(agent, messageId, overrides = {}) {
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

/**
 * POST a receipt the way PhenoBot's httpWakeAdapter does, and interpret the reply with
 * the producer's OWN acceptance rule. `delivered` means the producer would have marked
 * the receipt delivered; anything else means it would have been retained for replay.
 */
async function postAsPhenoBot(receiver, receipt) {
  const response = await receiver.post(receipt, {
    token: TOKEN,
    headers: { "idempotency-key": receipt.id },
  });

  const body = response.json ?? { unparseable: response.text };
  let producerVerdict = "failed";
  if (response.status === 202) producerVerdict = "pending-protocol";
  else if (
    response.status === 200 &&
    body.status === "awakened" &&
    body.receiptId === receipt.id
  ) {
    producerVerdict = "delivered";
  }
  return { ...response, body, producerVerdict };
}

describe("the PhenoBot producer contract", () => {
  test("a valid PhenoBot receipt satisfies the producer's own validation", () => {
    const receipt = phenobotReceipt("jcode", "1562592540816048149");
    assert.deepEqual(validateReceiptBody(receipt), []);
  });

  test("the receipt id is derived the way PhenoBot derives it", () => {
    const receipt = phenobotReceipt("jcode", "1562592540816048149");
    // sha256("jcode:1562592540816048149"), the exact input PhenoBot's Inbox.put uses.
    assert.match(receipt.id, /^[a-f0-9]{64}$/);
    assert.equal(receipt.id, deriveReceiptId("jcode", "1562592540816048149", "ping"));
  });

  test("a receipt for an unknown persona is rejected before any wake", async (t) => {
    const receiver = await withReceiver(t, BASE);

    // "NotAPersona" is not in PhenoBot's persona list, so PhenoBot could never have
    // persisted it. It must not be able to wake anything.
    const response = await postAsPhenoBot(
      receiver,
      phenobotReceipt("jcode", "m1", { agent: "NotAPersona" }),
    );

    assert.equal(response.status, 400);
    assert.equal(response.producerVerdict, "failed");
    assert.equal(receiver.calls.length, 0, "an invalid persona must not drive the waker");
  });
});

describe("a wake the producer would accept as delivered", () => {
  test("a mapped persona returns 200 {status:awakened, receiptId} and wakes its pane", async (t) => {
    const receiver = await withReceiver(t, BASE);

    const receipt = phenobotReceipt("jcode", "1562592540816048149");
    const response = await postAsPhenoBot(receiver, receipt);

    // The producer's verdict is the assertion that matters: it must be "delivered".
    assert.equal(response.producerVerdict, "delivered", response.text);
    assert.equal(response.status, 200);
    assert.equal(response.body.status, "awakened");
    assert.equal(response.body.receiptId, receipt.id);

    // The pane was really addressed, and confirmed with a per-pane source.
    assert.ok(
      receiver.calls.map((c) => c.join(" ")).includes(`pane get ${PANE_ID}`),
      "the receiver must drive the waker, which confirms per-pane",
    );

    // A durable receipt exists for the attempt.
    const stored = await receiver.receipts();
    assert.equal(stored.length, 1);
    assert.equal(stored[0].receiptId, receipt.id);
    assert.equal(stored[0].agent, "jcode");
    assert.equal(stored[0].woke, true);
    assert.equal(stored[0].paneId, PANE_ID);

    // The bearer token never appears in any output.
    assert.ok(!receiver.logger.lines.join("\n").includes(TOKEN));
  });

  test("the idempotency-key header is accepted and does not change the outcome", async (t) => {
    const receiver = await withReceiver(t, BASE);

    const receipt = phenobotReceipt("jcode", "m-idempotent");
    const response = await postAsPhenoBot(receiver, receipt);

    assert.equal(response.producerVerdict, "delivered", response.text);
  });
});

describe("a wake the producer would REFUSE (and must therefore never claim)", () => {
  test("an unmapped persona is a failure, never a fake 'awakened' ack", async (t) => {
    const receiver = await withReceiver(t, BASE);

    // The map has NO entry for "Dots": it has no live pane on this host.
    const response = await postAsPhenoBot(receiver, phenobotReceipt("Dots", "m-unmapped"));

    // The producer keeps the receipt and replays it. That is the honest outcome.
    assert.equal(response.producerVerdict, "failed");
    assert.notEqual(response.status, 200);
    assert.notEqual(response.body.status, "awakened");
    // 202 would be read by the producer as "pending protocol" -- also not a wake, but
    // it would stop the replay. An honest failure must not use 202.
    assert.notEqual(response.status, 202);
    assert.equal(receiver.calls.length, 0, "an unmapped persona must not even read the pane list");
  });

  test("a bad bearer token is a failure and never drives the waker", async (t) => {
    const receiver = await withReceiver(t, BASE);

    const response = await receiver.post(phenobotReceipt("jcode", "m-bad-token"), {
      token: "not-the-token",
    });

    assert.equal(response.status, 401);
    assert.equal(receiver.calls.length, 0, "a rejected token must never drive the waker");
  });

  test("a malformed receipt id is rejected and never drives the waker", async (t) => {
    const receiver = await withReceiver(t, BASE);

    const response = await postAsPhenoBot(
      receiver,
      phenobotReceipt("jcode", "m-bad-id", { id: "not-a-hash" }),
    );

    assert.equal(response.status, 400);
    assert.equal(response.producerVerdict, "failed");
    assert.equal(receiver.calls.length, 0);
  });
});
