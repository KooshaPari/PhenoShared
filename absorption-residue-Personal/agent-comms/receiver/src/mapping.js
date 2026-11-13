// Recipient -> pane mapping. Pure, dependency-free normalization and resolution so the
// receiver and the waker share one notion of "which local part did this message come for".
//
// A message arrives addressed to a recipient (an email address such as
// `civis@example.com`, or a bare local part). The runtime maps that recipient's
// LOCAL PART to a Herdr pane binding. The domain is never used for routing: this runtime
// consumes a mapping, it does not create mail routing, DNS, aliases, or provider routes.
//
// TWO KEYS, ONE TABLE. The same table is keyed by either of two namespaces, because the
// bridge has two real producers and both must resolve to the same pane:
//
//   * a RECIPIENT local part  -- the email leg (`civis@example.com`)
//   * a PhenoBot PERSONA name -- the Discord leg (`jcode`, `Instinct`, `Codex`, ...)
//
// They cannot collide: a persona name never contains "@" and a recipient local part
// never matches a persona key. A single lookup therefore serves both legs without a
// second file, and the map stays the ONE place that defines what may be woken.

/**
 * Normalize a recipient (email address or bare local part) to a canonical local part:
 * lowercase, trim, strip any "@domain" suffix. Returns "" when nothing is left.
 *
 * @param {string} recipient
 * @returns {string}
 */
export function normalizeRecipient(recipient) {
  const raw = String(recipient ?? "").trim().toLowerCase();
  if (!raw) return "";
  const at = raw.indexOf("@");
  return (at === -1 ? raw : raw.slice(0, at)).trim();
}

/**
 * Normalize a raw mapping object (from JSON) into `key -> {paneId, label?, agent?}`.
 * Accepts string values as a shorthand for an explicit pane binding, and object values for
 * a binding that also carries label/agent hints (used only as a fallback match when the
 * explicit paneId is not present in `herdr pane list`).
 *
 * Keys are lowercased so a lookup is case-insensitive, matching the domain's
 * case-insensitive local-part semantics. A persona key such as `jcode` lowercases to
 * `jcode`, which is exactly how PhenoBot sends it, so the persona name survives
 * lowercasing unchanged.
 *
 * @param {Record<string, string | {paneId?: string, label?: string, agent?: string}>} obj
 * @returns {Record<string, {paneId?: string, label?: string, agent?: string}>}
 */
export function parseRecipientMap(obj) {
  /** @type {Record<string, {paneId?: string, label?: string, agent?: string}>} */
  const map = {};
  for (const [key, value] of Object.entries(obj ?? {})) {
    // Keys starting with `_` are comments/metadata (JSON has no comment syntax).
    if (key.startsWith("_")) continue;
    const recipient = normalizeRecipient(key);
    if (!recipient) continue;
    if (typeof value === "string") {
      if (!value.trim()) throw new Error(`empty pane binding for recipient ${recipient}`);
      map[recipient] = { paneId: value.trim() };
    } else if (value && typeof value === "object" && typeof value.paneId === "string" && value.paneId.trim()) {
      map[recipient] = {
        paneId: value.paneId.trim(),
        ...(value.label ? { label: value.label } : {}),
        ...(value.agent ? { agent: value.agent } : {}),
      };
    } else {
      throw new Error(`invalid binding for recipient ${recipient}: expected a paneId string or object`);
    }
  }
  return map;
}

/**
 * Resolve a recipient (email address or bare local part) to its pane binding, or undefined.
 *
 * @param {Record<string, any>} recipientMap
 * @param {string} recipient
 * @returns {{paneId?: string, label?: string, agent?: string} | undefined}
 */
export function resolveRecipient(recipientMap, recipient) {
  const key = normalizeRecipient(recipient);
  if (!key) return undefined;
  return recipientMap[key];
}
