// The receiver HTTP surface. Loopback only, bearer-token gated, no secrets in any output.
//
// THE WIRE CONTRACT. The only real producer is PhenoBot's agent bridge, whose client
// (`httpWakeAdapter`, PhenoBot `src/bridges/inbox.ts`) POSTs a full Receipt and accepts
// the wake ONLY when the response body is exactly:
//
//     { "status": "awakened", "receiptId": "<the receipt id it sent>" }
//
// and the HTTP status is NOT 202. Anything else is a failed wake: PhenoBot keeps the
// receipt and replays it. This receiver therefore speaks that contract, and
// `receipt.js` is the single place the contract is defined.
//
// The OLD local-only shape (`{recipient}` in, `{woke, detail}` out) is still accepted
// so a local operator script or a curl probe keeps working, but it is NOT what the
// bridge producer uses. Two request shapes, one honest outcome.
//
// The recipient/persona map IS the write scope: a request can only ever wake a pane
// the operator explicitly mapped, so there is no path to an arbitrary pane. `maxPerMinute`
// mirrors the herdr-facade rate limit; 0 disables it.
//
// SINGLE-PROCESS CONSTRAINT. The idempotency index this handler uses is an in-memory map
// over a file plus a per-process in-flight set. It serialises duplicates inside ONE
// receiver process and nothing more: there is no lock file, no advisory lock, and no
// cross-process lease. Two receiver processes sharing a state directory would each answer
// from their own snapshot and could both walk the same pane; with the 30s lease, one could
// even retry an attempt the other is still running. Run exactly one receiver per state dir.
import http from "node:http";
import { timingSafeEqual } from "node:crypto";

import { normalizeRecipient } from "./mapping.js";
import { logSafe } from "./log-safe.js";
import { awakenedAck, deriveReceiptId, validateReceiptBody } from "./receipt.js";
import { SEEN_MAX_ATTEMPTS, isExhausted, isLeaseExpired } from "./store.js";

const MAX_BODY_BYTES = 16 * 1024;

/**
 * Render a filesystem failure as a short, sanitised detail. The errno code is the useful
 * part (`ENOSPC`, `EACCES`, `EROFS`); the message is truncated and control-escaped because
 * it is the one field that came from outside this process. Nothing here can carry the
 * bearer token, and the message is capped so a pathological error cannot flood a response.
 *
 * @param {unknown} error
 * @returns {string}
 */
function durableFailureDetail(error) {
  const code = typeof (/** @type {any} */ (error)?.code) === "string" ? error.code : "EUNKNOWN";
  const message = error instanceof Error ? error.message : String(error);
  return `${code}: ${logSafe(message).slice(0, 200)}`;
}

/**
 * Run a durable write sequence and report whether it landed, without throwing.
 *
 * The caller must never answer `awakened` on the strength of a write that failed, but it
 * also must not crash the request handler: the honest response is a refusal, and the
 * evidence of what did and did not reach the disk belongs in the reply and the log.
 *
 * @param {() => void} write
 * @returns {{ok: true} | {ok: false, error: unknown}}
 */
function recordOutcome(write) {
  try {
    write();
    return { ok: true };
  } catch (error) {
    return { ok: false, error };
  }
}

/**
 * Constant-time bearer comparison so the token is never leaked via timing side-channels.
 * @param {string} a
 * @param {string} b
 * @returns {boolean}
 */
function safeEqual(a, b) {
  const ab = Buffer.from(String(a));
  const bb = Buffer.from(String(b));
  if (ab.length !== bb.length) return false;
  return timingSafeEqual(ab, bb);
}

/**
 * Read a JSON body with a size cap. Never throws on a malformed body.
 * @param {import("node:http").IncomingMessage} req
 * @returns {Promise<any>}
 */
function readJson(req) {
  return new Promise((resolve) => {
    let raw = "";
    let overflow = false;
    req.on("data", (chunk) => {
      if (overflow) return;
      raw += chunk;
      if (raw.length > MAX_BODY_BYTES) {
        overflow = true;
        raw = "";
      }
    });
    req.on("end", () => {
      if (overflow || !raw) return resolve(undefined);
      try {
        resolve(JSON.parse(raw));
      } catch {
        resolve(undefined);
      }
    });
    req.on("error", () => resolve(undefined));
  });
}

/**
 * Build the request handler. `token` is read once and NEVER passed to the logger, never
 * included in a response, and never written to disk.
 *
 * `seen` is REQUIRED. It used to be optional, which meant a caller could build a receiver
 * that accepts PhenoBot receipts with no idempotency at all: every replay would walk the
 * pane again, and nothing in the reply would say so. A receiver that cannot dedupe must not
 * pretend to, so a missing index is a construction error rather than a silent downgrade.
 *
 * @param {{store: import("./store.js").ReceiptStore, seen: import("./store.js").SeenStore, waker: (recipient: string, receipt: Record<string, any>) => Promise<{woke: boolean, detail: string, paneId?: string}>, token: string, logger: {info: Function, warn: Function}, maxPerMinute?: number}} deps
 * @returns {(req: import("node:http").IncomingMessage, res: import("node:http").ServerResponse) => Promise<void>}
 */
export function createReceiver({ store, seen, waker, token, logger, maxPerMinute = 30 }) {
  if (!seen || typeof seen.record !== "function" || typeof seen.get !== "function") {
    throw new TypeError("createReceiver requires a seen index (no idempotency bypass)");
  }
  // Sliding one-minute window, exactly the facade's shape: a bounded number of accepted
  // wake attempts per minute, independent of the per-request token check.
  /** @type {number[]} */
  const stamps = [];
  // Receipt ids currently being walked. A concurrent duplicate is answered 503 (a failed
  // wake, so the producer retries) rather than racing a second walk to the same pane.
  /** @type {Set<string>} */
  const inFlight = new Set();
  function rateOk() {
    if (!(maxPerMinute > 0)) return true;
    const now = Date.now();
    while (stamps.length && now - stamps[0] > 60_000) stamps.shift();
    if (stamps.length >= maxPerMinute) return false;
    stamps.push(now);
    return true;
  }

  return async function handler(req, res) {
    const url = new URL(req.url ?? "/", "http://127.0.0.1");
    const send = (code, body) => {
      res.writeHead(code, { "content-type": "application/json", "cache-control": "no-store" });
      res.end(JSON.stringify(body));
    };

    if (req.method === "GET" && url.pathname === "/healthz") {
      return send(200, { ok: true });
    }

    if (req.method !== "POST" || url.pathname !== "/wake") {
      return send(404, { error: "not found" });
    }

    // Bearer gate. A wrong or missing token is logged as a fact, never with the token value.
    const auth = req.headers.authorization ?? "";
    const match = /^Bearer\s+(.+)$/i.exec(auth);
    const supplied = match ? match[1].trim() : "";
    if (!safeEqual(supplied, token)) {
      logger.warn("wake denied: bad or missing bearer token");
      return send(401, { error: "unauthorized" });
    }

    const body = await readJson(req);
    if (!body || typeof body !== "object" || Array.isArray(body)) {
      return send(400, { error: "receipt body required" });
    }

    // The PhenoBot shape is authoritative. A body that carries an `id` is a Receipt.
    const isReceipt = typeof body.id === "string";
    if (isReceipt) {
      const problems = validateReceiptBody(body);
      if (problems.length > 0) {
        logger.warn(`wake rejected: invalid receipt (${problems.join("; ")})`);
        return send(400, { error: "invalid receipt", problems });
      }
      // RECEIPT-ID COLLISION. The id is sha256(`${agent}:${messageId}:${sha256(content)}`), so
      // an id that does not match its own fields is either corrupt or a different receipt
      // claiming an existing id. Both must be refused: a mismatched id would make the
      // idempotency index answer for a message it never saw.
      //
      // Content is part of the derivation so an AMENDED body (same messageId, corrected text)
      // is a distinct receipt instead of a replay of the old one. A producer that still sends
      // the old `sha256(agent:messageId)` id is refused here rather than deduped against
      // content it never delivered.
      const derived = deriveReceiptId(body.agent, body.messageId, body.content);
      if (derived !== body.id) {
        const known = seen?.get(body.id);
        if (known) {
          logger.warn(`wake rejected: receipt id collision for ${body.agent}`);
          return send(409, {
            error: "receipt id already recorded for different receipt fields",
            code: "receipt-id-collision",
            receiptId: body.id,
          });
        }
        logger.warn(`wake rejected: receipt id does not match agent/messageId`);
        return send(400, {
          error: "receipt id must equal sha256(agent:messageId:sha256(content))",
          code: "receipt-id-mismatch",
          problems: ["id does not derive from agent, messageId, and content"],
        });
      }
    } else {
      // The local-only shape: a bare recipient, with no receipt to acknowledge.
      if (typeof body.recipient !== "string" || !normalizeRecipient(body.recipient)) {
        return send(400, { error: "recipient required" });
      }
    }

    // Recipients are keyed by LOCAL PART. The domain is never used for routing.
    // For a Receipt the key is the PERSONA name (`jcode`, `Instinct`, ...), which the
    // same map may also carry, so both legs resolve through one table.
    const key = isReceipt ? body.agent : normalizeRecipient(body.recipient);
    const recipient = normalizeRecipient(key);

    const receipt = {
      ts: new Date().toISOString(),
      recipient,
      ...(isReceipt
        ? {
            receiptId: body.id,
            agent: body.agent,
            messageId: typeof body.messageId === "string" ? body.messageId : undefined,
            subject: undefined,
          }
        : {
            messageId: typeof body.messageId === "string" && body.messageId ? body.messageId : undefined,
            subject: typeof body.subject === "string" ? body.subject.slice(0, 200) : undefined,
          }),
    };

    // IDEMPOTENT REPLAY, WITH AN HONEST UNKNOWN STATE.
    //
    // The producer keeps a receipt it considers undelivered and re-POSTs it. The four
    // possible answers to a replay:
    //
    //   delivered  -> 200 {status:"awakened"} with no pane walk and no second receipt line;
    //   failed     -> retried, because that is exactly what the producer is asking for, until
    //                 the attempt budget is spent;
    //   exhausted  -> 409 attempts-exhausted. Three failed attempts mean the receipt is
    //                 unwakeable as written: walking the pane again only repeats the failure,
    //                 and answering `awakened` would be a delivered claim with nothing behind
    //                 it. An operator resolves it (see the `resolve` command);
    //   pending    -> 409 uncertain, FAIL CLOSED while the lease is live. The outcome is
    //                 unknown (in flight, or the process just died mid-wake). This receiver
    //                 will not claim delivery and will not re-wake the pane. Once the 30s
    //                 lease has lapsed the attempt is presumed dead and the receipt becomes
    //                 retryable, so a crash cannot block the receipt forever;
    //   absent     -> a first attempt.
    //
    // This is deliberately NOT exactly-once delivery. See README "Scope and guarantees".
    const dedupe = Boolean(isReceipt && seen);
    // 1-based number of the attempt THIS request is starting, used only to label the reply
    // when the attempt that just failed was the last one the receipt is allowed.
    let attemptNumber = 1;
    if (dedupe) {
      const prior = seen.get(body.id);
      const attempts = prior && Number.isInteger(prior.attempts) ? prior.attempts : 0;
      attemptNumber = attempts + 1;
      const leaseExpired = isLeaseExpired(prior);
      if (prior && prior.status === "delivered") {
        logger.info(`wake duplicate for ${recipient}: already delivered`, { receiptId: body.id });
        return send(200, awakenedAck(body.id));
      }
      // A duplicate of THIS process's live attempt is retryable, not uncertain: the in-flight
      // set only ever holds ids this process is walking right now, so the outcome is coming.
      // This check precedes the `pending` check because a live attempt also has a durable
      // `pending` line, and 503 (retry later) is the honest answer for it.
      if (inFlight.has(body.id)) {
        // 503 is a failed wake, so the producer retains the receipt and replays it later,
        // by which time the first attempt has recorded its durable outcome.
        return send(503, { status: "failed", receiptId: body.id, detail: "duplicate in flight" });
      }
      // EXHAUSTION is checked before the pending rule: a receipt whose last attempt crashed
      // after its third try must not be "retried" by the lease, and a receipt with three
      // known failures must not be re-walked on every producer pass.
      if (
        prior &&
        attempts >= SEEN_MAX_ATTEMPTS &&
        (isExhausted(prior) || (prior.status === "pending" && leaseExpired))
      ) {
        logger.warn(`wake refused for ${recipient}: attempt budget exhausted`, {
          receiptId: body.id,
          attempts,
        });
        return send(409, {
          status: "failed",
          receiptId: body.id,
          code: "attempts-exhausted",
          detail:
            `this receipt used all ${SEEN_MAX_ATTEMPTS} wake attempts without being delivered; ` +
            "it will not be retried automatically. An operator can resolve it with " +
            "`node agent-comms/receiver/src/index.js resolve <receipt-id> delivered|failed`",
        });
      }
      if (prior && prior.status === "pending" && !leaseExpired) {
        // Unknown outcome. Answering 200 would be a delivered claim this process cannot
        // support; walking the pane again risks a second activation of the same message.
        logger.warn(`wake refused for ${recipient}: previous attempt outcome unknown`, {
          receiptId: body.id,
        });
        return send(409, {
          status: "uncertain",
          receiptId: body.id,
          code: "uncertain-outcome",
          detail:
            "a previous attempt was interrupted before its outcome was recorded; " +
            "the pane is not woken again and delivery is not claimed",
        });
      }
      if (prior && prior.status === "pending" && leaseExpired) {
        // The attempt's lease lapsed: the process that wrote it is presumed dead. Retrying is
        // safe again, and it is the only way an abandoned receipt ever makes progress.
        logger.warn(`wake retrying for ${recipient}: previous attempt lease expired`, {
          receiptId: body.id,
          attempted_at: prior.attempted_at,
        });
      }
    }

    // Rate limit accepted wake attempts (the bearer gate is already passed). Return before
    // the intent write so a rate-limited request cannot fill the index with pendings.
    if (!rateOk()) {
      logger.warn(`wake rate-limited for ${recipient}`);
      // 429 is not 202 and not a 200 "awakened", so PhenoBot treats it as a failed wake
      // and retains the receipt for replay. That is the correct outcome: rate-limited
      // is not delivered.
      return send(429, { error: "slow down" });
    }

    // DURABLE INTENT BEFORE THE WAKE. If this write fails, no pane is touched: an attempt
    // whose intent could not be recorded would be a wake the receiver could never dedupe.
    if (dedupe) {
      try {
        seen.record(body.id, "pending");
      } catch (error) {
        // A full index of unresolved receipts is not a disk fault: it needs an operator.
        // Both answers refuse the wake, but the code has to say which one it is.
        if (/** @type {any} */ (error)?.code === "seen-index-at-capacity") {
          logger.warn(`wake refused for ${recipient}: index at capacity`);
          return send(503, {
            status: "failed",
            receiptId: body.id,
            code: "index-at-capacity",
            error: "too many unresolved receipts; an operator must resolve them",
          });
        }
        const detail = durableFailureDetail(error);
        logger.warn(`wake refused for ${recipient}: intent not durable (${detail})`);
        return send(500, {
          status: "failed",
          receiptId: body.id,
          code: "intent-not-durable",
          error: "could not record the wake intent",
        });
      }
      inFlight.add(body.id);
    }

    try {
      let outcome;
      try {
        outcome = await waker(recipient, receipt);
      } catch (error) {
        const detail = `wake error: ${/** @type {Error} */ (error).message}`;
        // The waker's message can quote an external response or a CLI stderr blob, so it is
        // escaped before it reaches a log line.
        logger.warn(`wake errored for ${recipient}: ${logSafe(detail)}`);
        receipt.woke = false;
        receipt.detail = detail;
        // The waker threw, so no pane was raised: `failed` is a known outcome and is
        // recorded as one. If the record itself fails, the durable state stays `pending`,
        // which replays treat as uncertain rather than retrying blind.
        const failed = recordOutcome(() => {
          store.add(receipt);
          if (dedupe) seen.record(body.id, "failed");
        });
        if (!failed.ok) {
          return send(500, {
            status: "failed",
            receiptId: isReceipt ? body.id : undefined,
            code: "outcome-not-durable",
            error: "wake failed and the failure could not be recorded",
          });
        }
        return send(502, {
          status: "failed",
          receiptId: isReceipt ? body.id : undefined,
          error: detail,
          ...(dedupe && attemptNumber >= SEEN_MAX_ATTEMPTS
            ? {
                code: "attempts-exhausted",
                detail: "no further automatic retries; an operator must resolve this receipt",
              }
            : {}),
        });
      }

      receipt.woke = outcome.woke;
      receipt.detail = outcome.detail;
      if (outcome.paneId) receipt.paneId = outcome.paneId;

      // DURABLE OUTCOME BEFORE THE REPLY. Evidence first, then the index: that order means
      // a failure at either step leaves the index at `pending` (uncertain), never a
      // `delivered` claim with no receipt behind it.
      const recorded = recordOutcome(() => {
        store.add(receipt);
        if (dedupe) seen.record(body.id, outcome.woke ? "delivered" : "failed");
      });
      if (!recorded.ok) {
        // The pane state is now genuinely unknown to the durable record: the waker returned,
        // but we cannot say for certain the outcome survived. Fail closed. Returning the
        // success ack here would be exactly the false "delivered" this protocol prevents,
        // and the next replay will read `pending` and refuse rather than re-wake.
        const detail = durableFailureDetail(recorded.error);
        logger.warn(`wake outcome not durable for ${recipient} (${detail})`);
        return send(500, {
          status: "failed",
          receiptId: isReceipt ? body.id : undefined,
          code: "outcome-not-durable",
          error: "the wake outcome could not be recorded; delivery is not claimed",
        });
      }

      // Log receipt identity only. The token is never passed to the logger.
      logger.info(`wake for ${recipient}: ${outcome.woke ? "woke" : "not woken"}`, {
        woke: outcome.woke,
        detail: outcome.detail,
      });

      if (isReceipt) {
        // The producer's contract: a 200 with {status:"awakened", receiptId} is the ONLY
        // thing that counts as delivered. A 202 means "accepted, protocol pending" and is
        // explicitly NOT a wake, so an honest failure must NOT use 202.
        if (!outcome.woke) {
          // Honest failure. The pane was not raised, so the wake did not happen. 503 keeps
          // PhenoBot's receipt in the replay queue instead of marking it delivered.
          return send(503, {
            status: "failed",
            receiptId: body.id,
            detail: outcome.detail,
            ...(attemptNumber >= SEEN_MAX_ATTEMPTS
              ? {
                  code: "attempts-exhausted",
                  attempts: attemptNumber,
                  detail:
                    `${outcome.detail} (attempt ${attemptNumber} of ${SEEN_MAX_ATTEMPTS}: ` +
                    "no further automatic retries; an operator must resolve this receipt)",
                }
              : {}),
          });
        }
        return send(200, awakenedAck(body.id));
      }

      return send(200, { woke: outcome.woke, detail: outcome.detail, paneId: outcome.paneId });
    } finally {
      if (dedupe) inFlight.delete(body.id);
    }
  };
}

/**
 * Bind a loopback HTTP server and return it. `listen` is asynchronous: a failed bind
 * (EADDRINUSE, EACCES) surfaces as an 'error' event, which the caller must handle by
 * exiting non-zero rather than letting the process print nothing and exit 0.
 *
 * @param {(req: import("node:http").IncomingMessage, res: import("node:http").ServerResponse) => Promise<void>} handler
 * @param {{port: number, host: string}} options
 * @returns {import("node:http").Server}
 */
export function createWakeServer(handler, { port, host }) {
  const server = http.createServer(handler);
  server.listen(port, host);
  return server;
}
