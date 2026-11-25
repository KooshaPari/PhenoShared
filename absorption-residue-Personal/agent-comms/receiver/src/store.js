// Durable state for the wake receiver: an append-only receipt log and the durable
// idempotency index that decides whether a replay may wake a pane again.
//
// DURABILITY IS A CONTRACT HERE, NOT A HOPE. Every write in this module fsyncs before it
// returns, and every write throws on failure. Swallowing a disk error would let the server
// answer `{"status":"awakened"}` for a wake whose outcome never reached the disk, which is
// exactly the lie the replay protocol exists to prevent. Callers decide what a write
// failure means; this module never decides it for them.
//
// The append is `open(O_APPEND)` + `write` + `fsync` + `close` rather than
// `appendFileSync`, because `appendFileSync` returns once the bytes are in the page cache.
// A crash or power loss after that return but before the kernel flushes would lose the
// line, and a lost `pending` line is a wake the receiver would then happily repeat.
import fs from "node:fs";
import path from "node:path";

/** The index exists on disk but cannot be trusted. Failing closed beats guessing. */
export class SeenIndexCorruptError extends Error {
  /**
   * @param {string} file
   * @param {number} lineNo 1-based line number of the unreadable record
   * @param {string} reason
   */
  constructor(file, lineNo, reason) {
    // Deliberately no file content: a corrupt line could contain anything, including a
    // hand-pasted secret, and this message ends up in a log and on a terminal.
    super(`seen index is corrupt at ${path.basename(file)} line ${lineNo}: ${reason}`);
    this.name = "SeenIndexCorruptError";
    this.code = "seen-index-corrupt";
    this.line = lineNo;
  }
}

/**
 * The index is full of unresolved (`pending`) receipts, so a new id cannot be recorded
 * without evicting one. Evicting an unknown outcome would let a replay wake the pane a
 * second time, so the write is refused instead.
 */
export class SeenIndexCapacityError extends Error {
  /** @param {number} pending number of unresolved pending entries holding a live lease */
  constructor(pending) {
    super(
      `seen index holds ${pending} unresolved pending receipts; resolve them before new ids can be recorded`,
    );
    this.name = "SeenIndexCapacityError";
    this.code = "seen-index-at-capacity";
    this.pending = pending;
  }
}

/**
 * An operator asked to resolve a receipt id that is not in the index.
 *
 * Creating the record instead would be worse than refusing: a typo would plant a
 * `delivered` line for an id the producer may later use for a real message, and that
 * message would then be acknowledged without ever waking its pane.
 */
export class UnknownReceiptError extends Error {
  /** @param {string} id */
  constructor(id) {
    super(`no receipt with id ${id} is recorded in the seen index`);
    this.name = "UnknownReceiptError";
    this.code = "unknown-receipt";
    this.receiptId = id;
  }
}

/**
 * How long a `pending` receipt is treated as a LIVE attempt.
 *
 * A pending line is written before the pane is walked and replaced by the outcome
 * afterwards. If the process dies in between, the outcome is genuinely unknown and the
 * receiver fails closed. But "unknown forever" is not safe either: every abandoned attempt
 * would hold a permanent slot in a bounded index, and three crashed wakes would eventually
 * wedge the whole bridge on capacity with no way out short of a hand edit.
 *
 * So a pending intent is a LEASE. After this long, the attempt is presumed dead and the
 * receipt becomes retryable again: a replay may walk the pane once more. 30s is well above
 * the slowest observed wake (herdr steps have a 10s per-call ceiling) and short enough that
 * a stuck receipt unblocks itself rather than parking the index.
 */
export const SEEN_LEASE_MS = 30_000;

/**
 * How many wake attempts a receipt may accumulate before it is EXHAUSTED.
 *
 * `failed` is normally retryable, which is exactly right for a transient failure. It is
 * wrong for a receipt whose pane will never answer: the producer replays on every pass, the
 * receiver walks the pane again, and the loop has no terminal state. After this many failed
 * attempts the receipt is marked `exhausted` and replays are refused instead of re-walked.
 * An operator resolves it explicitly (see the `resolve` command) once they know why.
 */
export const SEEN_MAX_ATTEMPTS = 3;

/**
 * True when a `pending` entry's lease has lapsed, so the attempt is presumed dead.
 *
 * Entries with no `attempted_at` are NEVER expired. Those are lines written before the lease
 * existed (or hand-written by an operator during recovery); their age is unknown, and
 * inventing an age from `ts` would let compaction silently discard an unknown outcome that
 * an older version deliberately preserved. They stay blocking until resolved, exactly as
 * before.
 *
 * @param {{status?: string, attempted_at?: string} | undefined} entry
 * @param {number} [now] epoch milliseconds
 * @returns {boolean}
 */
export function isLeaseExpired(entry, now = Date.now()) {
  if (!entry || entry.status !== "pending") return false;
  if (typeof entry.attempted_at !== "string") return false;
  const started = Date.parse(entry.attempted_at);
  if (!Number.isFinite(started)) return false;
  return now - started > SEEN_LEASE_MS;
}

/**
 * True when a receipt has used every allowed attempt without being delivered.
 * @param {{status?: string, attempts?: number} | undefined} entry
 * @returns {boolean}
 */
export function isExhausted(entry) {
  return (
    Boolean(entry) &&
    entry.status === "failed" &&
    Number(entry.attempts ?? 0) >= SEEN_MAX_ATTEMPTS
  );
}

/**
 * fsync a directory so a create or rename inside it survives a power loss.
 *
 * Best effort by design: some filesystems and platforms refuse to fsync a directory
 * (Windows raises EPERM/EINVAL), and a refusal there does not invalidate the write that
 * already succeeded. It never throws, and it never hides a failed *data* fsync: those
 * happen on the file descriptor and do propagate.
 *
 * @param {string} dir
 */
function fsyncDir(dir) {
  let fd;
  try {
    fd = fs.openSync(dir, "r");
    fs.fsyncSync(fd);
  } catch {
    // Directory fsync unsupported here; the file-level fsync upstream still stands.
  } finally {
    if (fd !== undefined) {
      try {
        fs.closeSync(fd);
      } catch {
        // closing a read-only directory handle cannot fail in a way worth reporting
      }
    }
  }
}

/**
 * Create the file if it is absent and make that directory entry durable.
 *
 * Without the directory fsync, a power loss after the first append can leave the file's
 * data on disk but its name missing, which reads as "no index at all" and re-opens every
 * receipt for replay.
 *
 * @param {string} file
 * @param {string} dir
 */
function ensureFileDurable(file, dir) {
  const existed = fs.existsSync(file);
  const fd = fs.openSync(file, "a");
  fs.closeSync(fd);
  if (!existed) fsyncDir(dir);
}

/**
 * Append one line and fsync it. Throws whatever the filesystem throws.
 *
 * A record must never share a physical line with a previous one. If the file does not end
 * in a newline (a hand edit, or a writer that died mid-line), the next append would splice
 * onto that line, and the reload would then be unable to parse the *valid* new record. One
 * leading newline here keeps every future record independently readable.
 *
 * @param {string} file
 * @param {string} line a single line, without the trailing newline
 */
function appendLineDurable(file, line) {
  // "a+" so the last byte can be inspected and the write still lands at the end.
  const fd = fs.openSync(file, "a+");
  try {
    const size = fs.fstatSync(fd).size;
    if (size > 0) {
      const last = Buffer.alloc(1);
      fs.readSync(fd, last, 0, 1, size - 1);
      if (last[0] !== 0x0a) fs.writeSync(fd, "\n");
    }
    fs.writeSync(fd, line + "\n");
    fs.fsyncSync(fd);
  } finally {
    fs.closeSync(fd);
  }
}

/**
 * Read a JSONL file into raw lines, returning [] when it does not exist yet. Throws on any
 * other read error; read failures are never a reason to pretend the index is empty.
 * @param {string} file
 * @returns {string[]}
 */
function readLines(file) {
  let raw;
  try {
    raw = fs.readFileSync(file, "utf8");
  } catch (error) {
    if (/** @type {NodeJS.ErrnoException} */ (error).code === "ENOENT") return [];
    throw error;
  }
  return raw.split("\n").filter(Boolean);
}

export class ReceiptStore {
  /**
   * @param {string} stateDir directory that will hold receipts.jsonl
   */
  constructor(stateDir) {
    this.stateDir = stateDir;
    fs.mkdirSync(stateDir, { recursive: true });
    this.file = path.join(stateDir, "receipts.jsonl");
    ensureFileDurable(this.file, this.stateDir);
  }

  /**
   * Append a receipt and fsync it. Throws on failure: the caller must not report a wake
   * whose evidence could not be made durable.
   *
   * @param {Record<string, any>} receipt
   */
  add(receipt) {
    appendLineDurable(this.file, JSON.stringify(receipt));
  }
}

// Bound the durable seen-receipt index. When it grows past this, the oldest SETTLED entries
// are compacted away. A receipt older than that is almost certainly past the producer's
// replay window, and holding every id forever would turn a small index into an unbounded
// file. Entry 2 (`pending`) is never evicted: see _compact.
const SEEN_MAX = 10_000;

/** The three durable states a receipt id can be in. */
export const SEEN_STATUSES = Object.freeze(["pending", "delivered", "failed"]);

/**
 * One durable index record.
 * @typedef {object} SeenEntry
 * @property {string} id
 * @property {"pending" | "delivered" | "failed"} status
 * @property {string} ts when the transition was recorded (ISO-8601)
 * @property {string} [attempted_at] when the current attempt began; pending lines only
 * @property {number} [attempts] wake attempts started for this receipt
 * @property {boolean} [exhausted] failed lines that have used every allowed attempt
 */

/**
 * Durable idempotency index for PhenoBot receipts.
 *
 * THE THREE STATES, AND WHY `pending` EXISTS.
 *
 *   pending    an intent to wake was written, and the wake has not been recorded as
 *              finished. Either it is happening right now, or the process died between the
 *              intent and the outcome. Those two cases are indistinguishable from the disk,
 *              and that ambiguity is the whole point: a `pending` record is an
 *              UNKNOWN OUTCOME and must never be read as delivered. A pending record is a
 *              LEASE, not a life sentence: once `attempted_at` is older than
 *              `SEEN_LEASE_MS` the attempt is presumed dead and the receipt is retryable
 *              again, so a crash cannot park a slot in a bounded index forever.
 *   delivered  the pane was raised and that fact reached the disk.
 *   failed     a known attempt did not raise the pane. Retrying is correct, up to
 *              `SEEN_MAX_ATTEMPTS`; past that the receipt is `exhausted` and replays are
 *              refused instead of re-walked, which is what stops an unwakeable receipt from
 *              replaying forever. An exhausted receipt is settled, so compaction may evict it.
 *
 * The index is written BEFORE the pane is walked (the intent) and again AFTER the outcome
 * is known. That ordering is what makes a crash safe:
 *
 *   * crash before the intent  -> no record at all, the producer replays, nothing happened;
 *   * crash after the intent    -> `pending` survives, replay is refused as uncertain, and
 *                                  the receiver does NOT pretend delivery and does NOT
 *                                  re-wake;
 *   * crash after the outcome   -> `delivered`/`failed` survives and the replay rule applies.
 *
 * Stores only receipt identity, status, timestamps, and an attempt count:
 * `{id, status, ts}`, plus `attempted_at`/`attempts` on a pending line and `attempts`/
 * `exhausted` on a failed one. It never stores `content`, the bearer token, or any other
 * message body — the content only ever contributes a one-way hash to the receipt id, which
 * is computed by the caller — so the index is safe to keep on disk.
 *
 * CONCURRENCY SCOPE (SINGLE PROCESS ONLY). This index is a single-process, file-backed
 * record. It serialises concurrent duplicates inside ONE receiver process (the in-memory map
 * plus the server's in-flight set). It is NOT a cross-process lock: two receiver processes
 * sharing a state dir would each hold their own map over the same file and could both walk
 * the same pane; the lease would also let one process's expired pending be retried by the
 * other while the first is still walking. Run exactly one receiver per state dir.
 * See README "Scope and guarantees" for the honest limits.
 */
export class SeenStore {
  /**
   * @param {string} stateDir directory that will hold seen.jsonl
   */
  constructor(stateDir) {
    this.stateDir = stateDir;
    fs.mkdirSync(stateDir, { recursive: true });
    this.file = path.join(stateDir, "seen.jsonl");
    ensureFileDurable(this.file, this.stateDir);
    /** @type {Map<string, SeenEntry>} */
    this.map = new Map();
    this._load();
  }

  /**
   * Load the durable index, FAILING CLOSED on any line that cannot be trusted.
   *
   * `pending` lines are loaded deliberately. Dropping them would erase the only evidence
   * that a wake's outcome is unknown, and the next replay would wake the pane a second
   * time. A later line for the same id wins, so an operator can resolve an uncertain
   * receipt by appending a `delivered` or `failed` line for it.
   *
   * WHY A CORRUPT LINE IS FATAL. Silently skipping an unparsable line means skipping an
   * unknown transition. The skipped line could be the `delivered` for a receipt that then
   * wakes again, or the `pending` of an attempt whose outcome is unknown. Neither mistake is
   * recoverable from inside the process, and a receiver that will not start is strictly
   * safer than one that wakes panes on a fabricated clean slate. The operator truncates the
   * bad line (it has a line number) and restarts.
   */
  _load() {
    const lines = readLines(this.file);
    /** @type {Set<string>} ids already inserted in this pass */
    const seenInFile = new Set();
    for (let index = 0; index < lines.length; index += 1) {
      const line = lines[index];
      let entry;
      try {
        entry = JSON.parse(line);
      } catch {
        throw new SeenIndexCorruptError(this.file, index + 1, "unparsable JSON record");
      }
      if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
        throw new SeenIndexCorruptError(this.file, index + 1, "record is not a JSON object");
      }
      if (typeof entry.id !== "string" || !SEEN_STATUSES.includes(entry.status)) {
        throw new SeenIndexCorruptError(this.file, index + 1, "record has no valid id/status");
      }
      // Optional fields are validated when present, because a mis-typed attempt counter would
      // silently disable the exhaustion rule (a string "3" or NaN never reaches the
      // threshold), and a mis-typed lease would either never expire or expire instantly.
      // Lines written before these fields existed are still valid: absent means "unknown",
      // which reads as attempt 0 / no lease, never as success.
      if (entry.attempts !== undefined && !(Number.isInteger(entry.attempts) && entry.attempts >= 0)) {
        throw new SeenIndexCorruptError(this.file, index + 1, "record has an invalid attempts count");
      }
      if (entry.attempted_at !== undefined && typeof entry.attempted_at !== "string") {
        throw new SeenIndexCorruptError(this.file, index + 1, "record has an invalid attempted_at");
      }
      if (entry.exhausted !== undefined && typeof entry.exhausted !== "boolean") {
        throw new SeenIndexCorruptError(this.file, index + 1, "record has an invalid exhausted flag");
      }
      // Refresh recency for a repeated id. `Map.set` on an existing key keeps the ORIGINAL
      // insertion position, so a receipt resolved late (or a duplicate line) would otherwise
      // stay at the front of the queue and be the first thing _compact drops.
      if (seenInFile.has(entry.id)) this.map.delete(entry.id);
      else seenInFile.add(entry.id);
      this.map.set(entry.id, entry);
    }
  }

  /**
   * Number of unresolved entries holding a LIVE lease, which are the ones that genuinely
   * block capacity. A pending entry whose lease lapsed is presumed dead: it is retryable and
   * evictable, so counting it here would let one crashed attempt wedge the index forever.
   *
   * @param {number} [now] epoch milliseconds
   */
  _pendingCount(now = Date.now()) {
    let count = 0;
    for (const entry of this.map.values()) {
      if (entry.status === "pending" && !isLeaseExpired(entry, now)) count += 1;
    }
    return count;
  }

  /**
   * The recorded outcome for a receipt id, or undefined if it was never attempted.
   * @param {string} id
   * @returns {{id: string, status: string, ts: string} | undefined}
   */
  get(id) {
    return this.map.get(id);
  }

  /**
   * Record a state transition and fsync it. Throws on failure, so the caller can refuse to
   * report anything the disk does not know.
   *
   * `pending` starts (or restarts) an attempt: it stamps `attempted_at` with the lease start
   * and increments `attempts`. `failed` carries that count forward and marks itself
   * `exhausted` once the budget is spent. `delivered` keeps the count as evidence of how
   * many attempts it took.
   *
   * @param {string} id
   * @param {"pending" | "delivered" | "failed"} status
   */
  record(id, status) {
    if (!SEEN_STATUSES.includes(status)) throw new Error(`unknown seen status: ${status}`);
    // CAPACITY, FAIL CLOSED. A new id needs room, and room can only be made by evicting a
    // settled entry. When every slot is held by an unresolved receipt with a live lease
    // there is no safe eviction, so refuse the write and let the producer replay later. The
    // alternative (evicting a live pending entry) would forget an in-flight attempt and
    // permit a second wake.
    if (!this.map.has(id) && this.map.size >= SEEN_MAX) {
      const pending = this._pendingCount();
      if (pending >= SEEN_MAX) throw new SeenIndexCapacityError(pending);
    }
    const entry = this._nextEntry(id, status);
    appendLineDurable(this.file, JSON.stringify(entry));
    // Re-insert so map order tracks recency: compaction keeps the tail, and a receipt
    // resolved long after its first attempt must not keep its original (old) slot.
    this.map.delete(id);
    this.map.set(id, entry);
    if (this.map.size > SEEN_MAX) this._compact();
  }

  /**
   * Build the record for a transition, deriving the lease and attempt fields from what is
   * already recorded. Pure, so `record` and `resolve` cannot disagree about the shape.
   *
   * @param {string} id
   * @param {"pending" | "delivered" | "failed"} status
   * @param {{resetAttempts?: boolean}} [options]
   * @returns {SeenEntry}
   */
  _nextEntry(id, status, { resetAttempts = false } = {}) {
    const prior = this.map.get(id);
    const priorAttempts =
      !resetAttempts && prior && Number.isInteger(prior.attempts) ? prior.attempts : 0;
    const now = new Date().toISOString();
    if (status === "pending") {
      return { id, status, ts: now, attempted_at: now, attempts: priorAttempts + 1 };
    }
    if (status === "failed") {
      const attempts = resetAttempts ? 0 : Math.max(priorAttempts, 1);
      return { id, status, ts: now, attempts, exhausted: attempts >= SEEN_MAX_ATTEMPTS };
    }
    return { id, status, ts: now, attempts: priorAttempts };
  }

  /**
   * Operator resolution of an uncertain receipt. Appends `delivered` or `failed` so the LAST
   * line for the id wins on the next load, and applies it in memory for the running process.
   *
   * Resolving to `failed` deliberately RESETS the attempt counter: an operator who says "the
   * pane was not raised, try again" is granting a fresh budget, otherwise a receipt that had
   * already exhausted its attempts would be refused the moment the producer replayed it.
   * Resolving to `delivered` keeps the count as history.
   *
   * An unknown id is refused rather than created: a typo would otherwise plant a durable
   * `delivered` line for an id the producer may later use for a real message.
   *
   * @param {string} id
   * @param {"delivered" | "failed"} status
   * @returns {{previous: SeenEntry, entry: SeenEntry}}
   */
  resolve(id, status) {
    if (status !== "delivered" && status !== "failed") {
      throw new Error(`an operator may only resolve a receipt to delivered or failed, not ${status}`);
    }
    const prior = this.map.get(id);
    if (!prior) throw new UnknownReceiptError(id);
    const entry = this._nextEntry(id, status, { resetAttempts: status === "failed" });
    appendLineDurable(this.file, JSON.stringify(entry));
    this.map.delete(id);
    this.map.set(id, entry);
    if (this.map.size > SEEN_MAX) this._compact();
    return { previous: prior, entry };
  }

  /**
   * Rewrite the index, atomically, keeping every unresolved entry that still holds a lease.
   *
   * LIVE `pending` entries are retained regardless of age: forgetting one turns an in-flight
   * (or just-crashed) attempt into "never attempted", and the next replay could walk the pane
   * a second time while the first walk is still alive. An entry whose lease has LAPSED is a
   * different case: the attempt is presumed dead and retryable, so it is treated as settled
   * for eviction purposes. That is what stops a handful of crashed wakes from filling the
   * index and refusing every new receipt forever.
   *
   * The budget is `SEEN_MAX` total, of which live pending takes priority and the remaining
   * slots go to the newest settled entries (delivered, failed, and lapsed pending).
   */
  _compact() {
    const now = Date.now();
    const all = [...this.map.values()];
    const livePending = all.filter(
      (entry) => entry.status === "pending" && !isLeaseExpired(entry, now),
    );
    const settled = all.filter(
      (entry) => entry.status !== "pending" || isLeaseExpired(entry, now),
    );
    const room = Math.max(0, SEEN_MAX - livePending.length);
    const keep = [...livePending, ...settled.slice(-room)];
    const tmp = `${this.file}.tmp`;
    try {
      const fd = fs.openSync(tmp, "w");
      try {
        fs.writeSync(fd, keep.map((entry) => JSON.stringify(entry)).join("\n") + "\n");
        fs.fsyncSync(fd);
      } finally {
        fs.closeSync(fd);
      }
      fs.renameSync(tmp, this.file);
      // The rename is a directory mutation; without this fsync a power loss can resurrect the
      // pre-compaction file and silently drop the pending entries just written.
      fsyncDir(this.stateDir);
      this.map = new Map(keep.map((entry) => [entry.id, entry]));
    } catch {
      // Best effort: a failed compaction leaves the (larger) index in place, which is a
      // size problem, not a correctness problem. The pre-compaction file is still the
      // durable truth because compaction only lands via the atomic rename.
      try {
        fs.unlinkSync(tmp);
      } catch {
        // nothing to clean up
      }
    }
  }
}
