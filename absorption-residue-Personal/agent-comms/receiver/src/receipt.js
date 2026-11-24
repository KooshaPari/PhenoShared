// The PhenoBot receipt contract.
//
// The only real producer of wake requests is PhenoBot's agent bridge. Its client
// (`httpWakeAdapter` in PhenoBot `src/bridges/inbox.ts`) posts a full Receipt and
// accepts the wake ONLY when the response body is exactly:
//
//     { "status": "awakened", "receiptId": "<the receipt id it sent>" }
//
// Any other shape is treated as a failed wake, and the receipt is RETAINED for
// replay. A 202 means "accepted, protocol pending" and is also not a wake.
//
// This module is the single place that knows that contract, so the receiver
// cannot drift from the producer. The mirrored source of truth is:
//
//     PhenoBot/src/bridges/inbox.ts   (httpWakeAdapter, Receipt)
//     PhenoBot/src/bridges/personas.ts (persona keys)
//
// MIRRORED, NOT COPIED, ON PURPOSE. The persona list and the receipt-id
// derivation are duplicated here rather than imported, because PhenoBot is a
// separate repository and job-cockpit must not take a runtime dependency on it.
// Both sides are covered by contract tests, so a change on either side fails
// loudly rather than silently mismatching.

import { createHash } from "node:crypto";

// PhenoBot's persona keys (PhenoBot `src/bridges/personas.ts`). The set of
// personas PhenoBot is willing to wake. A wake for anything else is refused.
export const PHENOBOT_PERSONAS = Object.freeze([
  "Instinct",
  "Dots",
  "Hermes",
  "ChatGPT",
  "jcode",
  "Codex",
  "Paperclip",
]);

// PhenoBot derives receipt ids with `/^[a-f0-9]{64}$/`.
export const RECEIPT_ID_PATTERN = /^[a-f0-9]{64}$/;

/**
 * sha256 of a message body, hex. Used as the content component of a receipt id.
 *
 * A non-string (or absent) content hashes as the empty string. That keeps a two-argument
 * `deriveReceiptId(agent, messageId)` call well defined, and it means a body that omits
 * `content` can never collide with a body whose content happens to be `"undefined"`.
 *
 * @param {unknown} content
 * @returns {string}
 */
export function contentHash(content) {
  return createHash("sha256")
    .update(typeof content === "string" ? content : "")
    .digest("hex");
}

/**
 * Derive the receipt id as:
 *   sha256(`${agent}:${messageId}:${sha256(content)}`)
 *
 * WHY CONTENT IS PART OF THE IDENTITY. A receipt id built from `agent:messageId` alone
 * makes an AMENDED message indistinguishable from the original: the producer can send the
 * same `messageId` with corrected content, and the receiver would answer with the outcome
 * recorded for the OLD content — including a `delivered` ack for text the pane never saw,
 * or a `pending` refusal that blocks the correction forever. Folding a hash of the content
 * into the id gives each distinct body its own receipt, so an amendment is a new receipt
 * and a replay of unchanged content is still the same receipt.
 *
 * The producer must hash the same way. PhenoBot's older `sha256(agent:messageId)` ids no
 * longer match, and are refused `400 {"code":"receipt-id-mismatch"}` rather than silently
 * deduped against the wrong body. See README "Receipt-id integrity".
 *
 * @param {string} agent
 * @param {string} messageId
 * @param {unknown} [content] the body the receipt carries; absent hashes as ""
 * @returns {string}
 */
export function deriveReceiptId(agent, messageId, content = "") {
  return createHash("sha256")
    .update(`${agent}:${messageId}:${contentHash(content)}`)
    .digest("hex");
}

/**
 * Validate a posted receipt body. Returns a list of human-readable problems;
 * an empty list means the body is acceptable.
 *
 * We deliberately validate the same invariants PhenoBot enforces on its own side
 * (`Inbox.path` throws "Invalid receipt reference" for an unknown persona or a
 * non-hex-64 id), so a body PhenoBot could never have persisted is rejected here too.
 *
 * @param {unknown} body
 * @returns {string[]}
 */
export function validateReceiptBody(body) {
  const problems = [];
  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return ["receipt body must be a JSON object"];
  }
  const receipt = /** @type {Record<string, any>} */ (body);

  if (typeof receipt.id !== "string" || !RECEIPT_ID_PATTERN.test(receipt.id)) {
    problems.push("id must be 64 lowercase hex characters");
  }
  if (typeof receipt.agent !== "string" || !PHENOBOT_PERSONAS.includes(receipt.agent)) {
    problems.push(`agent must be one of: ${PHENOBOT_PERSONAS.join(", ")}`);
  }
  if (typeof receipt.messageId !== "string" || !receipt.messageId) {
    problems.push("messageId is required");
  }
  if (typeof receipt.userId !== "string" || !receipt.userId) {
    problems.push("userId is required");
  }
  if (typeof receipt.content !== "string") {
    problems.push("content is required");
  }
  if (typeof receipt.guildId !== "string" || !receipt.guildId) {
    problems.push("guildId is required");
  }
  if (typeof receipt.channelId !== "string" || !receipt.channelId) {
    problems.push("channelId is required");
  }
  return problems;
}

/**
 * The acknowledgement body PhenoBot requires for a wake to count as delivered.
 * It must echo the receipt id EXACTLY; PhenoBot compares with `!==` and treats
 * any other value as an invalid acknowledgement.
 *
 * @param {string} receiptId
 * @returns {{status: "awakened", receiptId: string}}
 */
export function awakenedAck(receiptId) {
  return { status: "awakened", receiptId };
}
